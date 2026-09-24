# Changelog

## 0.3.0 - 2026-09-24

- Added recoverable, versioned passage indexing, SQLite FTS5 keyword search, and local Chroma semantic search.
- Added app-managed local model setup, hybrid Search, and evidence-backed Ask with validated citation references.
- Added offline retrieval benchmark and backend/desktop tests for isolation, deletion, search, and restart.
- Kept indexing off the import completion path, added recoverable FTS rebuilds, clickable evidence citations, and a clear low-memory answer state.

## 0.2.0 - 2026-09-23

- Added versioned document migration, project-scoped retained files, duplicate detection, and recovery states.
- Added PDF, DOCX, TXT, and Markdown extraction with source references.
- Added document import, reading, retry, original opening, and deletion in the desktop workspace.
- Added backend, frontend, and Electron restart coverage for Phase 2.

## 0.1.0 — 2026-09-23

- Initialized the local-first Electron, React, and FastAPI application shell.
- Added SQLite-backed project CRUD APIs and frontend workspace UI.
- Added backend health/readiness lifecycle and foundational tests.

## Unreleased

- Replaced the Activity dashboard, API, and SQLite event writes with background JSON Lines operational logs.
- Added queue-based rotating file logging for import, extraction, chunking parameters, FastEmbed/Chroma embeddings, SQLite FTS5 indexing, hybrid search, and local Ask generation/citation validation.
- Corrected automatic answer citation recovery so model knowledge cannot be shown as document evidence; unsupported claims are rejected and source-matching fallback answers are extractive.
