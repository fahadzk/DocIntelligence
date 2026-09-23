# Document Intelligence

A local-first desktop workspace for organizing and reading document collections. Projects can import text-based PDF, DOCX, UTF-8 TXT, and Markdown files. Originals are retained with the project, and extracted text keeps PDF page or paragraph references.

## Quick start

Prerequisites: Node.js 22+ and Python 3.10+.

```powershell
npm install --cache .npm-cache
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
npm run dev
```

Run checks with `npm test`, `npm run build`, and from `backend`, `..\.venv\Scripts\python.exe -m pytest`.

See [Development](DEVELOPMENT.md), [Architecture](ARCHITECTURE.md), and the [work plan](docs/WORKPLAN.md).

Open a project and choose **Add documents**. Processing status and failures appear in the document list. Select a ready document to read its extracted text and source references. **Open original** opens the retained copy in the operating system's default application.

Files and extracted artifacts are stored in the configured `DOCUMENT_INTELLIGENCE_DATA_DIR` (default: project `data/` during development). The original source file remains untouched. The import limit defaults to 50 MB and is configurable with `DOCUMENT_INTELLIGENCE_MAX_DOCUMENT_BYTES`.
