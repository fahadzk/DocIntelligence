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

## Project activity records

SQLite migration version 4 adds `activity_logs`. The application records durable, project-scoped operational events rather than raw document content. Document lifecycle records cover validation, retained-original persistence, extraction, content artifact persistence, and failures. Search records keyword/semantic retrieval configuration and counts. Index records include the fixed sliding-window chunking configuration (900 characters, 120-character overlap, whitespace boundary after 550 characters), FastEmbed model, Chroma, SQLite FTS5, passage counts, and elapsed time. Ask records retrieval, llama.cpp generation, citation validation, and total time. `GET /api/projects/{project_id}/activity` exposes typed entries; the React Activity tab polls this endpoint by a user-configurable 5–60 second interval or on demand.
