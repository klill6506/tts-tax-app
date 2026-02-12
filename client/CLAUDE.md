# Client — Electron Conventions

> **Note**: The Electron client has not been started yet. This file documents
> the planned conventions for when development begins.

## Stack
- Electron (Windows-first)
- Tailwind UI / Tailwind Plus for components
- IPC for renderer ↔ main process communication

## IPC Boundaries
- Renderer process: UI only, no direct DB or filesystem access
- Main process: handles API calls to Django server, file operations, config
- All server communication goes through main process → Django REST API

## Environment Config
- Server URL stored in a local config file (not hardcoded)
- Default: `http://127.0.0.1:8000` for local dev

## UI Patterns
- Keyboard-first: all primary actions must be keyboard-accessible
- Global search placeholder (Cmd/Ctrl+K style)
- Follow Sherpa UI Design System from global CLAUDE.md
- Light mode default

## Security
- Never store credentials in renderer process
- Auth tokens held in main process only
- No PII in console.log or dev tools output
