"""Current Standard values and the only place Pipeline Lab resolves overrides."""
from copy import deepcopy
import hashlib
import json

DEFAULTS = {
    "document": {
        "chunking": {"plugin": "sliding_window", "unit": "characters", "chunk_size": 900,
                     "overlap": 120, "preserve_segments": True, "preserve_headings": True,
                     "boundary_search_start": 550,
                     "sensitivity": 0.35, "min_chunk_size": 200, "max_chunk_size": 900,
                     "chunk_by": "topic", "model": "qwen2.5-1.5b-instruct-q4_k_m.gguf"},
        "embedding": {"plugin": "fastembed_bge_small", "model": "BAAI/bge-small-en-v1.5"},
        "vector_store": {"plugin": "chroma", "distance": "l2"},
    },
    "search": {
        "retrieval": "hybrid", "keyword_candidates": 30, "semantic_candidates": 30,
        "result_limit": 12, "fusion": "rrf", "rrf_constant": 40,
        "keyword_weight": 0.5, "semantic_weight": 0.5,
        "similarity_threshold": None, "max_chunks_per_document": None, "reranker": "off",
    },
    "ask": {
        "provider": "llamacpp", "model": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "model_repository": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        "context_tokens": 4096, "temperature": 0.0, "max_output_tokens": 300,
        "seed": 42, "history": False, "stream": False,
        "threads": 2, "gpu_layers": 0, "chat_format": "chatml",
        "minimum_free_bytes": 2500000000,
        "grounding": "sources_only", "evidence_candidates": 12,
        "evidence_count": 3, "evidence_characters": 4800,
        "require_citations": True, "answer_style": "concise",
    },
}


def resolve(overrides: dict | None = None) -> dict:
    effective = deepcopy(DEFAULTS)
    for section, options in (overrides or {}).items():
        if section not in effective or not isinstance(options, dict):
            raise ValueError(f"Invalid pipeline section: {section}")
        for key, value in options.items():
            if key not in effective[section]:
                raise ValueError(f"Invalid {section} option: {key}")
            if isinstance(effective[section][key], dict):
                if not isinstance(value, dict) or set(value) - set(effective[section][key]):
                    raise ValueError(f"Invalid {section}.{key} options")
                effective[section][key].update(value)
            else:
                effective[section][key] = value
    return effective


def document_version(config: dict) -> str:
    encoded = json.dumps(config["document"], sort_keys=True, separators=(",", ":"))
    return "lab-" + hashlib.sha256(encoded.encode()).hexdigest()[:16]

