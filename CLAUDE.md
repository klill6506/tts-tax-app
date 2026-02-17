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
├── docs/                       # PROJECT_CHARTER, ADRs, DEVLOG
├── resources/irs_forms/        # Official IRS PDF templates
│   ├── forms_manifest.json     # Template registry (URL + SHA256)
│   └── 2025/                   # Templates by tax year
├── scripts/                    # Project-wide scripts
│   └── update_irs_forms.py     # Download + verify IRS PDFs
├── server/                     # Django backend
│   ├── config/settings/        # base.py + dev.py (+ prod.py later)
│   ├── apps/                   # Django apps (core, firms, accounts, etc.)
│   │   └── tts_forms/          # IRS form PDF rendering subsystem
│   │       ├── renderer.py     # Core PDF renderer
│   │       ├── statements.py   # Supporting statement pages
│   │       └── coordinates/    # Field position mappings per form
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

## UI/Design Standards

### General Principles
- **Professional, not sterile.** We're a CPA firm, not a hospital. Warm neutrals > cold grays.
- **Generous whitespace.** Don't cram. Let elements breathe.
- **Subtle depth.** Use soft shadows (shadow-sm, shadow-md) to create layers.
- **Consistent spacing.** Pick a scale (4, 8, 16, 24, 32px) and stick to it.

### Colors
- Primary: Blue (trust, professionalism) — not too bright
- Accent: Warm gold or amber for CTAs and highlights
- Backgrounds: Off-white or very light warm gray (not pure white, not cold gray)
- Text: Near-black (gray-900), not pure black

### Typography
- Headings: Semi-bold, slightly larger than you think
- Body: Regular weight, good line-height (1.5-1.6)
- Don't be afraid of font-medium for emphasis

### Components
- Buttons: Rounded corners (rounded-lg), padding (px-4 py-2 minimum), hover states
- Cards: Subtle border OR shadow, not both. Rounded corners.
- Forms: Labels above inputs, clear focus states, adequate spacing between fields
- Tables: Alternating row colors optional, but always clear headers

### Dark Mode (if applicable)
- Not pitch black — use gray-900 or slate-900
- Reduce contrast slightly (gray-100 text, not white)
- Accent colors may need to be lighter/more saturated
