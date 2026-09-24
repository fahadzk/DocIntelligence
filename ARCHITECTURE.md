# Architecture

Document Intelligence is a local desktop application. Electron owns the application lifecycle and starts the local FastAPI process. It waits for `GET /health` before loading the React UI.

`frontend/` is a React + TypeScript Vite application. It only accesses application data through HTTP APIs. `electron/` contains only desktop lifecycle concerns. `backend/app/api` handles HTTP and Pydantic contracts; `application` contains use cases; `domain` holds core concepts; and `infrastructure` contains persistence adapters.

SQLite stores project and document metadata. Migration version 2 adds the `documents` table without replacing existing projects. A one-time migration also imports project rows from the former `backend/data` development location into the canonical `data/` database. Original files and extracted JSON segments live under `data/documents/<project ID>/<document ID>/` and are never stored as database blobs.

Document imports use multipart uploads from the native file picker. The application layer validates size and type, copies bytes into owned storage, hashes content, and records a processing state. FastAPI background tasks extract content through a focused extractor interface. SQLite records the final state only after the extracted artifact is written atomically. On startup, interrupted processing is marked failed with a retry option; ready documents missing an original or content artifact are marked failed.

PDF segments retain page numbers. DOCX, TXT, and Markdown segments retain heading or paragraph references where available. Phase 3 splits each segment into bounded passages without crossing a source boundary. Each passage retains its segment, page/paragraph reference, and character offsets.

SQLite migration version 3 adds passages, an FTS5 keyword index, and per-document indexing state. Existing projects and imported files are retained. A startup recovery worker rebuilds missing, interrupted, outdated, or changed indexes. The UI shows persisted indexing state; only ready documents with matching content hashes and index versions can be retrieved. Deletion removes FTS rows and vectors, while SQL joins prevent stale vector IDs from appearing if vector cleanup fails.

The optional FastEmbed ONNX provider uses the quantized BGE-small English model (MIT) for CPU embeddings. Chroma stores vectors behind a narrow `VectorStore` boundary. Rank fusion combines FTS and semantic result order without showing raw similarity scores. The local Qwen2.5 1.5B Instruct GGUF model (Apache 2.0) runs through llama.cpp Python bindings on CPU. Its setup is app-managed; no remote inference is used. Retrieved passages are bounded before prompting, document text is explicitly treated as untrusted, and citation numbers are checked against project-scoped live passages before display. This is evidence validation, not a guarantee that every generated interpretation is correct.

Models are downloaded on request into `data/models/` (or the configured model directory); vectors live in `data/vectors/`. Keyword search works before either model is installed. Extraction hands indexing to a separate background worker so document reading does not wait for embeddings. Model setup also runs in the background. An interrupted index remains in a non-ready state and is rebuilt at the next startup. Changing the chunk or embedding version triggers reindexing, and Search offers a manual rebuild path. Ask checks free memory before a cold model load and returns a clear low-memory state without affecting Search.

## Boundaries

Embedding, LLM, and vector-store adapters are kept in `infrastructure/local_models.py`; application services depend on their focused methods. Reranking and hosted providers are not implemented.

## Background operational logging

Operational work records are produced through a focused logging boundary and immediately queued with Python standard-library `QueueHandler`. A dedicated `QueueListener` performs JSON Lines file I/O on a background thread, so import, extraction, indexing, search, and answer workers do not wait for log disk writes. The rotating output is `logs/document-intelligence.jsonl` beneath the configured data directory (10 MB per file, five backups). It includes safe event metadata, durations, counts, and error details; it never records document text, questions, or generated answers. Migration version 4’s prior activity table is left intact in existing databases for compatibility but is no longer written or exposed.