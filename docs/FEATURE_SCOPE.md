# Future Feature Scope

This file is the canonical backlog for features that are planned or being considered for Document Intelligence. It complements `WORKPLAN.md`, which records work that has already been scheduled or completed.

When starting a new development increment, read this file, list the features whose status is `Ready` or `Proposed`, and ask which feature ID to implement. Update the selected feature's status and decisions here as the work progresses.

## Product direction

Document Intelligence should remain a local-first, evidence-first desktop workspace. Future features should preserve these rules:

- A user can understand what data is stored locally and what, if anything, is sent to a hosted provider.
- Original documents and extracted content are authoritative. Passages, keyword indexes, embeddings, and vector stores are derived and can be rebuilt.
- Answers remain grounded in live project sources and show verifiable citations.
- Project configuration is explicit, versioned, and portable where possible.
- Credentials, secrets, downloaded model binaries, caches, and operational logs are never silently shared.
- Destructive, expensive, or external actions require a clear preview and user confirmation.

## Status and priority

- **Ready**: sufficiently defined to start implementation.
- **Proposed**: in scope, but needs design decisions before implementation.
- **In progress**: currently being implemented.
- **Done**: implemented and verified.
- **Deferred**: intentionally postponed.

`P0` is the next major capability, `P1` is a high-value follow-up, and `P2` is a longer-term enhancement.

## Feature index

| ID | Feature | Priority | Status | Suggested sequence |
| --- | --- | --- | --- | --- |
| F-001 | Portable project export and import | P0 | Ready | 1 |
| F-002 | Project templates and configuration profiles | P1 | Proposed | 2 |
| F-003 | Pipeline evaluation and recommended settings | P1 | Proposed | 3 |
| F-004 | Backup, restore, and project snapshots | P1 | Proposed | 4 |
| F-005 | OCR for scanned documents and images | P1 | Proposed | 5 |
| F-006 | Metadata, tags, filters, and saved views | P1 | Proposed | 6 |
| F-007 | Ask sessions, saved research, and answer export | P1 | Proposed | 7 |
| F-008 | Additional file types and controlled data sources | P2 | Proposed | 8 |
| F-009 | Cross-project search and comparison | P2 | Proposed | 9 |
| F-010 | Interoperability with other RAG tools | P2 | Proposed | 10 |
| F-011 | Research intelligence and knowledge extraction | P2 | Proposed | 11 |
| F-012 | Safe extension and plugin packaging | P2 | Proposed | 12 |
| F-013 | Context-aware rolling-window LLM chunking | P1 | Proposed | 13 |

---

## F-001 — Portable project export and import

**Priority:** P0  
**Status:** Ready

### Goal

Let a user export a project from the UI and import it into another Document Intelligence workspace. The package must retain the project's reproducible configuration and may include its documents and extracted data.

### User experience

The project menu gains **Export project** and the project list gains **Import project**.

Export offers three clearly described package modes:

1. **Configuration only** — project metadata, pipeline settings, and optional reusable prompts/profiles; no document content.
2. **Configuration + source documents** — configuration and retained originals. The destination re-extracts, re-chunks, and reindexes them.
3. **Portable project** — configuration, originals, and extracted `content.json` artifacts. The destination can validate the artifacts and rebuild all derived indexes without repeating extraction.

Before writing the package, the UI shows its estimated size, included document count, missing/failed documents, whether document text is included, and a privacy warning. Export progress can be cancelled safely. Import first shows a preview and compatibility report, then creates a new project by default.

### Portable package

Use a versioned archive extension such as `.diproj`. The archive should contain documented, tool-neutral files rather than a copied live SQLite database.

Suggested version 1 layout:

```text
manifest.json
project.json
pipeline.json
documents/
  <portable-document-id>/
    metadata.json
    original.<type>       # optional by export mode
    content.json          # optional by export mode
checksums.sha256
```

`manifest.json` should include:

- format name and semantic format version;
- exporting application version and export timestamp;
- package mode and declared capabilities;
- stable portable IDs, counts, sizes, and SHA-256 checksums;
- required and optional entries;
- content/privacy flags such as `contains_originals` and `contains_extracted_text`.

`project.json` should include the name, description, creation metadata where safe, and a schema version. It must not require source-machine UUIDs to remain database primary keys after import.

`pipeline.json` should include both saved overrides and the resolved effective configuration so the importer can distinguish user choices from inherited defaults. It should cover:

- chunking strategy and every relevant option;
- embedding plugin and model identifier;
- vector-store plugin and distance metric;
- retrieval, candidate counts, fusion, weights, thresholds, result limit, and reranker;
- Ask provider type and model identifier;
- context/output limits, temperature, seed, grounding mode, evidence selection, citation requirement, and answer style;
- configuration schema version and plugin identifiers.

The package records provider/model references but never includes API keys, credential-vault entries, downloaded model files, machine-specific paths, logs, caches, SQLite files, FTS tables, Chroma collections, or embeddings. On import, unavailable plugins, models, and providers appear in a compatibility report. The user may install/select a replacement or import with a safe fallback; substitutions are recorded rather than silently applied.

### Import rules

- Treat every archive as untrusted input: limit compressed and expanded sizes, reject absolute paths and path traversal, cap entry count, validate JSON schemas, and verify checksums before creating records.
- Extract into a temporary directory, validate completely, then commit the new project atomically.
- Generate new project, document, passage, and index identities while maintaining an internal old-to-new mapping.
- Default to **Create as new project**. A name collision gets a suggested suffix. Merging into an existing project is not part of version 1.
- Detect duplicate documents within the imported project and report skipped or conflicting items.
- Imported originals and extracted artifacts must pass the same type, size, hash, and readiness checks as normal imports.
- Rebuild passages, FTS, embeddings, and Chroma vectors locally. Never trust or import derived indexes in version 1.
- If a required model is unavailable, complete the import with an actionable `setup required` state instead of failing the whole project.
- Failed or cancelled imports leave no partially visible project and clean up their temporary files.

### Acceptance criteria for version 1

- A configuration-only project can round-trip between two clean workspaces with equivalent effective pipeline settings.
- A portable project containing supported documents can round-trip without losing originals, extracted source locations, or document hashes.
- Search and Ask work after destination-side index rebuild and required model setup.
- Credentials and model binaries are absent from the archive, verified by an automated archive-content test.
- Corrupt, oversized, incompatible, and malicious archives fail with a useful message and do not create partial projects.
- Export/import progress, cancellation, low-disk-space errors, and overwrite avoidance are covered by backend, frontend, and desktop tests.
- An exported package is deterministic where practical: stable ordering, normalized JSON, and checksums make changes inspectable.

### Later increments

- Optional archive encryption with a user-supplied passphrase.
- Selective document export.
- A signed manifest for provenance verification.
- Import merge with an explicit duplicate/conflict resolution screen.
- Redacted sharing mode that removes selected documents or metadata fields.

---

## F-002 — Project templates and configuration profiles

**Priority:** P1  
**Status:** Proposed  
**Depends on:** F-001 configuration schema

Save a project's pipeline configuration as a small reusable template, without documents. Users can start a new project from a template or apply a profile to an existing project after previewing the changes.

Profiles should support built-in, user-created, and imported variants such as **Fast local search**, **Balanced grounded Q&A**, **High-recall research**, and **Low-memory device**. Applying a document-pipeline change must explain that re-chunking/reindexing is required. Profiles reference providers and models but contain no credentials.

---

## F-003 — Pipeline evaluation and recommended settings

**Priority:** P1  
**Status:** Proposed

There is no universally best Ask configuration. Add an evaluation workspace that recommends settings for a particular project, device, and task using evidence rather than a generic label.

Users create a small evaluation set of questions, optional expected facts, and relevant documents/passages. The workspace can compare selected pipeline profiles and report:

- retrieval hit rate and ranking quality;
- citation validity and source coverage;
- groundedness/unsupported-claim checks;
- answer usefulness rated by the user or a clearly labeled optional judge model;
- index time, query latency, answer latency, memory use, and hosted-provider cost estimates;
- configuration and model versions needed to reproduce the run.

The result can be saved as **Recommended for this project**, but applying it remains an explicit user action. The first increment should compare a small number of user-selected configurations and avoid an unbounded automatic parameter search.

---

## F-004 — Backup, restore, and project snapshots

**Priority:** P1  
**Status:** Proposed  
**Depends on:** F-001 archive and validation services

Add recoverable snapshots for one project or the whole workspace. A snapshot records originals, extracted artifacts, metadata, and configuration; derived indexes may be omitted and rebuilt. Provide retention controls, disk-space estimates, integrity verification, and a restore preview. Backups should be user-directed to a chosen location and never imply cloud synchronization.

---

## F-005 — OCR for scanned documents and images

**Priority:** P1  
**Status:** Proposed

Detect PDFs with no usable text and offer local OCR. Add image import for supported formats, per-page progress, language selection, rotation/orientation handling, retry, and confidence metadata. Keep the original file, store OCR output as a derived extracted artifact, preserve page citations, and allow OCR to be rerun when its engine or settings change.

The initial version should favor a local engine and make any hosted OCR an explicit opt-in with a data-disclosure warning.

---

## F-006 — Metadata, tags, filters, and saved views

**Priority:** P1  
**Status:** Proposed

Add project-defined tags and document metadata such as author, date, source, document type, and notes. Search and Ask can filter evidence by these fields. Users can save frequently used filter combinations as views. Imported metadata must remain distinguishable from user-edited metadata, and project export/import should preserve both.

---

## F-007 — Ask sessions, saved research, and answer export

**Priority:** P1  
**Status:** Proposed

Allow users to save questions, grounded answers, citations, and notes into named research sessions. Optional multi-turn context must be visible, editable, clearable, and disabled by default until its effect on grounding is well defined. Users can export selected findings to Markdown or DOCX with project/model/configuration provenance and stable source references.

Saved answers are historical artifacts, not live truth: if a cited document is changed or deleted, the UI should mark the saved answer as stale.

---

## F-008 — Additional file types and controlled data sources

**Priority:** P2  
**Status:** Proposed

Extend ingestion through focused adapters, beginning with formats that preserve reliable source locations: HTML, EPUB, CSV, XLSX, PPTX, and email exports. Later adapters may support a user-selected folder, web page, or approved connector.

Every adapter must define ownership, refresh behavior, deletion behavior, size limits, source attribution, and whether data ever leaves the device. Background folder watching and authenticated connectors should be separate increments rather than hidden behavior in basic file import.

---

## F-009 — Cross-project search and comparison

**Priority:** P2  
**Status:** Proposed

Let a user select multiple projects for a temporary federated search or comparison without weakening project isolation. Results and citations must retain their project identity. Ask should show exactly which projects are in scope and enforce a combined evidence budget. Moving or copying documents between projects should remain an explicit action.

---

## F-010 — Interoperability with other RAG tools

**Priority:** P2  
**Status:** Proposed  
**Depends on:** F-001 and stable portable schemas

Build adapters that transform a validated `.diproj` package into documented neutral outputs—such as JSONL documents/chunks plus a manifest—or into a specific RAG tool's supported import format. Likewise, allow supported foreign exports to be mapped into a new Document Intelligence project.

An assisted mapping agent may propose field, chunking, embedding, or provider mappings, but it must:

- show a dry-run compatibility and data-loss report;
- distinguish exact mappings, substitutions, and unsupported settings;
- never copy credentials or silently upload document content;
- require confirmation before writing files or contacting another service;
- produce an audit record containing the source format, target format, mapping choices, and tool versions.

Start with the neutral JSONL/manifest export. Add named tool adapters only against stable, documented target formats.

---

## F-011 — Research intelligence and knowledge extraction

**Priority:** P2  
**Status:** Proposed

Add evidence-linked workflows such as document summaries, timelines, entity/relationship extraction, claim comparison, contradiction discovery, and duplicate/near-duplicate detection. Every generated item must link back to source passages, record the producing model/configuration, and be regenerable. A knowledge graph is a possible view of extracted evidence, not a replacement for original sources.

---

## F-012 — Safe extension and plugin packaging

**Priority:** P2  
**Status:** Proposed

Evolve the current built-in plugin registry toward installable, versioned extensions for extractors, chunkers, embedding providers, vector stores, retrieval, rerankers, and answer providers. Before user-installable code is allowed, define package signing/trust, permissions, compatibility, sandboxing expectations, failure isolation, upgrade/rollback, and how missing extensions affect imported projects.

Portable projects should identify required extensions by stable ID and compatible version range, but should never embed executable plugin code.

---

## F-013 — Context-aware rolling-window LLM chunking

**Priority:** P1
**Status:** Proposed

Replace the fixed 12-paragraph, 220-character-preview batching used by LLM chunking with token-aware rolling windows. Large documents must remain incremental; the application must never send an entire document to a model in one request.

The strategy should:

- discover the selected model's context window where the provider exposes it, with a conservative configurable fallback;
- reserve explicit budgets for system instructions, structured output, and a safety margin;
- fill each request with complete paragraphs up to the remaining input-token budget;
- carry a configurable number of paragraphs into the next request and reconcile boundary decisions in the overlap;
- split an oversized paragraph into sentence-aware subwindows instead of bypassing semantic boundary analysis;
- keep `max_chunk_size` as an independent hard limit on stored chunk size rather than treating it as the model-input limit;
- preserve page and paragraph citation metadata while processing pages and segments incrementally;
- expose progress, cancellation, retry, and resumable checkpoints for long documents;
- respect provider concurrency and rate limits, and avoid repeating successful model calls after a recoverable failure.

Initial configuration should include an automatic context-budget mode, an optional context-window override, reserved output tokens, input safety margin, and batch-overlap paragraphs. The first implementation should default to a 4,096-token context window when model metadata is unavailable and use a two-paragraph overlap.

Acceptance criteria should cover small-context local models, larger hosted models, very long paragraphs, hundreds-page PDFs, provider interruption and resume, deterministic boundary reconciliation, and enforcement of the final chunk-size limit.

## Explicitly out of scope for this backlog

- Exporting API keys, credential-vault data, authentication tokens, or other secrets.
- Bundling downloaded model binaries or third-party executable code inside a project package.
- Treating copied SQLite, FTS, Chroma, or embedding files as the portable source of truth.
- Silent upload of project content by an agent, connector, evaluation judge, or conversion tool.
- Real-time multi-user editing, accounts, hosted project storage, and automatic cloud sync until a separate security and product design is approved.
- Autonomous answers without source visibility or citation validation.

## Decisions still needed before F-001 implementation

1. Confirm the public package extension (`.diproj` is the current proposal) and MIME type.
2. Decide whether version 1 exports only all documents or also supports document selection.
3. Decide whether extracted `content.json` is included in **Portable project** by default or behind a separate checkbox.
4. Define maximum archive size, expanded size, file count, and compression-ratio limits.
5. Define the minimum older/newer package versions that the importer must accept.
6. Decide whether imports preserve original project/document creation timestamps as provenance fields.

## Change log

- 2026-10-01: Added F-013 for token-aware rolling-window LLM chunking with overlap, provider context metadata, and resumable large-document processing.
- 2026-09-30: Created the future feature scope. Defined portable project export/import as the first implementation candidate and added related roadmap features.
