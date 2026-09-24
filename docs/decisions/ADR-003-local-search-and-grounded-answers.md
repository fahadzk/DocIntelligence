# ADR-003: Local search and grounded answers

**Status:** Accepted - 2026-09-24

## Context

Phase 3 needs offline search and answers on a Windows laptop with an Intel i7-7500U (2 cores), 8 GB RAM, and no suitable inference GPU. Imported content already has PDF page or paragraph references. A hosted API would violate the default no-key, no-recurring-charge requirement.

## Decision

SQLite migration v3 stores deterministic passages, source offsets, FTS5 content, and indexing states. Extracted `content.json` remains the rebuild source. The index version includes chunking and embedding choices; startup rebuilds incomplete or mismatched indexes. SQL validates project, document readiness, content hash, and version for every result/citation, including IDs returned by Chroma. Explicit deletion removes derived rows and vectors.

The local embedding provider is FastEmbed's quantized ONNX form of [BAAI BGE-small English v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5), [MIT licensed](https://huggingface.co/BAAI/bge-small-en-v1.5). [FastEmbed](https://github.com/qdrant/fastembed) is CPU-oriented; its [quantized artifact](https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q) is downloaded on request. The measured Windows cache occupied about 64 MB; the UI budgets roughly 70 MB. Chroma is a replaceable vector-store adapter. Reciprocal-rank fusion combines keyword and vector ranks.

The answer provider is [Qwen2.5 1.5B Instruct GGUF Q4_K_M](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF), Apache 2.0, 1.07 GB, using the CPU [llama-cpp-python wheel](https://github.com/abetlen/llama-cpp-python). It is downloaded only when the user chooses setup. Approximately 3 GB free RAM is recommended; a cold load is refused below 2.5 GB free rather than letting the OS thrash. Older CPUs may take tens of seconds per answer. Search stays available without it.

Ask receives at most five bounded project passages. The model is instructed to treat document text as untrusted, abstain when unsupported, and cite numbered evidence. Displayed citations are checked against live, project-scoped passage records. A missing, invalid, or stale citation yields an honest unsupported/error state; citations do not independently prove every generated inference.

## Consequences

Keyword search works immediately and offline. Semantic search and Ask need a first-time download, then work offline. English-only embeddings, small-model reasoning limits, CPU latency, complex document reading order, and no OCR are known limitations. Derived indexes can be rebuilt without touching originals or existing projects. Packaging the Python runtime and local model dependencies into an installer remains a release-phase task.
