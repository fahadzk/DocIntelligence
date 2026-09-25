"""Project configuration resolution, validation, and persistence."""
import json
from datetime import datetime, timezone
from uuid import UUID

from app.config.pipeline_defaults import DEFAULTS, resolve, document_version
from app.domain.documents import DocumentError
from app.infrastructure.search_repository import SearchRepository


class PipelineConfigService:
    def __init__(self, repository: SearchRepository, registry, on_document_change=None):
        self.repository = repository
        self.registry = registry
        self.on_document_change = on_document_change

    def _require_project(self, project_id: UUID):
        with self.repository.connect() as connection:
            row = connection.execute("SELECT 1 FROM projects WHERE id=?", (str(project_id),)).fetchone()
        if row is None:
            raise DocumentError("PROJECT_NOT_FOUND", "The project could not be found.", 404)

    def overrides(self, project_id: UUID) -> dict:
        self._require_project(project_id)
        with self.repository.connect() as connection:
            row = connection.execute("SELECT overrides_json FROM project_pipeline_config WHERE project_id=?",
                                     (str(project_id),)).fetchone()
        return json.loads(row[0]) if row else {}

    def effective(self, project_id: UUID) -> dict:
        return resolve(self.overrides(project_id))

    def save(self, project_id: UUID, overrides: dict) -> dict:
        self._require_project(project_id)
        try:
            candidate = resolve(overrides)
            self.validate(candidate)
        except (TypeError, ValueError) as error:
            raise DocumentError("INVALID_PIPELINE_CONFIG", str(error), 422) from error
        old_version = document_version(self.effective(project_id))
        encoded = json.dumps(overrides, sort_keys=True)
        with self.repository.connect() as connection:
            connection.execute("""INSERT INTO project_pipeline_config VALUES (?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET overrides_json=excluded.overrides_json,
                updated_at=excluded.updated_at""",
                (str(project_id), encoded, datetime.now(timezone.utc).isoformat()))
        if self.on_document_change and document_version(candidate) != old_version:
            self.on_document_change(project_id)
        return {"defaults": DEFAULTS, "overrides": overrides, "effective": candidate}

    def state(self, project_id: UUID) -> dict:
        overrides = self.overrides(project_id)
        return {"defaults": DEFAULTS, "overrides": overrides, "effective": resolve(overrides)}

    def validate(self, config: dict):
        document = config["document"]
        search = config["search"]
        ask = config["ask"]
        selected = [("chunking", document["chunking"]["plugin"]),
                    ("embeddings", document["embedding"]["plugin"]),
                    ("vector_stores", document["vector_store"]["plugin"]),
                    ("retrieval", search["retrieval"]), ("fusion", search["fusion"]),
                    ("rerankers", search["reranker"]), ("llm_providers", ask["provider"])]
        for category, plugin_id in selected:
            self.registry.get(category, plugin_id)
        groups = [(document["chunking"], self.registry.get("chunking", document["chunking"]["plugin"])),
                  (document["embedding"], self.registry.get("embeddings", document["embedding"]["plugin"])),
                  (document["vector_store"], self.registry.get("vector_stores", document["vector_store"]["plugin"])),
                  (search, self.registry.get("retrieval", search["retrieval"])),
                  (search, self.registry.get("fusion", search["fusion"])),
                  (ask, self.registry.get("llm_providers", ask["provider"]))]
        for group, plugin in groups:
            for field in plugin.schema:
                key = field["key"]
                value = group.get(key)
                if value is None:
                    continue
                kind = field["type"]
                if kind == "boolean" and type(value) is not bool:
                    raise ValueError(f"{key} must be true or false")
                if kind in ("number", "slider"):
                    if type(value) not in (int, float) or not field.get("min", float("-inf")) <= value <= field.get("max", float("inf")):
                        raise ValueError(f"{key} is outside its supported range")
                if kind == "select" and value not in field["options"]:
                    raise ValueError(f"Unsupported {key}: {value}")
                if kind == "model_select" and not isinstance(value, str):
                    raise ValueError(f"Invalid {key}")
        chunking = document["chunking"]
        if chunking["preserve_segments"] is not True or chunking["preserve_headings"] is not True:
            raise ValueError("Source segments and available heading references must be preserved for citations")
        if chunking["overlap"] >= chunking["chunk_size"] or chunking["min_chunk_size"] > chunking["max_chunk_size"]:
            raise ValueError("Chunk sizes and overlap are inconsistent")
        if search["keyword_weight"] + search["semantic_weight"] <= 0:
            raise ValueError("At least one fusion weight must be positive")
        if not 1 <= ask["evidence_count"] <= 12 or not 1 <= ask["evidence_candidates"] <= 50:
            raise ValueError("Evidence limits are outside their supported range")
        if not 100 <= ask["evidence_characters"] <= 12000:
            raise ValueError("Evidence character budget is outside its supported range")
        if ask["grounding"] not in ("sources_only", "sources_plus_model"):
            raise ValueError("Unknown grounding mode")
        if ask["answer_style"] not in ("concise", "detailed", "bullet_summary", "research"):
            raise ValueError("Unknown answer style")
        if type(ask["require_citations"]) is not bool:
            raise ValueError("Require citations must be true or false")
        if not isinstance(ask["model"], str) or len(ask["model"]) > 160:
            raise ValueError("Invalid answer model")
