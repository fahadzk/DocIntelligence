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

- [x] Centralize current Standard defaults and add validated, project-scoped overrides.
- [x] Discover and validate bundled plugin metadata; render Lab controls from schemas.
- [x] Separate Lab passages, FTS, vectors, and index state from Standard.
- [x] Add document preview, configurable Lab retrieval and Ask context inspection.
- [x] Add optional OS-vault cloud credentials and provider model discovery.
- [x] Cover registry, configuration, isolation, chunking, citations, UI fields, and desktop switching.
