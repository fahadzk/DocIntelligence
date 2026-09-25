# Development

## Local commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Run Electron and the Vite UI; Electron starts FastAPI. |
| `npm run build` | Type-check and build frontend and Electron code. |
| `npm test` | Run frontend unit tests. |
| `cd backend; pytest` | Run backend API tests. |
| `.\.venv\Scripts\python.exe -m ruff check backend scripts` | Lint Python application and verification code. |
| `npm run test:e2e` | Launch Electron, import, search, inspect failure, restart, and check persistence. |
| `.\.venv\Scripts\python.exe scripts\verify_phase3.py` | Offline semantic benchmark with disposable data; add `--answers` when sufficient RAM is free. |

Backend configuration uses the `DOCUMENT_INTELLIGENCE_` prefix. See `.env.example`. During development Electron uses `PYTHON_EXECUTABLE` or the project `.venv` and stores data in the project `data/` directory. The e2e test uses a separate temporary directory and port. Production packaging still needs a bundled Python runtime.

The Python test runner may stall while writing its cache in this environment; use `python -m pytest -p no:cacheprovider`. Supported imports: text PDFs via PyMuPDF, DOCX via python-docx, and UTF-8 TXT/Markdown. No OCR is included. Complex PDF columns, tables, and DOCX layout may not preserve exact visual reading order.

Search needs SQLite FTS5 (available in the tested Python 3.10 build). The first semantic/answer setup downloads models into `data/models/`; allow approximately 70 MB for embedding weights/cache and 1.1 GB for the answer model, plus temporary transfer space. The answer model uses about 3 GB RAM at a 4,096-token context and runs slowly on older dual-core CPUs. The UI retains keyword search when local inference is unavailable. Model sources and licenses are recorded in ADR-003. Use the **Rebuild index** control in Search after suspected index corruption; restarting also reindexes interrupted or outdated work. The smoke benchmark sets Hugging Face offline mode and uses cached model files only.

The Python requirements include a CPU wheel index for `llama-cpp-python` on Windows. Set `DOCUMENT_INTELLIGENCE_MODEL_DIR` to share a provisioned model cache across disposable test data directories; otherwise models are kept below `DOCUMENT_INTELLIGENCE_DATA_DIR/models`. Development builds compile the Electron shell and frontend; a self-contained installer with a bundled Python runtime remains a release-phase task.

Measured on the development Windows laptop (i7-7500U, 2 cores, 8 GB RAM, CPU inference): three short documents reached a ready hybrid index in 8.05 seconds, an offline paraphrase search took 0.02 seconds, and a grounded local answer took 11–19 seconds when memory was available. Cold loading can be substantially slower under memory pressure. Ask now declines to load the model below 2.5 GB free RAM, with Search unaffected. These are small-collection observations, not large-corpus benchmarks.

Operational logs are written asynchronously to `data/logs/document-intelligence.jsonl` in development (or `DOCUMENT_INTELLIGENCE_DATA_DIR/logs/` when configured). Each line is valid JSON and can be tailed or parsed without requiring the app UI. Logs rotate at 10 MB with five retained backups. The queue-based writer keeps file I/O outside request and processing threads; it records safe timing and configuration metadata but not document text, prompts, or answers.

## Pipeline Lab development

`GET /api/plugins` returns built-in plugin metadata and schemas. `GET/PUT /api/projects/{id}/pipeline` resolves and saves project overrides. `POST /pipeline/preview`, `/pipeline/search`, and `/pipeline/ask` use separate Lab indexes. The Lab index is versioned by its document settings; changing chunking, embedding, or vector settings schedules a rebuild. Search/Ask settings do not reprocess documents. `POST /pipeline/index/ensure` repairs missing or outdated Lab indexes; use it after a forced interruption. The Standard index/rebuild controls remain separate.

Cloud provider keys are stored with Windows Credential Locker (or the OS credential backend selected by `keyring`). They are never written to the project database, logs, or exported data. Provider connectivity and model discovery require internet access and the user's own account. Running Lab with local Qwen remains offline after setup. Tests use mocked provider responses and do not contact paid APIs.

The Electron end-to-end test uses an isolated temporary data directory. On virtualized Windows test hosts it enables software rendering and passes `--no-sandbox` to the test instance only; normal desktop launches retain Electron's sandbox defaults. Electron stores its Chromium profile under the configured app data directory so test runs do not touch the normal profile.
