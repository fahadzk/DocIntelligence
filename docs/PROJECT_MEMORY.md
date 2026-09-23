# Project Memory

- Development uses one main agent. Do not spawn sub-agents or delegate architecture, implementation, testing, documentation, or integration work. The main agent owns decisions and completes each development increment end to end.
- The application is local-first and desktop-first. Electron delivers the UI; FastAPI owns application behavior; frontend code never accesses databases directly.
- Phase 2 adds import and extraction for text PDFs, DOCX, UTF-8 TXT, and Markdown. Search, embeddings, RAG, providers, graphs, cloud, and accounts remain out of scope until scheduled.
- Canonical development data lives in project `data/`; migration version 2 retains existing projects and imports rows once from the former `backend/data` database. Production data paths must use the Electron user data directory.
- Each document owns `documents/<project UUID>/<document UUID>/original.<type>` and `content.json`. Processing status is persisted. Startup marks incomplete work interrupted and retryable; ready requires both files.
- Import uses multipart bytes from the file picker. Backend never accepts an arbitrary source path. The default maximum is 50 MB and duplicate hashes are rejected per project.
- SQLite owns structured metadata. Document originals and extracted artifacts use the filesystem; vectors will use a replaceable vector-store adapter in a later phase.
- The visual direction is “Calm Intelligence”: neutral, evidence-first, professional, and not chatbot-centric.
- APIs return explicit Pydantic contracts. Missing projects use `PROJECT_NOT_FOUND` and no internal trace is exposed to users.
