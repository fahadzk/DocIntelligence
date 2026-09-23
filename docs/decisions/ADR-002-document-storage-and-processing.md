# ADR-002: Local document storage and processing

**Status:** Accepted - 2026-09-23

## Context

Phase 2 needs durable, project-scoped imports with source references and visible failure states. Phase 1 had two development database paths because launches used different working directories.

## Decision

SQLite migration version 2 stores document metadata and status. A one-time migration copies legacy project rows from `backend/data` into canonical development `data/` without deleting the former database. Original files and extracted JSON are stored in UUID-scoped directories. Content hashes detect duplicates within a project. Uploads use multipart bytes, not client-supplied filesystem paths.

FastAPI background tasks process each registered import. Stages are persisted; no percentage estimate is shown. Content is written atomically before a document becomes ready. Startup marks unfinished work interrupted with a retry action. The extraction boundary accepts a file path and type and returns source-located segments. PDF extraction uses PyMuPDF; DOCX uses python-docx; text and Markdown use UTF-8 decoding.

## Consequences

The UI remains responsive while extraction runs. Forced shutdown can interrupt a task; it is never shown as ready after restart. A default system application opens the retained original through a restricted Electron IPC call. Exact visual reading order in complex PDFs or DOCX layouts is not guaranteed. OCR, search, and embeddings are separate later decisions.
