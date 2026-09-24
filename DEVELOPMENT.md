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
