# ADR-004: Background operational logging

**Status:** Accepted — 2026-09-24

## Decision

Replace the project Activity dashboard, polling API, and SQLite activity writes with standard-library queue-based background logging. Application services send privacy-safe structured events to an `OperationalLogger`. Python `QueueHandler` returns control to the caller without writing to disk; a dedicated `QueueListener` writes JSON Lines to `logs/document-intelligence.jsonl` under the configured application data directory. `RotatingFileHandler` rotates each file at 10 MB and retains five backups.

## Rationale

The operational details are useful for diagnosis but do not need to be a constantly polled product surface. Queue-based logging prevents document import, extraction, indexing, search, and Ask work from blocking on logging I/O. JSON Lines remain easy to tail, archive, or inspect with standard tooling.

## Consequences

The file records import/extraction, fixed chunking configuration, embedding/vector/FTS storage, retrieval, local generation, citation validation, errors, counts, and elapsed time. It excludes document content, user prompts, and generated answers. Existing SQLite migration 4 activity tables are deliberately left untouched for compatibility, but the application no longer writes or serves them.