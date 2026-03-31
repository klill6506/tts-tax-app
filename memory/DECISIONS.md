# TTS Tax App — Architecture Decisions & Standards

## Tech Stack (Locked)
- Backend: Django 5.2 LTS + Django REST Framework
- Frontend: Vite + React 19 + TypeScript (SPA)
- Styling: Tailwind Plus (no hardcoded colors)
- Database: Supabase Postgres 17.6 (session pooler, IPv4)
- Hosting: Render.com (Virginia)
- Serving: Django + WhiteNoise (same origin)
- Dependencies: Poetry (Python 3.13), npm (client)
- PDF: ReportLab + pypdf + pymupdf
- AI: Gemini (IRS-grounded RAG)
- Grid: Hand-rolled Tailwind tables (no third-party grid library)
- Web-only. No Electron. No Docker. No SQLite in production.

## Architecture Decisions
Do not change without discussing with Ken first.

- **Single app all tax years** — one deployment handles all years via tax_year field. Never separate sites per year.
- **Year-scoped seed data** — all FormFieldDefinition rows must have tax_year. Never year-agnostic seed rows.
- **Year-scoped PDF paths** — always resolve as resources/irs_forms/{tax_year}/form.pdf. Never hardcode a year in a path.
- **Year-scoped field maps** — AcroForm field maps versioned by year when IRS redesigns a form.
- **Depreciation** — internal DepreciationAsset model is the default. Sherpa Depreciation app is future optional upgrade via checkbox on return.
- **State depreciation fields** — use state_ prefix on all fields for future multi-state support.
- **Shared database** — Supabase shared across the tax suite. All suite tables have firm_id + created_at.
- **No third-party grid library** — hand-rolled Tailwind tables throughout. Do not introduce AG Grid, MUI DataGrid, TanStack Table, etc.
- **compute_return() before every render** — always call before generating any PDF. No exceptions.

## Coding Standards
Always follow these exactly.

- **Testing** — never run full test suite during development. Fast tests only: `poetry run pytest -m "not db" --ignore=tests/test_acroform_filler.py`
- **Flow assertion gate** — any session modifying compute.py, renderer.py, k1_allocator.py, aggregate functions, depreciation_engine.py, or MACRS tables MUST run `pytest tests/test_flow_assertions.py -v` and ALL assertions must pass before committing. If an assertion fails, fix the code — do not modify the assertion JSON without explicit instruction.
- **Git** — always `git add . && git commit -m "message" && git push origin main` together. Never commit without pushing.
- **MACRS display** — store method internally as 200DB/150DB/SL/NONE. Always display as "MACRS 200DB HY 5yr" format in UI and on printed schedules. Never show raw codes to user.
- **Color system** — RED/YELLOW/GREEN on all data entry fields. RED=error, YELLOW=calculated/imported, GREEN=manually entered. Never deviate.
- **Colors** — managed via Tailwind Plus palette. Never hardcode hex or RGB values.
- **AcroForm widgets** — always set widget.border_color=(0,0,0) and widget.fill_color=(1,1,1). Never fill AcroForm fields directly — use text overlay approach.
- **Seed commands** — idempotent (update_or_create). Run automatically via build.sh on every Render deploy.
- **No feature deploys during peak season** — Feb 15–Apr 15: hotfixes only. Feature branches merge after Apr 15.

## Tax Law Accuracy Policy
- Never rely on training data alone for specific rates, limits, phaseouts, or dates.
- When uncertain about any tax rule, flag it for Ken rather than guessing.
- Ken is a CPA specializing in depreciation — verify all depreciation rules carefully.

### Verified Rules — 2025 Tax Year
- **Bonus depreciation (OBBBA, July 4 2025):** 100% if acquired+placed in service after Jan 19 2025 (permanent). 40% if binding contract before Jan 20 2025. Taxpayer can elect 40% instead of 100% for first tax year ending after Jan 19 2025.
- **Section 179 federal:** $2,500,000 limit / $4,000,000 phaseout. Effective for property placed in service after Dec 31 2024.
- **Section 179 Georgia:** $1,050,000 limit / $2,620,000 phaseout. GA has NOT adopted OBBBA. Static conformity date Jan 1 2025.
- **Georgia bonus depreciation:** Never allowed. Any federal bonus = GA addition on GA-600S Schedule 1.
- **MACRS tables:** IRS Publication 946.
- **Luxury auto limits:** Current IRS Rev. Proc. for applicable year.
- **Section 197 / Startup costs (195):** 180 months straight-line.

## Future Roadmap (Build Toward These)
Do not build yet — but don't paint into a corner.

- **Year rollover command** — management command to clone seed data year N → N+1. Needed before Oct 2026.
- **Staging environment** — needed before first external client goes live.
- **Multi-state depreciation** — state conformity table replaces hardcoded GA logic when adding states.
- **Return Manager** — add preparer filter (default current user) + client side panel for multi-return clients.
- **State help tab** — Gemini searches state DOR instructions by state + form. Same pattern as federal help.
- **Lacerte depreciation import** — PDF → structured asset data. Design data model to accommodate now.
- **Next-year depreciation projection** — same engine, pass tax_year+1. Hook already exists in model.
- **Bulk actions on Return Manager** — multi-select returns, batch PDF generation, status changes.
