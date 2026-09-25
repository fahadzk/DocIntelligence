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

## Background operational logs

Operational events for imports, extraction, chunking, local embeddings, SQLite FTS5, Chroma, search, and Ask are written in the background to JSON Lines. The development path is `data/logs/document-intelligence.jsonl`; production uses the configured application data directory. Files rotate at 10 MB and retain five backups. The log records safe metadata, timings, counts, and errors, never document text, questions, or generated answers. No dashboard, polling, logging API, or SQLite activity writes are used.

## Pipeline Lab

Open a project and choose **Pipeline Lab** under Advanced in the sidebar for technical experiments. Its DOCUMENT, SEARCH, and ASK tabs show the effective settings and expose controls supplied by the built-in Python plugin registry. Changes save automatically after a short pause; the header shows pending, saving, saved, or retryable failure. Preview, Search, and Ask become available after saving. Lab has separate passage, FTS, and Chroma indexes; changing its document settings rebuilds only Lab-derived data. Return to Documents, Search, or Ask in the sidebar at any time; Standard indexing and answers still use the original defaults.

**Settings → Appearance** offers Light, Dark, and System themes. The choice is saved locally and takes effect immediately; System follows the operating-system preference. The desktop layout adapts to narrower windows without hiding project navigation.

Use the small control at the top of the workspace to collapse the sidebar to icons or pin it open. The collapsed rail shows only the current project; click its icon to open the full project list, or hover over the rail to peek at it. The pinned choice persists. The project list scrolls independently, so Settings stays visible at the bottom. Scrollbars are thin when expanded and hidden in the collapsed rail.

DOCUMENT previews chunks without changing either index. The built-in choices are sliding window, paragraph-aware semantic chunking, and local-LLM chunking; the latter two require installed local models. The registered embedding/vector implementations currently remain BGE Small/FastEmbed and Chroma/L2. SEARCH offers keyword, semantic, or hybrid retrieval, RRF or weighted rank fusion, and an optional term-overlap reranker. The inspector labels real BM25, L2 distance, ranks, and fusion values. ASK shows the passages actually sent to the model and preserves supporting evidence and original-opening links.

Lab can optionally call OpenAI, Anthropic, or Google with your own account and key. **Manage Providers** stores keys in the operating system credential vault, never in SQLite or browser storage; **Test Connection** and **Refresh Models** query the provider. Cloud Ask sends your question and selected passage text to that provider and may incur charges. Standard and local Lab operation need no cloud account. Model knowledge, when enabled, is displayed separately as unverified and is never cited as a document source. See [ADR-005](docs/decisions/ADR-005-pipeline-lab.md) for index isolation and limitations.
