# Work Plan

## Phase 1 — Application foundation

- [x] Desktop shell, local backend lifecycle, and readiness check
- [x] React workspace shell and project navigation
- [x] SQLite project CRUD API and project-management UI
- [x] Reusable Phase 1 design system and environment reconnaissance
- [x] Run backend, frontend, and desktop workflow tests
- [ ] Validate a packaged desktop installer on Windows (release phase)

## Phase 2 - Document import and reading

- [x] Migrate Phase 1 project databases and add document metadata
- [x] Retain originals and extracted content in project-scoped storage
- [x] Extract PDF, DOCX, TXT, and Markdown with source references
- [x] Surface progress, failures, retry, reading, original opening, and deletion
- [x] Cover import, isolation, recovery, deletion, and Electron restart

## Phase 3 - Search and grounded answers

- [x] SQLite FTS5 passages with source offsets and project scoping
- [x] Local ONNX embeddings and Chroma behind provider boundaries
- [x] Hybrid retrieval, model setup UI, Search and Ask workspaces
- [x] Evidence IDs, project-scoped citation validation, and index recovery/rebuild
- [x] Backend, frontend, and Electron search/restart tests
- [x] Complete local answer-model download and record CPU answer benchmark

## Later phases (not in current scope)

- OCR and research-intelligence workflows
- Packaged installer validation

## Post-Phase 3 observability

- [x] Add background JSON Lines operational logging for document, retrieval, and answer operations.
- [x] Keep operational file I/O off request and processing threads with queue-based logging.

## Pipeline Lab

- [x] Centralize defaults and persist validated configuration overrides per project.
- [x] Apply the selected project settings to the shared Basic Search and Ask workflows.
- [x] Reindex readable documents after document pipeline settings change; apply retrieval and Ask settings on the next request.
- [x] Render document, search, and answer configuration in separate tabs with one Save & Apply action.
- [x] Use one grounded Ask API for Basic mode and selected local or hosted providers.
- [x] Add local Ollama model discovery and non-streaming `/api/chat` generation.
- [x] Keep optional hosted provider credentials in the OS credential store.
- [x] Retain chunk preview and diagnostic retrieval/index views.
