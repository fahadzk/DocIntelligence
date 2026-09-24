# Document Intelligence

A local-first desktop workspace for organizing, searching, and asking questions over document collections. Projects can import text-based PDF, DOCX, UTF-8 TXT, and Markdown files. Originals are retained with the project, and extracted text keeps PDF page or paragraph references.

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

Use **Search** to find passages immediately by exact terms. The optional local semantic model adds paraphrase search; **Ask** uses a separate local answer model and shows the passages behind numbered citations. Each model is installed from the app's setup panel, with its source and size shown before download. No account or API key is needed, and once provisioned both run offline. On this development Windows machine, the semantic model occupied about 64 MB; the answer model is approximately 1.07 GB and needs roughly 3 GB available RAM. If less than 2.5 GB is free when Ask tries to load it, the app gives a clear memory warning. Search remains usable.

Files and extracted artifacts are stored in the configured `DOCUMENT_INTELLIGENCE_DATA_DIR` (default: project `data/` during development). The original source file remains untouched. The import limit defaults to 50 MB and is configurable with `DOCUMENT_INTELLIGENCE_MAX_DOCUMENT_BYTES`.

SQLite stores project/document metadata, source-located passages, and the FTS5 keyword index. Chroma vectors and downloaded models live under `data/vectors/` and `data/models/`. The **Rebuild index** action in Search safely regenerates passage and vector indexes from retained extracted text. Scanned PDFs and other files without usable text remain excluded until OCR is added in a later phase.

## Activity dashboard

Each project includes an **Activity** tab. It records structured operational events for document upload and persistence, extraction, chunking, local embeddings, SQLite FTS5, Chroma storage, search retrieval, and local answer generation. Entries include safe metadata such as storage provider, chunking configuration, counts, success or error state, and elapsed time. Document text, prompts, and answers are not saved in the activity log.

The tab refreshes every 5 seconds by default. Choose 10, 15, 30, or 60 seconds, or disable automatic refresh and use **Refresh now**. The preference is stored locally in the desktop UI. Activity records are project-scoped and retained in SQLite with project deletion.
