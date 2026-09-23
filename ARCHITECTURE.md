# Architecture

Document Intelligence is a local desktop application. Electron owns the application lifecycle and starts the local FastAPI process. It waits for `GET /health` before loading the React UI.

`frontend/` is a React + TypeScript Vite application. It only accesses application data through HTTP APIs. `electron/` contains only desktop lifecycle concerns. `backend/app/api` handles HTTP and Pydantic contracts; `application` contains use cases; `domain` holds core concepts; and `infrastructure` contains persistence adapters.

SQLite stores project and document metadata. Migration version 2 adds the `documents` table without replacing existing projects. A one-time migration also imports project rows from the former `backend/data` development location into the canonical `data/` database. Original files and extracted JSON segments live under `data/documents/<project ID>/<document ID>/` and are never stored as database blobs.

Document imports use multipart uploads from the native file picker. The application layer validates size and type, copies bytes into owned storage, hashes content, and records a processing state. FastAPI background tasks extract content through a focused extractor interface. SQLite records the final state only after the extracted artifact is written atomically. On startup, interrupted processing is marked failed with a retry option; ready documents missing an original or content artifact are marked failed.

PDF segments retain page numbers. DOCX, TXT, and Markdown segments retain heading or paragraph references where available. These source references can support later citations, but Phase 2 does not create search indexes.

## Boundaries

Future LLM, embedding, reranking, and vector-store integrations must be introduced behind focused infrastructure interfaces. Domain and application code must not depend on a vendor SDK.
