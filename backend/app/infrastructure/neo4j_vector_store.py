"""Neo4j network vector-store adapter with project-isolated indexes."""
from __future__ import annotations

import hashlib

from app.domain.documents import DocumentError


class Neo4jVectorStore:
    def __init__(self, uri: str, database: str, username: str, password: str | None,
                 index_name: str, timeout_seconds: int = 30, dimensions: int = 384):
        self.uri = uri
        self.database = database
        self.username = username
        self.password = password
        self.index_name = index_name
        self.timeout_seconds = timeout_seconds
        self.dimensions = dimensions
        self._driver = None

    def driver(self):
        if not self.password:
            raise DocumentError("PROVIDER_NOT_CONFIGURED", "Add the Neo4j password to this plugin.", 409)
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                self._driver = GraphDatabase.driver(
                    self.uri, auth=(self.username, self.password),
                    connection_timeout=self.timeout_seconds)
            except ImportError as error:
                raise DocumentError(
                    "NEO4J_DRIVER_MISSING",
                    "Install the Neo4j Python driver and restart the backend.", 503) from error
            except Exception as error:
                self._translate("create a connection", error)
        return self._driver

    def _translate(self, operation: str, error: Exception):
        if isinstance(error, DocumentError):
            raise error
        raise DocumentError(
            "NEO4J_UNAVAILABLE", f"Neo4j could not {operation} at {self.uri}.", 503) from error

    def _execute(self, query: str, **parameters):
        try:
            records, _summary, _keys = self.driver().execute_query(
                query, parameters_=parameters, database_=self.database)
            return records
        except Exception as error:
            self._translate("complete the vector-store operation", error)

    def _scope(self, project_id: str) -> tuple[str, str]:
        digest = hashlib.sha256(f"{self.index_name}:{project_id}".encode()).hexdigest()[:16]
        return f"{self.index_name[:40]}_{digest}", f"DIPassage_{digest}"

    def ensure_index(self, project_id: str) -> str:
        index, label = self._scope(project_id)
        query = (
            f"CREATE VECTOR INDEX `{index}` IF NOT EXISTS "
            f"FOR (node:`{label}`) ON (node.embedding) "
            "OPTIONS {indexConfig: {"
            f"`vector.dimensions`: {self.dimensions}, "
            "`vector.similarity_function`: 'euclidean'}}"
        )
        self._execute(query)
        records = self._execute(
            "SHOW VECTOR INDEXES YIELD name, labelsOrTypes, properties, options, state "
            "WHERE name = $index_name "
            "RETURN labelsOrTypes[0] AS label, properties[0] AS property, "
            "options.indexConfig['vector.dimensions'] AS dimensions, "
            "options.indexConfig['vector.similarity_function'] AS similarity, state",
            index_name=index)
        if not records:
            raise DocumentError("NEO4J_INDEX_MISSING", f"Neo4j did not create vector index {index}.", 503)
        row = records[0]
        if (row["label"] != label or row["property"] != "embedding"
                or int(row["dimensions"]) != self.dimensions
                or str(row["similarity"]).lower() != "euclidean"):
            raise DocumentError(
                "NEO4J_INDEX_INCOMPATIBLE",
                f"Neo4j index {index} must use {self.dimensions}-dimension Euclidean vectors.", 409)
        return str(row["state"])

    def health_check(self) -> dict:
        try:
            self.driver().verify_connectivity(database=self.database)
            records = self._execute(
                "SHOW VECTOR INDEXES YIELD name WHERE name STARTS WITH $prefix RETURN count(*) AS count",
                prefix=f"{self.index_name[:40]}_")
            return {"indexes": int(records[0]["count"]) if records else 0}
        except Exception as error:
            self._translate("complete a health check", error)

    def upsert(self, ids: list[str], texts: list[str], vectors: list[list[float]],
               project_id: str, document_id: str) -> None:
        if not (len(ids) == len(texts) == len(vectors)):
            raise DocumentError("INVALID_VECTOR_BATCH", "Vector IDs, texts, and embeddings must have equal lengths.", 500)
        if any(len(vector) != self.dimensions for vector in vectors):
            raise DocumentError("INVALID_VECTOR_DIMENSIONS", f"Neo4j expects {self.dimensions}-dimension vectors.", 409)
        self.ensure_index(project_id)
        _index, label = self._scope(project_id)
        rows = [{"id": point_id, "embedding": vector} for point_id, vector in zip(ids, vectors)]
        self._execute(
            f"MATCH (old:`{label}` {{project_id: $project_id, document_id: $document_id}}) DELETE old",
            project_id=project_id, document_id=document_id)
        if not rows:
            return
        self._execute(
            "UNWIND $rows AS row "
            f"CREATE (node:`{label}`) "
            "SET node.passage_id = row.id, node.project_id = $project_id, "
            "node.document_id = $document_id, node.embedding = row.embedding",
            project_id=project_id, document_id=document_id, rows=rows)

    def search_with_distances(self, project_id: str, vector: list[float],
                              limit: int) -> list[tuple[str, float]]:
        if len(vector) != self.dimensions:
            raise DocumentError("INVALID_VECTOR_DIMENSIONS", f"Neo4j expects {self.dimensions}-dimension vectors.", 409)
        state = self.ensure_index(project_id)
        if state != "ONLINE":
            raise DocumentError("NEO4J_INDEX_BUILDING", "The Neo4j vector index is still being built. Try again shortly.", 409)
        index, _label = self._scope(project_id)
        records = self._execute(
            "CALL db.index.vector.queryNodes($index_name, $limit, $vector) "
            "YIELD node, score RETURN node.passage_id AS id, score ORDER BY score DESC",
            index_name=index, limit=limit, vector=vector)
        return [(str(row["id"]), max(0.0, 1.0 - float(row["score"]))) for row in records]

    def search(self, project_id: str, vector: list[float], limit: int) -> list[str]:
        return [point_id for point_id, _distance in self.search_with_distances(project_id, vector, limit)]

    def delete(self, project_id: str, document_id: str) -> None:
        _index, label = self._scope(project_id)
        self._execute(
            f"MATCH (node:`{label}` {{project_id: $project_id, document_id: $document_id}}) DELETE node",
            project_id=project_id, document_id=document_id)
