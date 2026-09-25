# ADR-005: Standard defaults and isolated Pipeline Lab experiments

**Status:** Accepted — 2026-09-24

## Context

Technical users need to inspect and tune document, retrieval, and answer settings without changing the working Standard Workbench. The implementation, rather than older prose in ADR-003, is the source for current Standard values: Ask selects at most three passages, not five, and no longer falls back to an extractive quote after citation validation fails.

## Decision

`app.config.pipeline_defaults.DEFAULTS` records the current Standard values. Standard endpoints and UI keep their existing behavior and storage. `PipelineConfigService` resolves defaults plus validated, project-scoped Lab overrides from SQLite migration v5. The React application fetches built-in plugin metadata once per session and renders supported fields from each selected plugin's schema. Bundled Python modules are discovered and validated at backend startup. No external plugin installation or hot loading is supported.

Lab passages, FTS5 rows, and index state use dedicated tables; vectors use a dedicated Chroma collection. A document setting hash forms the Lab index version. Changing document settings schedules reindexing from retained extracted content; search or Ask settings do not rewrite documents. Missing, failed, or outdated Lab indexes never pass live evidence validation. Original documents and extracted content remain the source of truth. Standard indexes are untouched by Lab overrides.

Sliding-window chunking preserves the original 900-character/120-overlap Standard path. Lab includes paragraph-aware semantic boundaries using the installed FastEmbed model and bounded local-LLM paragraph boundaries. Both keep source-segment references. The Lab preview runs chunking without writing passages or vectors. The only currently registered embedding implementation is BGE Small/FastEmbed, and the only vector implementation is Chroma/L2; the interface lists only those implementations.

Lab search can use keyword, semantic, or hybrid retrieval. RRF and weighted rank fusion operate on candidate ranks; weighted fusion scores are rank contributions, not normalized vector similarity. The optional lexical reranker uses query-term overlap. The inspector exposes actual FTS5 BM25, Chroma L2 distance, ranks, and computed fusion/reranker values only when present. Standard remains hybrid RRF with no reranker.

Lab Ask shares the existing retrieval, evidence selection, generation, and citation validation path. The default local model remains Qwen2.5 1.5B through llama.cpp. Optional OpenAI, Anthropic, and Google providers use user-supplied credentials in the operating system credential vault via `keyring`; credentials are never returned to React or stored in SQLite. Provider model IDs are fetched from provider APIs. Source-backed claims must pass the same citation validator. Optional model-background text is labeled separately as unverified and never receives a document citation. Standard never selects a cloud provider.

## Consequences and limits

Advanced cloud calls send the selected question and passage text to the chosen provider and may incur provider charges; the UI states this before use. No cloud service is required for Standard or local Lab operation. Semantic and LLM chunking need their local models provisioned. Source boundaries remain preserved so citations retain a single source location. Current citation checks are lexical heuristics, not entailment proofs. The existing packaging limitation (bundled Python runtime) remains.
