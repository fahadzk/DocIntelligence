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

Use **Search** to find passages immediately by exact terms. The optional local semantic model adds paraphrase search. **Ask** uses the selected project answer provider and shows supporting document passages. The embedding and app-managed llama.cpp models can be installed from the app's setup controls. You can also use Ollama and any model installed in your local Ollama instance; see [Local Ollama models](#local-ollama-models). No account or API key is needed for either local option. The app-managed answer model is approximately 1.07 GB and needs roughly 3 GB available RAM. If less than 2.5 GB is free when it loads, the app gives a memory warning. Search remains usable.

Files and extracted artifacts are stored in the configured `DOCUMENT_INTELLIGENCE_DATA_DIR` (default: project `data/` during development). The original source file remains untouched. The import limit defaults to 50 MB and is configurable with `DOCUMENT_INTELLIGENCE_MAX_DOCUMENT_BYTES`.

SQLite stores project/document metadata, source-located passages, and the FTS5 keyword index. Chroma vectors and downloaded models live under `data/vectors/` and `data/models/`. The **Rebuild index** action in Search safely regenerates passage and vector indexes from retained extracted text. Scanned PDFs and other files without usable text remain excluded until OCR is added in a later phase.


## Local Ollama models

1. Install Ollama for Windows from [ollama.com/download](https://ollama.com/download/windows) and start Ollama.
2. Download a model through Ollama. For example, in PowerShell run:

   ```powershell
   ollama pull llama3.2
   ```

3. Run `ollama list` to confirm the model is installed.
4. In the app, open the project's **Pipeline Lab > ASK** tab, set **Provider** to **Ollama (local)**, then select **Refresh Models**. Models listed by your local Ollama instance will appear in the model picker. Choose one and select **Save & Apply**.

The app reads the local Ollama model list from `http://localhost:11434`. Any model available to that Ollama instance can be selected; the app does not download the Ollama model itself. Ask in the project's regular workspace then uses the saved provider and model. Each project keeps its own provider configuration.


## Background operational logs

Operational events for imports, extraction, chunking, local embeddings, SQLite FTS5, Chroma, search, and Ask are written in the background to JSON Lines. The development path is `data/logs/document-intelligence.jsonl`; production uses the configured application data directory. Files rotate at 10 MB and retain five backups. The log records safe metadata, timings, counts, and errors, never document text, questions, or generated answers. No dashboard, polling, logging API, or SQLite activity writes are used.

## Pipeline Lab

Open a project and choose **Pipeline Lab** under Advanced in the sidebar to configure its document, search, and answer pipeline. Its DOCUMENT, SEARCH, and ASK tabs expose controls supplied by the built-in Python plugin registry. Changes remain drafts until you select **Save & Apply**. Changing document settings reindexes that project's shared document index; search and answer settings take effect on the next request. Basic Search and Ask use the same saved project settings.

**Settings → Appearance** offers Light, Dark, and System themes. The choice is saved locally and takes effect immediately; System follows the operating-system preference. The desktop layout adapts to narrower windows without hiding project navigation.

Use the small control at the top of the workspace to collapse the sidebar to icons or pin it open. The collapsed rail shows only the current project; click its icon to open the full project list, or hover over the rail to peek at it. The pinned choice persists. The project list scrolls independently, so Settings stays visible at the bottom. Scrollbars are thin when expanded and hidden in the collapsed rail.

DOCUMENT provides a chunk preview and configures sliding-window, semantic, or local-LLM chunking; semantic chunking needs the local embedding model and LLM chunking needs the app-managed local answer model. The registered embedding/vector implementations currently remain BGE Small/FastEmbed and Chroma/L2. SEARCH configures keyword, semantic, or hybrid retrieval, RRF or weighted rank fusion, and an optional term-overlap reranker. The document and search sections retain preview and diagnostic tools for technical users.

Ask can use the app-managed llama.cpp model, local Ollama, or an optional OpenAI, Anthropic, or Google provider. For hosted providers, **Manage Providers** stores keys in the operating system credential vault, never in SQLite or browser storage; **Test Connection** and **Refresh Models** query the provider. Hosted Ask sends your question and selected passage text to that provider and may incur charges. Local providers need no cloud account. See [ADR-005](docs/decisions/ADR-005-pipeline-lab.md) for provider behavior and limitations.
