# TTS Tax App — Project Charter

## Purpose
Build a modern, Windows-first professional tax preparation application targeting
small/mid accounting firms (~3,000 returns, ~9 preparers per firm).

## Phase 1 Scope: 1120S (S-Corp)
The first tax form supported will be Form 1120S. This keeps scope manageable
while delivering real value for the most common entity type at the firm.

## Architecture
- **Server**: Django + PostgreSQL on an on-prem Windows Server
- **Client**: Electron desktop app (Windows first)
- **Remote access**: Firm's existing VPN — no custom remote solution
- **AI**: Help/Q&A assistant layer (internet access OK), not core automation

## Key Decisions
1. Multi-user "real server" — not file-based returns on a shared drive
2. Database-first — returns live as records in Postgres
3. Bundled installer for office server (Django + Postgres)
4. Workstations install Electron client only
5. QuickBooks integration v1: export Trial Balance to CSV/Excel, import into app

## Team Roles
- **Bob**: Senior developer, writes implementation tickets
- **Architect/QA Supervisor**: Reviews code vs plan, tests, maintainability
- **Security Supervisor**: Reviews PII handling, auth, logging, secrets

## Build Roadmap
1. **Platform Spine** — Auth, firms, roles, entities, tax years, TB import, audit log
2. **MVP 1120S** — Core data model, K-1, depreciation, book→tax adjustments, review cockpit, PDF output
3. **Complete 1120S** — Expanded forms, state framework, tie-outs, installer polish
