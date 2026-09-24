# ADR-004: Project activity observability

**Status:** Accepted — 2026-09-24

## Decision

Store structured project activity in SQLite migration v4. Events are project-scoped and use an operation, human-readable message, safe metadata, severity, optional document ID, duration, and timestamp. The frontend fetches events only when the Activity tab is selected. It refreshes every five seconds by default, and the user can choose 10, 15, 30, or 60 seconds, disable polling, or refresh on demand.

## Rationale

Users need to see local processing steps and performance without consulting terminals. SQLite preserves events across restarts and avoids exposing backend internals directly to the frontend. The event payload excludes raw document content, prompts, and generated answers to preserve local privacy and avoid unnecessarily duplicating sensitive material.

## Consequences

New work records document import/extraction, fixed chunking settings, embedding provider/vector store, index persistence, retrieval, local generation, citation validation, errors, counts, and elapsed time. Older activity does not exist retroactively. Activity rows are deleted with their project.