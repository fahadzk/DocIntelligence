# ADR-001: Electron with a local FastAPI service

**Status:** Accepted — 2026-09-23

## Context

The product is a downloadable, local-first desktop application that needs clean UI, application, and infrastructure boundaries.

## Decision

Use Electron for the desktop lifecycle, React + TypeScript + Vite for the renderer, and a local FastAPI process for application behavior. Electron launches FastAPI bound to loopback and waits for `/health` before loading the UI.

## Consequences

The UI stays independent from persistence and AI vendors. Packaging must bundle a compatible Python runtime in a future packaging increment.
