"""Qdrant vector-store adapter for local, network, and managed deployments."""
from __future__ import annotations

from app.domain.documents import DocumentError


class QdrantVectorStore:
    def __init__(self, url: str, collection_name: str, api_key: str | None = None,
                 timeout_seconds: int = 30, dimensions: int = 384):
        self.url = url.rstrip("/")
        self.collection_name = collection_name
        self.api_key = api_key or None
        self.timeout_seconds = timeout_seconds
        self.dimensions = dimensions
        self._client = None

    def client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(url=self.url, api_key=self.api_key,
                                            timeout=self.timeout_seconds)
            except ImportError as error:
                raise DocumentError("QDRANT_DRIVER_MISSING", "Install the Qdrant client dependency and restart the backend.", 503) from error
        return self._client

    def _translate(self, operation: str, error: Exception):
        if isinstance(error, DocumentError):
            raise error
        raise DocumentError("QDRANT_UNAVAILABLE", f"Qdrant could not {operation} at {self.url}.", 503) from error

    def _validate_collection(self) -> None:
        try:
            from qdrant_client.models import Distance
            info = self.client().get_collection(self.collection_name)
            vectors = info.config.params.vectors
            if isinstance(vectors, dict) or vectors.size != self.dimensions or vectors.distance != Distance.EUCLID:
                raise DocumentError(
                    "QDRANT_COLLECTION_INCOMPATIBLE",
                    f"Collection {self.collection_name} must use {self.dimensions}-dimension Euclidean vectors.", 409)
        except DocumentError:
            raise
        except Exception as error:
            self._translate("inspect the configured collection", error)

    def ensure_collection(self) -> None:
        try:
            from qdrant_client.models import Distance, PayloadSchemaType, VectorParams
            client = self.client()
            if client.collection_exists(self.collection_name):
                self._validate_collection()
                return
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dimensions, distance=Distance.EUCLID),
            )
            for field in ("project_id", "document_id"):
                client.create_payload_index(
                    collection_name=self.collection_name, field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD, wait=True)
        except DocumentError:
            raise
        except Exception as error:
            self._translate("create the configured collection", error)

    def health_check(self) -> dict:
        try:
            client = self.client()
            collections = client.get_collections().collections
            names = {item.name for item in collections}
            if self.collection_name in names:
                self._validate_collection()
            return {"collection_exists": self.collection_name in names,
                    "collections": len(collections)}
        except DocumentError:
            raise
        except Exception as error:
            self._translate("complete a health check", error)

    @staticmethod
    def _filter(project_id: str, document_id: str | None = None):
        from qdrant_client.models import FieldCondition, Filter, MatchValue
        conditions = [FieldCondition(key="project_id", match=MatchValue(value=project_id))]
        if document_id is not None:
            conditions.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
        return Filter(must=conditions)

    def upsert(self, ids: list[str], texts: list[str], vectors: list[list[float]],
               project_id: str, document_id: str) -> None:
        if not (len(ids) == len(texts) == len(vectors)):
            raise DocumentError("INVALID_VECTOR_BATCH", "Vector IDs, texts, and embeddings must have equal lengths.", 500)
        self.ensure_collection()
        self.delete(project_id, document_id)
        if not ids:
            return
        try:
            from qdrant_client.models import PointStruct
            points = [PointStruct(id=point_id, vector=vector,
                                  payload={"project_id": project_id, "document_id": document_id, "text": text})
                      for point_id, text, vector in zip(ids, texts, vectors)]
            self.client().upsert(collection_name=self.collection_name, points=points, wait=True)
        except Exception as error:
            self._translate("store document vectors", error)

    def search_with_distances(self, project_id: str, vector: list[float],
                              limit: int) -> list[tuple[str, float]]:
        self.ensure_collection()
        try:
            result = self.client().query_points(
                collection_name=self.collection_name, query=vector,
                query_filter=self._filter(project_id), limit=limit,
                with_payload=False, with_vectors=False)
            return [(str(point.id), float(point.score)) for point in result.points]
        except Exception as error:
            self._translate("search document vectors", error)

    def search(self, project_id: str, vector: list[float], limit: int) -> list[str]:
        return [point_id for point_id, _distance in self.search_with_distances(project_id, vector, limit)]

    def delete(self, project_id: str, document_id: str) -> None:
        try:
            from qdrant_client.models import FilterSelector
            client = self.client()
            if not client.collection_exists(self.collection_name):
                return
            client.delete(collection_name=self.collection_name,
                          points_selector=FilterSelector(filter=self._filter(project_id, document_id)),
                          wait=True)
        except Exception as error:
            self._translate("delete document vectors", error)
