# ADR-005: Project pipeline configuration and shared Ask providers

**Status:** Accepted ? 2026-09-26

## Context

Pipeline Lab is the advanced configuration surface for document chunking, retrieval, and answer generation. These are project settings: Basic Search and Ask must resolve the same saved settings so users do not get different answers or chunks depending on which workspace they opened. Reprocessing is required when document settings change; changing retrieval or answer settings takes effect on the next request.

## Decision

`app.config.pipeline_defaults.DEFAULTS` defines the defaults. `PipelineConfigService` stores validated overrides per project in SQLite. The Pipeline Lab exposes these settings and a single Save & Apply action. Applying document-pipeline changes rebuilds the shared document index from retained extracted content. Search and Ask changes are saved and used by subsequent operations without rewriting chunks.

The public grounded Ask workflow is `POST /api/projects/{project_id}/ask`. It retrieves evidence using that project's saved settings, generates through the selected provider, validates citations, and returns the same response shape to the Basic UI. Pipeline Lab no longer has a separate Ask route or Ask experiment form.

LLM providers implement the same `answer(system, prompt, model, temperature, max_output_tokens)` and `models()` interface. The built-in local providers are llama.cpp and Ollama. Ollama discovers installed models through `/api/tags` and sends non-streaming chat requests to `http://localhost:11434/api/chat`, with the system and user messages and generation options in one adapter. OpenAI, Anthropic, and Google remain optional hosted providers; their API keys stay in the operating system credential vault. Hosted providers receive the selected evidence and question.

Plugin metadata is bundled and discovered at backend startup. The UI renders supported settings from plugin schemas. External plugin installation and hot loading are not supported.

Pipeline Lab retains chunk preview and its diagnostic search/index facilities. Its configuration controls are project-scoped and the standard Basic Ask route consumes the same effective project settings. Citation validation always resolves live project-scoped passages; source locations must be preserved by chunkers.

## Consequences and limits

Changing chunking or embedding settings requires reindexing readable documents; changing retrieval or answer settings does not. Ollama must be running locally and the selected model must already be installed. Hosted providers may incur charges and receive document evidence. Citation checks are lexical heuristics, not proof of entailment. The default answer provider remains the app-managed llama.cpp model.
