# Development

## Local commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Run Electron and the Vite UI; Electron starts FastAPI. |
| `npm run build` | Type-check and build frontend and Electron code. |
| `npm test` | Run frontend unit tests. |
| `cd backend; pytest` | Run backend API tests. |
| `npm run test:e2e` | Launch Electron, import, inspect failure, delete, restart, and check persistence. |

Backend configuration uses the `DOCUMENT_INTELLIGENCE_` prefix. See `.env.example`. During development Electron uses `PYTHON_EXECUTABLE` or the project `.venv` and stores data in the project `data/` directory. The e2e test uses a separate temporary directory and port. Production packaging still needs a bundled Python runtime.

The Python test runner may stall while writing its cache in this environment; use `python -m pytest -p no:cacheprovider`. Supported imports: text PDFs via PyMuPDF, DOCX via python-docx, and UTF-8 TXT/Markdown. No OCR is included. Complex PDF columns, tables, and DOCX layout may not preserve exact visual reading order.
