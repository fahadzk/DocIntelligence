"""Pipeline Lab profile of the shared indexing, retrieval, and Ask service."""
import logging
import re
import threading
from uuid import UUID

from app.config.pipeline_defaults import document_version
from app.application.search import SearchService
from app.domain.documents import DocumentError
from app.infrastructure.local_models import ChromaVectorStore
from app.infrastructure.lab_search_repository import LabSearchRepository

logger = logging.getLogger(__name__)


class LabSearchService(SearchService):
    def __init__(self, standard: SearchService, config_service, registry, data_dir):
        super().__init__(standard.documents, LabSearchRepository(standard.repository.database_path),
                         data_dir, embeddings=standard.embeddings,
                         vectors=ChromaVectorStore(data_dir / "vectors", "pipeline_lab_v1"),
                         llm=standard.llm, operations=standard.operations)
        self.config_service = config_service
        self.registry = registry

    def version_for(self, project_id: UUID) -> str:
        return document_version(self.config_service.effective(project_id)) + (
            "+bge-small-en-v1.5" if self.embeddings.ready else "+keyword")

    def schedule_project(self, project_id: UUID) -> None:
        threading.Thread(target=self.ensure_project, args=(project_id,), daemon=True,
                         name=f"lab-index-{project_id}").start()

    def ensure_project(self, project_id: UUID) -> None:
        try:
            version = self.version_for(project_id)
        except DocumentError:
            return
        states = {item["document_id"]: item for item in self.repository.status(str(project_id))}
        try:
            documents = self.documents.list(project_id)
        except DocumentError:
            return  # The project was removed before its background reindex began.
        for document in documents:
            if document.status != "ready":
                continue
            state = states.get(str(document.id))
            if state is None or state["status"] != "ready" or state["index_version"] != version or state["indexed_hash"] != document.content_hash:
                self.index_document(project_id, document.id)

    def index_document(self, project_id: UUID, document_id: UUID, force: bool = False) -> None:
        with self._lock:
            try:
                document = self.documents.get(project_id, document_id)
            except DocumentError:
                return  # A queued index task outlived this document.
            if document.status != "ready":
                return
            try:
                config = self.config_service.effective(project_id)
                version = self.version_for(project_id)
            except DocumentError:
                return
            state = next((item for item in self.repository.status(str(project_id))
                          if item["document_id"] == str(document_id)), None)
            if not force and state and state["status"] == "ready" and state["index_version"] == version and state["indexed_hash"] == document.content_hash:
                return
            try:
                self.repository.mark(str(project_id), str(document_id), "indexing", "splitting", version, document.content_hash)
                segments = self.documents.content(project_id, document_id)["segments"]
                settings = config["document"]["chunking"]
                chunker = self.registry.get("chunking", settings["plugin"]).implementation
                passages = chunker(str(project_id), str(document_id), document.content_hash,
                                   segments, version, settings, embeddings=self.embeddings, llm=self.llm)
                if self.embeddings.ready and passages:
                    self.repository.mark(str(project_id), str(document_id), "indexing", "embedding", version, document.content_hash)
                    vectors = self.embeddings.embed([row["text"] for row in passages])
                    self.vectors.upsert([row["id"] for row in passages], [row["text"] for row in passages],
                                        vectors, str(project_id), str(document_id))
                else:
                    # Remove vectors left from a former configuration or model state.
                    self.vectors.delete(str(project_id), str(document_id))
                self.repository.replace(str(project_id), str(document_id), passages, version, document.content_hash)
            except Exception as error:
                logger.exception("Pipeline Lab indexing failed for %s", document_id)
                try:
                    self.repository.mark(str(project_id), str(document_id), "failed", "indexing", version,
                                         document.content_hash, str(error)[:240])
                except Exception:
                    # The document/project may have been deleted while this background task ran.
                    logger.info("Pipeline Lab index result discarded for removed document %s", document_id)

    def preview(self, project_id: UUID, document_id: UUID) -> dict:
        document = self.documents.get(project_id, document_id)
        if document.status != "ready":
            raise DocumentError("DOCUMENT_NOT_READY", "Only readable documents can be previewed.", 409)
        config = self.config_service.effective(project_id)
        settings = config["document"]["chunking"]
        chunker = self.registry.get("chunking", settings["plugin"]).implementation
        passages = chunker(str(project_id), str(document_id), document.content_hash,
                           self.documents.content(project_id, document_id)["segments"],
                           self.version_for(project_id), settings, embeddings=self.embeddings, llm=self.llm)
        return {"count": len(passages),
                "average_characters": round(sum(len(row["text"]) for row in passages) / len(passages)) if passages else 0,
                "samples": passages[:12]}

    def _keyword(self, project_id: UUID, query: str, limit: int) -> list[tuple[str, float]]:
        terms = re.findall(r"\w+", query, re.UNICODE)[:12]
        if not terms:
            return []
        expression = " OR ".join(f'"{term}"' for term in terms)
        with self.repository.connect() as connection:
            rows = connection.execute("""SELECT f.id, bm25(lab_passages_fts) AS score
                FROM lab_passages_fts f JOIN lab_passages p ON p.id=f.id AND p.project_id=f.project_id
                JOIN documents d ON d.id=p.document_id
                JOIN lab_document_indexes i ON i.document_id=d.id
                WHERE lab_passages_fts MATCH ? AND f.project_id=? AND d.status='ready'
                AND i.status='ready' AND i.index_version=p.index_version AND i.content_hash=d.content_hash
                ORDER BY score LIMIT ?""", (expression, str(project_id), limit)).fetchall()
        return [(row[0], row[1]) for row in rows]

    def search(self, project_id: UUID, query: str, document_id: UUID | None = None,
               limit: int | None = None) -> list[dict]:
        self.documents.require_project(project_id)
        if not query.strip():
            return []
        config = self.config_service.effective(project_id)["search"]
        strategy = self.registry.get("retrieval", config["retrieval"])
        sources = strategy.implementation(config)
        if not sources or set(sources) - {"keyword", "semantic"}:
            raise DocumentError("INVALID_RETRIEVAL_PLUGIN", "The selected retrieval plugin returned invalid sources.", 500)
        use_keyword = "keyword" in sources
        use_semantic = "semantic" in sources
        keyword = self._keyword(project_id, query, config["keyword_candidates"]) if use_keyword else []
        semantic = []
        if use_semantic and self.embeddings.ready:
            vector = self.embeddings.embed([query])[0]
            semantic = self.vectors.search_with_distances(str(project_id), vector, config["semantic_candidates"])
            threshold = config["similarity_threshold"]
            if threshold is not None:
                semantic = [(pid, distance) for pid, distance in semantic if distance <= threshold]
        elif use_semantic and not use_keyword:
            raise DocumentError("MODEL_NOT_READY", "Set up the local embedding model for semantic search.", 409)
        records = {}
        for source, candidates in (("keyword", keyword), ("semantic", semantic)):
            for rank, (pid, score) in enumerate(candidates):
                item = records.setdefault(pid, {"id": pid, "fusion_score": 0.0,
                                                "keyword_rank": None, "semantic_rank": None,
                                                "keyword_score": None, "semantic_score": None})
                item[source + "_rank"] = rank + 1
                item[source + "_score"] = score
                item["fusion_score"] += self.registry.get("fusion", config["fusion"]).implementation(rank, config, source)
        ordered = sorted(records.values(), key=lambda item: -item["fusion_score"])
        results = []
        for candidate in ordered:
            passage = self.repository.get(str(project_id), candidate["id"])
            if passage and (document_id is None or passage["document_id"] == str(document_id)):
                passage.update(candidate)
                passage["match_type"] = "exact and related" if candidate["keyword_rank"] and candidate["semantic_rank"] else "keyword" if candidate["keyword_rank"] else "semantic"
                passage["final_rank"] = len(results) + 1
                results.append(passage)
        if config["reranker"] != "off":
            results = self.registry.get("rerankers", config["reranker"]).implementation(query, results)
            query_terms = set(re.findall(r"\w+", query.lower()))
            for item in results:
                item["reranker_score"] = len(query_terms & set(re.findall(r"\w+", item["text"].lower())))
        counts = {}
        selected = []
        for item in results:
            cap = config["max_chunks_per_document"]
            count = counts.get(item["document_id"], 0)
            if cap is not None and count >= cap:
                continue
            counts[item["document_id"]] = count + 1
            item["final_rank"] = len(selected) + 1
            selected.append(item)
            if len(selected) >= (limit or config["result_limit"]):
                break
        return selected
