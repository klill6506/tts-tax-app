# TTS Tax App — Project Instructions

## Product Vision
Professional tax preparation software for small/mid firms (~3,000 returns, ~9 preparers).
- **Phase 1 target**: 1120S (S-Corp) returns
- **Windows-first** desktop app for preparers
- Replaces legacy tax software with modern, maintainable architecture

## Stack
| Layer | Technology |
|-------|-----------|
| Server | Django 5.2 LTS + Django REST Framework |
| Database | PostgreSQL 16 (multi-user, shared) |
| Desktop Client | Electron (Windows first) |
| UI | Tailwind UI / Tailwind Plus |
| Dev DB | Postgres in Docker Compose |
| Dependency Mgmt | Poetry |
| Remote Access | Firm's existing VPN (no custom remote) |
| AI | Help/Q&A layer (separate module, internet OK) |

## Project Rules (enforced)
- **No real PII in dev** — use synthetic/fake data only
- **No secrets in repo** — all credentials via `.env` (which is gitignored)
- **Migrations required** — every model change needs a migration
- **Tests required** — every ticket must include tests; tests must pass before merge
- **Postgres only** — no SQLite fallback in settings

## How to Run

### Prerequisites
- Docker Desktop (for Postgres)
- Python 3.13+
- Poetry

### Start Postgres
```powershell
cd D:\dev\tts-tax-app
docker compose up -d
```

### Start Django dev server
```powershell
cd D:\dev\tts-tax-app\server
poetry install
poetry run python manage.py migrate
poetry run python manage.py runserver
# Or use: .\scripts\run_dev.ps1
```

### Run tests
```powershell
cd D:\dev\tts-tax-app\server
poetry run pytest
```

## Directory Layout
```
tts-tax-app/
├── docker-compose.yml          # Postgres for dev
├── CLAUDE.md                   # This file (project-wide)
├── docs/                       # PROJECT_CHARTER, ADRs, DEVLOG
├── server/                     # Django backend
│   ├── config/settings/        # base.py + dev.py (+ prod.py later)
│   ├── apps/                   # Django apps (core, firms, accounts, etc.)
│   ├── tests/                  # pytest test files
│   └── scripts/                # Dev scripts (run_dev.ps1)
└── client/                     # Electron app (future)
```

## Definition of Done (per ticket)
- [ ] Code matches acceptance criteria
- [ ] Migrations created and applied
- [ ] Tests written and passing
- [ ] No secrets or PII in committed code
- [ ] Code reviewed by Architect/QA supervisor prompt
- [ ] Code reviewed by Security supervisor prompt
