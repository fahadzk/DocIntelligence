"""Bundled strategies. Adding another module beside this one extends discovery."""
from app.plugins.registry import Plugin
from app.plugins import strategies
from app.infrastructure.local_models import LocalEmbeddings, LocalLLM, ChromaVectorStore


def field(key, label, kind, **options):
    return {"key": key, "label": label, "type": kind, **options}


PLUGINS = [
    Plugin("sliding_window", "Sliding Window", "Character windows inside source segments.", "chunking", (
        field("unit", "Unit", "select", options=["characters"]),
        field("chunk_size", "Chunk size", "number", min=100, max=4000),
        field("overlap", "Overlap", "number", min=0, max=1000),
        field("preserve_segments", "Preserve source segments (required for citations)", "boolean", readonly=True),
        field("preserve_headings", "Preserve headings where available", "boolean", readonly=True)),
        {"source_locations": True}, strategies.sliding_window),
    Plugin("semantic", "Semantic", "Split at paragraph meaning changes using the local embedding model.", "chunking", (
        field("sensitivity", "Sensitivity", "slider", min=0.05, max=0.95, step=0.05),
        field("min_chunk_size", "Minimum characters", "number", min=50, max=4000),
        field("max_chunk_size", "Maximum characters", "number", min=100, max=4000)),
        {"requires_embeddings": True, "source_locations": True}, strategies.semantic),
    Plugin("llm", "LLM", "Suggest paragraph boundaries with the installed local model.", "chunking", (
        field("model", "Chunking model", "model_select"),
        field("chunk_by", "Chunk by", "select", options=["topic", "section", "concept"]),
        field("max_chunk_size", "Maximum characters", "number", min=100, max=4000),
        field("preserve_headings", "Preserve headings", "boolean")),
        {"requires_answer_model": True, "source_locations": True}, strategies.llm),
    Plugin("fastembed_bge_small", "BGE Small / FastEmbed", "Local ONNX English embeddings, 384 dimensions.", "embeddings", (
        field("model", "Model", "select", options=["BAAI/bge-small-en-v1.5"]),),
        {"local": True, "dimensions": 384}, LocalEmbeddings),
    Plugin("chroma", "Chroma", "Persistent local vector collection.", "vector_stores", (
        field("distance", "Distance", "select", options=["l2"]),),
        {"local": True}, ChromaVectorStore),
    Plugin("keyword", "Keyword", "SQLite FTS5 and BM25 ordering.", "retrieval", (
        field("keyword_candidates", "Candidates", "number", min=1, max=100),
        field("result_limit", "Results", "number", min=1, max=50)),
        {"source": "SQLite FTS5"}, lambda config: ("keyword",)),
    Plugin("semantic", "Semantic", "Chroma vector retrieval.", "retrieval", (
        field("semantic_candidates", "Candidates", "number", min=1, max=100),
        field("result_limit", "Results", "number", min=1, max=50),
        field("similarity_threshold", "Maximum L2 distance", "number", min=0, max=10),
        field("max_chunks_per_document", "Max chunks per document", "number", min=1, max=50)),
        {"requires_embeddings": True}, lambda config: ("semantic",)),
    Plugin("hybrid", "Hybrid", "Keyword and semantic candidates combined by fusion.", "retrieval", (
        field("keyword_candidates", "Keyword candidates", "number", min=1, max=100),
        field("semantic_candidates", "Semantic candidates", "number", min=1, max=100),
        field("result_limit", "Results", "number", min=1, max=50),
        field("max_chunks_per_document", "Max chunks per document", "number", min=1, max=50)),
        {"requires_embeddings": False}, lambda config: ("keyword", "semantic")),
    Plugin("rrf", "Reciprocal Rank Fusion", "Combine ranks without pretending raw scores are comparable.", "fusion", (
        field("rrf_constant", "RRF constant", "number", min=1, max=200),),
        {}, lambda rank, config, source: strategies.rrf(rank, config["rrf_constant"])),
    Plugin("weighted", "Weighted rank fusion", "Combine rank contributions with chosen weights.", "fusion", (
        field("semantic_weight", "Semantic weight", "slider", min=0, max=1, step=0.05),
        field("keyword_weight", "Keyword weight", "slider", min=0, max=1, step=0.05)),
        {}, lambda rank, config, source: strategies.weighted(rank, config[source + "_weight"])),
    Plugin("off", "Off", "Keep retrieval order.", "rerankers", (), {}, lambda query, candidates: candidates),
    Plugin("lexical", "Term overlap", "Reorder candidates by matching query terms.", "rerankers", (),
           {"score": "matching_query_terms"}, strategies.lexical_rerank),
    Plugin("llamacpp", "Local Qwen / llama.cpp", "App-managed offline answer model.", "llm_providers", (
        field("model", "Model", "select", options=["qwen2.5-1.5b-instruct-q4_k_m.gguf","qwen2.5-0.5b-instruct-q4_k_m.gguf"]),
        field("temperature", "Temperature", "slider", min=0, max=1, step=0.05),
        field("max_output_tokens", "Maximum output tokens", "number", min=64, max=2048)),
        {"local": True, "model_discovery": False, "temperature": True,
         "streaming": False, "system_prompt": True}, LocalLLM),
]

