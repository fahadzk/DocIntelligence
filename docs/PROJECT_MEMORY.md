# Project Memory

- Development uses one main agent. Do not spawn sub-agents or delegate architecture, implementation, testing, documentation, or integration work. The main agent owns decisions and completes each development increment end to end.
- The application is local-first and desktop-first. Electron delivers the UI; FastAPI owns application behavior; frontend code never accesses databases directly.
- Phase 2 adds import and extraction for text PDFs, DOCX, UTF-8 TXT, and Markdown. Phase 3 adds local Search and grounded Ask. OCR, graphs, cloud, and accounts remain out of scope until scheduled.
- Canonical development data lives in project `data/`; migration version 2 retains existing projects and imports rows once from the former `backend/data` database. Production data paths must use the Electron user data directory.
- Each document owns `documents/<project UUID>/<document UUID>/original.<type>` and `content.json`. Processing status is persisted. Startup marks incomplete work interrupted and retryable; ready requires both files.
- Import uses multipart bytes from the file picker. Backend never accepts an arbitrary source path. The default maximum is 50 MB and duplicate hashes are rejected per project.
- SQLite migration version 3 owns source-located passages, FTS5 keyword search, and durable index state. Chroma vectors are derived and replaceable; original content.json remains the source of truth for rebuilding.
- Local FastEmbed BGE-small English embeddings (MIT) and Qwen2.5 1.5B Instruct GGUF answers (Apache 2.0) are optional, app-provisioned, and work offline after download. Keyword search never requires a model.
- The answer runtime checks for at least 2.5 GB free RAM before a cold load. On the development dual-core 8 GB Windows laptop, leave closer to 3 GB free for practical performance; Search still works when Ask cannot load.
- Citation evidence is resolved through live, project-scoped SQLite passages; deleted documents cannot be cited. A cited model response still requires user judgment and is not a factual guarantee.
- The visual direction is “Calm Intelligence”: neutral, evidence-first, professional, and not chatbot-centric.
- APIs return explicit Pydantic contracts. Missing projects use `PROJECT_NOT_FOUND` and no internal trace is exposed to users.
- Operational events use standard-library queue-based JSON Lines logging at `logs/document-intelligence.jsonl` below the configured data directory. File I/O is handled by a background listener, files rotate at 10 MB with five backups, and logs carry safe metadata/timings but never raw document text, prompts, or generated answers. The former migration 4 activity table is retained only for existing-database compatibility.
