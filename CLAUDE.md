# TTS Tax App — Project Instructions

## Owner
Ken — CPA, The Tax Shelter, Athens, Georgia. ~3,000 clients/year, ~9 preparers.
Building a unified tax practice platform (Sherpa) to replace fragmented SaaS tools
and potentially sell to other firms by ~2027.

## This Repo
`tts-tax-app` — The income tax preparation module. This is the **primary
development focus** of the entire Sherpa platform.

Local path: `D:\dev\tts-tax-app`

## Current Stack (What Actually Exists — Do Not Change Without Discussion)
| Layer | Technology |
|-------|-----------|
| Server | Django 5.2 LTS + Django REST Framework |
| Database | Supabase Postgres 17.6 |
| Web Client | Vite + React + TypeScript (SPA served by Django) |
| Styling | Tailwind UI / Tailwind Plus |
| Hosting | Render.com (Django + WhiteNoise serves SPA) |
| Dependency Mgmt | Poetry (Python 3.13) |
| AI Help | Gemini (IRS-grounded RAG + broad search) |
| PDF Rendering | ReportLab + pypdf + pymupdf over official IRS templates |

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
- Node.js (for React client)

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

### Start React dev server
```powershell
cd D:\dev\tts-tax-app\client
npm install
npm run dev
```

### Run tests
```powershell
cd D:\dev\tts-tax-app\server
poetry run pytest
```

## IRS Form Rendering (enforced)
- **Never draw IRS forms from scratch** — always use official IRS PDF templates as backgrounds
- **All PDF output via `apps.tts_forms.renderer`** — `render()` or `render_tax_return()`
- **Templates in `resources/irs_forms/<year>/`** — tracked in `forms_manifest.json` with URL + SHA256
- **Supporting detail → Statement pages** — never fake IRS layouts for breakdowns
- **Update templates via `scripts/update_irs_forms.py`** — downloads from irs.gov and verifies hashes
- See `.claude/rules/irs_form_rendering.md` for full details

## Directory Layout
```
tts-tax-app/
├── docker-compose.yml          # Postgres for dev
├── CLAUDE.md                   # This file (project-wide)
├── .claude/rules/              # Claude Code rules (auto-loaded)
│   └── irs_form_rendering.md   # IRS form rendering skill
├── resources/irs_forms/        # Official IRS PDF templates
│   ├── forms_manifest.json     # Template registry (URL + SHA256)
│   └── 2025/                   # Templates by tax year
├── scripts/                    # Project-wide scripts
│   └── update_irs_forms.py     # Download + verify IRS PDFs
├── server/                     # Django backend
│   ├── config/settings/        # base.py + dev.py (+ prod.py later)
│   ├── apps/                   # Django apps
│   │   ├── accounts/           # User authentication
│   │   ├── ai_help/            # Gemini-powered IRS help
│   │   ├── audit/              # Audit logging
│   │   ├── clients/            # Client/Entity management
│   │   ├── core/               # Shared utilities
│   │   ├── diagnostics/        # Return validation (planned)
│   │   ├── firms/              # Multi-firm support
│   │   ├── imports/            # Trial balance upload
│   │   ├── mappings/           # TB → form line mappings
│   │   ├── returns/            # Tax return models & logic
│   │   └── tts_forms/          # IRS form PDF rendering
│   ├── tests/                  # pytest test files
│   └── scripts/                # Dev scripts (run_dev.ps1)
└── client/                     # React web SPA
    └── src/renderer/           # React UI
```

## Definition of Done (per ticket)
- [ ] Code matches acceptance criteria
- [ ] Migrations created and applied
- [ ] Tests written and passing
- [ ] No secrets or PII in committed code

## UI/Design Standards
- **Professional, not sterile.** Think TaxWise/Lacerte aesthetic, not startup.
- **Light mode default.** Blue = primary, Green = create, Red = errors only.
- **Font**: Inter (Google Fonts) with Arial/Tahoma/Segoe UI fallbacks.
- **Colors**: Blue-800 nav, white cards, soft tinted page background.
- **Density**: Practitioners expect efficiency — avoid excessive whitespace.

## Sherpa Platform Vision (PLANNED — Not Yet Implemented)

Sherpa is a unified tax practice management platform. The long-term goal is for all
modules to share **one central Postgres database** so clients are entered once and
exist everywhere. Modules can be sold individually or as a suite.

### Modules
| Module | Status | Stack | Database |
|---|---|---|---|
| **Tax Prep** (this repo) | Active dev | Django + React SPA | Supabase Postgres |
| **1099 E-Filing** | Production | FastAPI(?) | Supabase Postgres |
| **Client Check-In** | Working | Flask | In-memory (no DB yet) |
| **Client Portal** | Planned (summer) | TBD | — |
| **Scheduling** | Planned (summer) | TBD | — |
| **Invoicing** | Planned (summer) | TBD | — |

### Database Consolidation Plan (Next Step)
- Migrate the tax app from local Docker Postgres → **Supabase Postgres** (the 1099 app is already there)
- Create a shared `clients` table as the backbone across all modules
- Add `firm_id` to all tables for multi-tenant support
- Each module only shows clients who have data in that module (e.g., 1099 app shows only the ~30 clients with 1099 records, not all 3,000)
- Clients have an `is_active` flag to hide former clients across all modules
- Keep Docker Postgres available for local/offline development

### QuickBooks Integration (Planned)
QBO stays — we don't rebuild the general ledger. Invoices and payments push to QBO via API.

## Competitive Context
No commercial Python-based tax preparation software exists. Every major competitor
(Lacerte, TaxWise, Drake, UltraTax CS, ProSeries) runs on legacy Microsoft stacks.
An AI-native, modern-stack tax platform for professional preparers is an open field.

## Development Rules
- ✅ Can create and modify files freely
- ❌ Ask before deleting files, bulk renames, or changes outside this repo
- ❌ Don't invent new ports or services without asking
- Push to GitHub regularly — that's the backup strategy
- Keep code readable — Ken is a CPA learning to code, not a career engineer
- **Do NOT change the tech stack** (Django, React, Vite) without explicit discussion
