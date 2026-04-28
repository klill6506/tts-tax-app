# TTS Tax App - Project Memory

## 2026-04-28 — Cleanup Commits (Session B, 8 of 9 shipped)

Pushed `a385720..ba7649d` to `origin/main`. Eight commits covering deletions, doc moves, .gitignore polish, and reference-data adds. See STATUS.md for the full per-commit table. Commit 4 (sherpa-1099 RLS SQL deletion) deferred pending preservation confirmation. Commits 10–14 (substantial code drift) remain in working tree.

### Standing facts established this session
- **`server/scripts/` hygiene rule**: ad-hoc throwaway scripts (test_*, debug_*, check_*, inspect_*, verify_*, extract_*, fix_*, kill_test_db*) are now gitignored by pattern. Real utilities go in `server/scripts/` (currently: `kill_sessions.py`, `run_dev.ps1`, `calibrate_coordinates.py`, `download_irs_templates.py`, `export_rule_studio.py`, `extract_field_maps.py` — all tracked). New utilities should live in `server/scripts/` with a non-throwaway name; experimental scripts should be deleted before commit or scoped to a feature branch.
- **`.claude/settings.local.json` is no longer tracked.** It was previously committed in error. Now sits in `.gitignore`, file remains on disk for IDE use. Do not re-stage it.
- **Canonical Form 4797 spec lives at `server/specs/form_4797_spec.json`.** The older root-level `4797_TY2025_v1_spec.json` (mentioned as "source of truth" in earlier MEMORY.md notes) was deleted in Commit 6 of this session — it had a different export schema and was superseded. The export script `server/scripts/export_rule_studio.py` writes to the canonical path.
- **Four-file system in effect.** `CLAUDE.md`, `MEMORY.md`, `STATUS.md`, `DECISIONS.md` all live at repo root and are tracked in git. `memory/DECISIONS.md` was renamed to `DECISIONS.md` in Commit 5 (100% identical, no content drift). Background sync mirrors to `G:\My Drive\kens-personal-life\apps\tts-tax-app\`.
- **`cowork_sessions.md` deleted** — superseded by the four-file system. Stale since 2026-03-22.

## 2026-04-21 — Supabase Security Audit (Cowork, 4 phases)

- **Shared Supabase project**: `tmqypsbmswishqkngbrl` hosts both the tax app and sherpa-1099. Tax-app "dev" is pointed at this prod DB — ~709 real clients, 321 returns, ~92K form values as of audit time. Treat every dev-time DB write as production.
- **Phase 1 — RLS enabled on all Django-owned public-schema tables** (52 tables: `django_*`, `auth_*`, `clients_*`, `returns_*`, `depreciation_*`, `portal_*`, `firms_*`, `mappings_*`, `imports_*`, `diagnostics_*`, `ai_help_*`, `audit_*`, `documents_*`, `brain_notes`). Django connects as Postgres superuser via the pgbouncer pooler, which bypasses RLS, so ORM queries are unaffected.
- **Phase 2 — 1099-app tenant isolation restored** on `filers`, `recipients`, `forms_1099`, `submissions`, `activity_log`, etc. See `scripts/sherpa_1099_phase2_rls_hardening.sql` (untracked, owned by the 1099 repo).
- **Phase 3 — Leaked-password protection** enabled via Supabase dashboard (HaveIBeenPwned check on auth).
- **Phase 4 — Doc cleanup**: CLAUDE.md updated (Docker references removed; dev-points-at-prod warning added; RLS rule with "never `USING (true)`" guidance), `.env.example` switched to Supabase pooler pattern, `docker-compose.yml` deleted.
- **Verified 2026-04-24**: 76 of 76 public tables have `rowsecurity=true` in Supabase.

## 2026-04-24 — RLS state captured as Django migration

- New migration: `server/apps/core/migrations/0001_enable_rls_on_public_tables.py`. Reversible. Idempotent (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY` is a no-op if already on). Scoped to 52 Django-owned tables only — the 24 1099-app tables are excluded.
- Running `migrate` against the current Supabase DB will be a no-op for this migration (use `--fake` if preferred).
- **Never write `USING (true)` or `WITH CHECK (true)` policies** — Postgres OR's policies together, so one permissive policy silently defeats every other policy on the table.
- If a new table will be exposed via PostgREST / anon key, add a `tenant_isolation`-style policy; otherwise default-deny is sufficient because Django bypasses RLS as superuser.

### Commits from the 2026-04-24 cleanup session (all on main, pushed)
| SHA | Message |
|---|---|
| `7ba4f1f` | docs: remove Docker references from CLAUDE.md (web app only, Supabase direct) |
| `ff30f28` | docs: update .env.example to Supabase connection pattern |
| `7afb4a8` | chore: remove inert docker-compose.yml (no longer used) |
| `a385720` | feat(core): capture April 21 RLS state as reversible migration |

Diff URL pattern: `https://github.com/klill6506/tts-tax-app/commit/<sha>`. Pre-session HEAD was `509f79e` (April 12, 1040 rough draft skeleton).

### Full RLS migration table list (52 Django-owned tables)
`django_migrations`, `django_content_type`, `django_admin_log`, `django_session`, `auth_permission`, `auth_group`, `auth_group_permissions`, `auth_user`, `auth_user_groups`, `auth_user_user_permissions`, `ai_help_helpquery`, `audit_auditentry`, `brain_notes`, `clients_client`, `clients_cliententitylink`, `clients_entity`, `clients_taxyear`, `depreciation_asset`, `depreciation_assetevent`, `depreciation_computeddeprline`, `depreciation_computedrollup`, `depreciation_regimepolicy`, `diagnostics_diagnosticfinding`, `diagnostics_diagnosticrule`, `diagnostics_diagnosticrun`, `documents_clientdocument`, `firms_firm`, `firms_firmmembership`, `firms_preparer`, `firms_printpackage`, `imports_trialbalancerow`, `imports_trialbalanceupload`, `mappings_mappingrule`, `mappings_mappingtemplate`, `portal_accesslog`, `portal_document`, `portal_documentrequest`, `portal_magiclinktoken`, `portal_message`, `portal_portaluser`, `returns_depreciationasset`, `returns_disposition`, `returns_formdefinition`, `returns_formfieldvalue`, `returns_formline`, `returns_formsection`, `returns_interestincome`, `returns_lineitemdetail`, `returns_officer`, `returns_otherdeduction`, `returns_partner`, `returns_partnerallocation`, `returns_preparerinfo`, `returns_prioryearreturn`, `returns_rentalproperty`, `returns_shareholder`, `returns_shareholderloan`, `returns_taxpayer`, `returns_taxreturn`, `returns_w2income`.

Excluded (1099-app owned, 24 tables, already had RLS before Phase 1): `activity_log`, `ats_submissions`, `column_aliases`, `filer_filing_status`, `filers`, `forms_1099`, `import_batches`, `import_history`, `import_rows`, `operating_years`, `recipients`, `submissions`, `tenant_members`, `tenants`, `tin_match_log`, `user_profiles` (plus a few others included in the 76-table total).

### Things that didn't match expectations during the 2026-04-24 session

1. **RLS migration file already existed locally as untracked** — Cowork had already written `server/apps/core/migrations/0001_enable_rls_on_public_tables.py` on April 21. It was committed as-is rather than rewritten; the content meets every Step 4 requirement (reversible, idempotent, 1099 tables excluded, docstring explaining the audit).

2. **Memory-file instructions diverged mid-session.** The pre-session global CLAUDE.md said dual-write memory to `C:\Users\Ken2\.claude\projects\D--dev-tts-tax-app\memory\memory.md` AND `G:\My Drive\sherpa-memory\tts-tax-app\`. A mid-session update to the global CLAUDE.md established a new rule: four files at project root (`CLAUDE.md`, `MEMORY.md`, `STATUS.md`, `DECISIONS.md`), with a background script handling the Google Drive mirror — **no dual-write from inside a CC session**. Followed the newer rule: updated `D:\dev\tts-tax-app\MEMORY.md`, created `D:\dev\tts-tax-app\STATUS.md` (was missing), did not touch legacy `C:\Users\Ken2\.claude\projects\...\memory\memory.md` or `G:\My Drive\sherpa-memory\`. Neither `MEMORY.md` nor `STATUS.md` is tracked in git — Ken to decide.

3. **Massive out-of-scope drift remains uncommitted.** ~8 other modified files and ~80 untracked files at session end. Worth its own dedicated cleanup session. See STATUS.md "Known issues / blockers" for the full list.

### Standing facts from this session
- **Dev DB is prod DB.** `server/.env` points Django at Supabase project `tmqypsbmswishqkngbrl`. ~709 real clients live there as of 2026-04-21. Dev-time DB writes are production writes.
- **Docker is gone for good.** `docker-compose.yml` deleted, CLAUDE.md cleaned. App runs Django + React dev servers only, talking to Supabase directly via the session pooler.
- **RLS is default-deny on all tax-app tables.** Django bypasses it as superuser. If a table is ever exposed via PostgREST / supabase-js / anon key, add a `tenant_isolation`-style policy — never `USING (true)`.
- **Memory/status workflow.** `MEMORY.md` + `STATUS.md` at project root. Background script syncs to `G:\My Drive\kens-personal-life\apps\<project>\`. Do not dual-write from within a CC session.

## Project Location
- Root: `D:\dev\tts-tax-app`
- Server: `D:\dev\tts-tax-app\server` (Django 5.2, Poetry, Python 3.13)
- Client: `D:\dev\tts-tax-app\client` (Vite, React, TypeScript — web SPA)
- GitHub: `https://github.com/klill6506/tts-tax-app` (private)

## CRITICAL: Actual Tech Stack (Do Not Change Without Discussion)
- **Backend**: Django 5.2 LTS + Django REST Framework
- **Frontend**: Vite + React 19 + TypeScript (web SPA, served by Django via WhiteNoise)
- **Database**: Supabase Postgres 17.6 (shared with 1099 app) — session pooler via IPv4
- **Hosting**: Render.com (Virginia region, same as Supabase) — Django + WhiteNoise serves SPA
- **Dependencies**: Poetry (Python), npm (client)
- **Note**: Electron was removed (Mar 6, 2026) — app is web-only now

## Database Connection (Supabase)
- **Host**: `aws-1-us-east-1.pooler.supabase.com` (session pooler, IPv4)
- **Port**: 5432 | **Database**: `postgres`
- Direct connection is IPv6-only — doesn't work from office network
- Tests run ~3x slower over Supabase; `test_postgres` DB lock issues common

## Web App Deployment
- **Deployed on Render** — Django serves React SPA via WhiteNoise, same origin
- **Web build**: `cd client && npm run build` → `client/dist-web/`
- **SPA catch-all**: `config/urls.py` serves `index.html` for non-API routes in prod
- **Session timeout**: 8 hours in production
- **Seeds run automatically**: `build.sh` runs all 8 seed commands after migrate on every deploy

## Diagnostics System — 37 ACTIVE RULES (Mar 22, 2026)
- **Architecture**: DiagnosticRule/Run/Finding models, dynamic rule loader, seed command
- **Runner**: `apps/diagnostics/runner.py` → run_diagnostics(tax_year) → computes return first, then checks
- **39 total rules** (37 active, 2 deactivated): 29 preparer + 10 internal — seeded via `seed_rules`
- **Deactivated**: TB_EXISTS (not every return uses TB import), EXTENSION_NO_EST (not useful)
- **Category field**: `preparer` (visible by default) vs `internal` (toggle in UI, localStorage pref)
- **Balance sheet check**: Uses L15a/L15d (total assets) vs L27a/L27d (total liab+equity) for 1120-S. Fires when either side has data and they don't match.
- **Preparer rules**: Balance sheet BOY/EOY, M-1/M-2 reconciliation, Page 1 math, missing EIN/address/shareholders/officers, ownership %, SSN, income entered, dates, preparer, 4797 disposition checks (5), distributions > AAA, reasonable comp, GA bonus addback, extension w/o payment, late filing, GA PTET election, deductions > income, meals limitation
- **Internal rules**: K18 reconciliation, 4797→Page 1 flow, GA bonus S1 addback, AAA negative, M1-3b sign, depr destination, 1125-A flow, 1125-E flow, 8825→K2 flow, 179→K11 flow
- **UI**: Severity filter buttons (All/Errors/Warnings/Info), internal toggle checkbox, rule code display, sorted by severity
- **API**: `POST /diagnostic-runs/run/` (computes return first), `GET /diagnostic-runs/?tax_year=`

## Key Facts
- **~473 tests** across 10+ Django apps
- Superuser: Ken2 (firm: "The Tax Shelter", id=dfe4540f-5ead-4030-9a3f-e5994837ae67)
- 1120-S: 11 sections, **303 lines** | 1065: 10 sections, **285 lines** | 1120: 9 sections, 172 lines
- GA-600S: 8 sections (Sched 1-8 incl. Sched 2 PTET), ~89 lines, 43 compute formulas
- All 5 entity types enabled: scorp, partnership, ccorp, trust, individual

## Landing Page — Return Manager (Mar 21, 2026)
- **Server-side pagination**: DRF PageNumberPagination, 25 per page
- **Entity type tabs**: All / S-Corp / Partnership / C-Corp / Trust / Individual with badge counts
- **Server-side filtering**: entity_type, status, preparer, year, search (client name, entity name, FEIN)
- **Server-side ordering**: client_name, entity_name, status, updated_at (default: -updated_at)
- **URL state**: All filters stored in URL query params via useSearchParams
- **Debounced search**: 300ms debounce before sending search to server
- **Lightweight list serializer**: Only essential fields (no nested data, no prefetch_related on list)
- **Entity type counts**: Returned in list response, respects all filters except entity_type
- **Database indexes**: status, -updated_at, -created_at on TaxReturn
- **Table columns**: Client (+ entity name), Type, FEIN, Status (color badge), Preparer, Modified (relative time), Actions

## Client UI — Current Tab Structure
- **Three-tab architecture**: Input | Forms | Diagnostics
- **Input section tabs** (federal, 16 tabs): Info, Admin, Shareholders, Income & Ded., Sched K, Balance Sheet, Sched B, Form 7203, Rental (8825), Dispositions, Depreciation, Schedule F, Extensions, PY Compare, State
- **Forms tab**: Browser native PDF iframe (PDF.js reverted — caused print/rendering bugs). Default zoom 138%. Left sidebar with form names + package selector + refresh/download
- **Header consolidation (Mar 22)**: Return header removed. Status badge + save indicator in blue toolbar breadcrumb. Import TB moved to input section tab bar. Content width: max-w-[1440px] in editor (was 1280px). Input tabs: overflow-x-auto (no wrapping).
- **Blue data text (Mar 22)**: `screen_mode` via contextvars. Blue (0,0,0.75) for on-screen, black for print. `?screen=true` on render-complete endpoint. Forms tab always uses screen mode.
- **Instruction page stripping**: SKIP_PAGES dict in renderer. 8879-S page 2 (instructions) excluded from rendered PDFs.
- **Coordinate calibration**: `scripts/calibrate_coordinates.py --form ga600s` — generates red crosshair PDF for position verification. Works with all coordinate overlay forms.

## AcroForm PDF Rendering (Mar 8-10, 2026)
- **Text overlay approach**: Extracts widget positions from IRS fillable PDFs, strips widgets, draws text via ReportLab overlay + pypdf merge
- **Year-scoped field maps**: `field_maps/{form_id}_{year}.py`, dynamic resolver via `importlib`
- **AcroForm forms (13)**: f1120s, f1120sk1, f7004, f8879s, f8453s, f1125a, f8825, f7203, f4797, f1120ssd, f8949, f1125e, f4562
- **Coordinate overlay (3)**: f1065, f1120, f7206 (GA-600S uses native generation, not coordinate overlay)
- **Key rule**: Never fill AcroForm fields directly — use text overlay only
- **Always call `compute_return()` before rendering**
- **Font fix (Mar 22)**: All data text uses Courier-Bold + explicit `setFillColorRGB(0,0,0)` for crisp black output

## PDF Rendering
See details: `memory/pdf_rendering.md`

## Complete Return PDF
- `render_complete_return(tax_return, package=None, return_page_map=False)` in `renderer.py`
- **Print Packages**: client, filing, extension, state, k1s, invoice, letter, None (all)
- Order: Letter → Invoice → Main → 1125-A → 8825 → 4562 → 4797 → Depr Schedule → K-1s → 7203s → 7206s → 7004 → State
- Form 7004 only included if `extension_filed` is True
- **Page map API**: `GET /api/v1/tax-returns/{id}/page-map/` — returns form→page mapping

## Invoice & Letter
- **Invoice**: `render_invoice()` in `invoice.py` — Lacerte-style bordered frame, ALL CAPS firm header, columnar forms list, fee summary
- **Letter**: `render_letter()` in `letter.py` — Gray-banded border frame, centered letterhead, auto page breaks
- `_get_forms_list()` returns `list[tuple[str, str]]` (form_number, description)

## Georgia State Return — COORDINATE OVERLAY (Mar 21, replaced native)
- See details: `memory/ga_state_return.md`
- **Switched from native generation to coordinate overlay** on official GA DOR template PDF
- Template: `server/pdf_templates/ga600s_2025.pdf` (8-page official form)
- `render_ga600s_overlay()` in `renderer.py` — same pattern as f1065/f1120
- Coordinate map: `coordinates/fga600s.py` — header fields + Schedules 1-8
- `ga600s_native.py` + `form_primitives.py` kept but no longer called
- Standalone endpoint: `POST /api/v1/tax-returns/{id}/render-ga600s/`
- Pages 0-2 populated (header, S1-S8). Pages 3-7 (NOL, credits) deferred

## Deductions — COMPLETE
- Flat 2-column layout, ~30 named D_* fields + 6 free-form rows
- M&E: D_MEALS_50, D_MEALS_DOT, D_ENTERTAINMENT → D_MEALS_DED, D_MEALS_NONDED computed
- Line 19 = computed sum. Nondeductible flow: D_MEALS_NONDED → K16c → M1_3b → M2_5a
- **M&E Statement**: Custom `_render_me_statement()` (not generic statement renderer) with proper category breakdowns

## Full 1120-S Implementation Pass from Rule Studio Specs (Mar 21)
- **All 17 specs exported** from Rule Studio to `server/specs/` (18 forms, one duplicate 4797 v1/v2)
- **Schedule D / 8949 flow BUILT** (was completely missing):
  - `aggregate_schedule_d()` in compute.py: Disposition(is_4797=False) → K7 (ST), K8a (LT)
  - `render_schedule_d()` + `render_8949()` in renderer.py
  - f8949_2025.py field map completed (192 fields — 11 rows × 8 cols per part + totals + checkboxes)
  - Both forms added to `render_complete_return()` when Sch D dispositions exist
  - K7→K-1 Box 7 and K8a→K-1 Box 8a already wired in SCHED_K_TO_K1_MAP
- **Rental income flow BUILT**: `aggregate_rental_income()` → K2 from Form 8825 net rents
- **Officer comp flow BUILT**: `aggregate_officer_compensation()` → Page 1 Line 7 from Officer model
- **All supporting forms verified against specs**: 4562, 1125-A, 1125-E, 8825, 7203 — all match
- **All K lines verified**: K1-K18 correctly sourced per spec
- **108 spec-based tests** (42 new + 66 existing), all passing
- **GA-600S PTET rate discrepancy**: Spec says 5.49% (TY2024), code uses 5.39% (TY2025 correct)

## 1120-S Compute — AUDITED FROM RULE STUDIO SPECS (Mar 18)
- **7 specs exported** from Rule Studio: Page 1, Sched K, K-1, M-1, M-2, Sched D, Form 8949
- **Specs location**: `server/specs/` (JSON files)
- **Export script**: `server/scripts/export_rule_studio.py`
- **3 bugs fixed in `compute.py`**:
  1. **M2_8a**: AAA distributions now capped — cannot reduce AAA below zero (IRC 1368(e)(1))
  2. **K18**: Now subtracts K12b, K12c, K12d (was only subtracting K11 + K12a)
  3. **M2_5a**: Now includes K12b, K12c, K12d in AAA reductions
- **Verified correct** (no change needed):
  - Page 1 Line 4 = 4797 Part II Line 17 (ordinary gains)
  - K9 = 4797 Part I Line 7 (Section 1231, distinct from K4 interest)
  - M1_3b = positive add-back (sign was correct)
  - 4797 bypasses Schedule D on 1120-S
  - M-1 reconciliation (M1_8 = K18 by construction)
- **36 new spec tests** in `test_1120s_spec.py` (all passing)
- **Note**: Spec R018 says "K18 = Page1_Line21" which is a simplification — K18 actually = sum(K1-K10) - deductions. Code is correct, spec description is misleading.

## Form 4797 — REBUILT FROM RULE STUDIO SPEC (Mar 18)
- **Source of truth**: `server/specs/form_4797_spec.json` (exported from Sherpa Tax Rule Studio). Older root-level export `4797_TY2025_v1_spec.json` was removed 2026-04-28 in Cleanup Commit 6.
- **Holding period**: Changed from days (≤365) to months (>12 = long-term) per spec R001
  - Uses `_holding_period_months()` helper in both compute.py and renderer.py
- **§1245 vs §1250 routing**: New `_is_1250_property()` helper
  - §1245 (equipment, furniture, vehicles, intangibles): full recapture = min(gain, depr)
  - §1250 (buildings, improvements): ordinary recapture = 0 (post-1986 SL), unrecaptured at 25% rate
- **Part III rendering**: Now fills correct IRS lines per property type
  - §1245: Line 26g (depreciation), Line 27a (recapture)
  - §1250: Line 25a (100%), Line 25b ($0 additional depr), Line 27a ($0 recapture)
- **Routing unchanged**: Short→Part II, LT loss→Part I, LT gain+depr→Part III, LT gain no depr→Part I
- **Flow OUT unchanged**: 1120-S K9+L4, 1065 K10+L6
- **5 new diagnostics** (D001-D005): F4797_MISSING_DATES, F4797_ZERO_DEPR, F4797_GAIN_NO_RECAPTURE, F4797_ZERO_SALE, F4797_1231_LOOKBACK
- **30 new spec-based tests** in `test_4797_spec.py` (6 scenarios + holding period + property type)
- Field map keys: `P4797_30/31/32` (summary), `P3_25a/25b/26g/27a_{col}` (per-property)

## Sherpa Client Portal — DEPLOYED
- See details: `memory/sherpa_portal.md`

## Second Brain — WORKING
- See details: `memory/second_brain.md`

## Sherpa Depreciation — UI REDESIGN COMPLETE
- See details: `memory/sherpa_depreciation.md`

## Internal Depreciation Module — COMPLETE
- `DepreciationAsset` model, 50+ fields, Section 179/bonus/MACRS/AMT/GA
- Groups: Buildings, M&E, F&F, Land, Improvements, Vehicles, Intangibles
- Flow: page1 (L14), 8825, sched_f. Section 179 → K11 only
- Auto-calculate on every POST/PATCH. Disposal calcs: adj_basis, gain/loss, recapture
- Engine: `depreciation_engine.py` with IRS Pub 946 MACRS tables
- 33 unit tests in `test_depreciation_engine.py`

## Lacerte Depreciation Import — COMPLETE (Mar 22)
- **Parser**: `apps/imports/importers/lacerte_depr_parser.py` — parses fixed-width TXT export
- **API**: `POST /api/v1/tax-returns/{id}/import-depreciation/` — preview (default) or commit (?commit=true)
- **Management cmd**: `poetry run python manage.py import_depreciation --file X --return-id Y [--dry-run]`
- **Frontend**: Import button on Depreciation tab — file picker → preview table → Import All
- **Format**: Lacerte fixed-width columns: No., Description, Acquired, Sold, Cost, Bus.Pct, 179, Prior, Method/Conv/Life, Current
- **Group mapping**: Auto/Transport→vehicles, Machinery→machinery_equipment, Furniture→furniture_fixtures, etc.
- **Date pivot**: 00-30→2000s, 31-99→1900s
- **Extensible**: `--format` flag for future parsers (taxwise, drake, proseries)
- **38 parser tests** in `test_lacerte_import.py`, fixture: `tests/fixtures/lacerte_mwelding.txt`

## Schedule F — Farm Income — COMPLETE
- 45 seed lines, computed F1c/F9/F33/F34, K-line flow: F34 → K10

## Dispositions — Schedule D / Form 4797 — COMPLETE
- Separate `Disposition` model, API endpoints, frontend edit form
- 12 tests in `test_dispositions.py`

## Tier 2 Forms — RENDER FUNCTIONS COMPLETE
- Forms: 4797, Sched D, 8949, 1125-E, 4562 — field maps + render functions
- 21 tests in `test_render_4562_4797.py`

## Fix Rounds
- **First Return Fixes** (Mar 11): See `memory/first_return_fixes.md`
- **Follow-Up Fixes** (Mar 12): See `memory/follow_up_fixes.md`
- **Round 4 Fixes** (Mar 12): See `memory/round4_fixes.md` — GA-600S headers, 4797 routing, M&E statement, form sidebar, invoice/letter redesign, 7004 extension guard
- **Round 4 Follow-Up** (Mar 13): GA-600S continuation headers fixed (y=755→670, x swapped), 4797 routing corrected (5-scenario IRS decision tree), letter/invoice white text bug (`_draw_frame` left fill=white → added saveState/restoreState), sidebar nav improved (removeAttribute+rAF)
- **Round 4 Follow-Up #2** (Mar 13): GA-600S native form generation (replaces coord overlay), letter/invoice explicit fill color reset, sidebar goToPage uses about:blank+setTimeout, GA seed Schedule 2 added + sort orders fixed
- **Round 5 Fixes** (Mar 13): GA-600S quality overhaul (B&W only, black section headers, bordered entity grid table, proper grid lines on all schedule rows, page numbers), 4797 IRS-compliant Part III→L31→Part II L13 and L32→Part I L6 flow (asset details NOT in Part I Line 2), letter/invoice inner margins widened (INNER_INSET 0.2→0.5 inch), invoice firm name enlarged (16→20pt)
- **Round 5 Revised** (Mar 14): 4797 summary line keys fixed (P3_30→P4797_30, etc.), aggregate_dispositions() added to compute.py for 1120-S K9/L4 flow, GA-600S rebuilt with form_primitives.py, invoice header reduced (20→14pt firm, 12→10pt detail), invoice underlines repositioned above content
- **Round 6** (Mar 14): 4797 field map off-by-one fix (entire map remapped from PDF widget dump — Lines 1a/b/c, 3-7, 8-9, 11-18b all corrected), header consolidation (menu bar hidden in editor, breadcrumb merged into blue toolbar via outlet context)

## Year-Scoping Architecture — COMPLETE
- `FormDefinition` uses `unique_together = [("code", "tax_year_applicable")]`
- All 4 seeds accept `--year`. Return creation filters by code + year.

## Testing Policy
- **Do NOT run full test suite after every task** — Supabase DB tests are too slow
- Ken visually verifies all UI/PDF changes directly after each session
- Full suite only when explicitly requested or before production deploy

## Shell Quirks (Windows)
- `poetry run python -c "..."` multi-line commands produce NO output — use script files
- Bash tool uses Git Bash — use `/d/dev/tts-tax-app/server` paths

## Tax Law Accuracy
- See CLAUDE.md for verified 2025 rules (OBBBA bonus, Sec 179, GA depreciation)
- GA does NOT conform to IRC 168(k) or OBBBA
- Ken is a CPA specializing in depreciation — verify rules carefully

## Form 1065 (Partnership) — Phase A
See full scope: `memory/form_1065_phase_a.md`
- 6-stage implementation plan (~10-12 sessions)
- **Stage 1 COMPLETE**: Partner model (25+ fields), PartnerAllocation model (13 categories), expanded seed (10 sections, 285 lines)
- **Stage 2 COMPLETE**: 35 compute formulas, K-1 allocation engine (`k1_allocator.py`), form-aware depreciation/disposition aggregation
- K-1 engine: pro-rata with special allocation overrides, SE by partner type, GP per-partner
- Partner CRUD API + allocation CRUD + K-1 preview endpoint (`/k1-allocations/`)
- 16 unit tests (allocator) + 11 seed tests = 27 tests total
- Next: Stage 3 (Frontend Input Tabs)

## Theme Preset System (Mar 21, 2026)
- **ThemePreset architecture** in `AppShell.tsx` — one-click full-theme switching
- Presets override all CSS custom properties (colors, fonts, CSS class)
- **Editorial Gold** preset: warm parchment surfaces (#f1eee5), dark gold nav (#493800), Work Sans body, Newsreader serif headlines, `.theme-editorial` class
- Fonts: Newsreader + Work Sans loaded via Google Fonts in `index.html`
- `index.css`: body font uses `var(--font-sans)`, `--font-headline` token, `.theme-editorial h1/h2/h3` rule
- Palette picker: "Theme" row at top, bg/accent rows dimmed when preset active, dark mode toggle hidden
- Preset persisted in `localStorage` key `sherpa-theme-preset`
- Hardcoded `text-blue-200` replaced with token-based `text-tx-on-dark` classes in AppShell + FormEditor
- Branch: `feature/editorial-gold-theme`

## Roadmap
See full list: `memory/roadmap.md`

## Big Picture
**Goal**: Sellable tax practice platform by ~2027.
**Target market**: Small/mid CPA firms (~3,000 returns, ~9 preparers).
**Competitors**: Taxwise (primary), Lacerte (Ken likes better but more expensive).
