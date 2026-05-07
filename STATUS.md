# TTS Tax App — Status

## Last updated
2026-05-07

## Currently in progress
- **1040 UI work** — partially started by Session G. The W-2 entry surface is now production-shaped (employer name + EIN + Box b address + Box 15 + autofill). Remaining surface area: taxpayer info tab (real fields), interest income tab (form expanded), W-2 boxes 3–6 / 12 / 13 / 14 / 18–20, dependent UI. Backend models for the missing W-2 boxes already exist (boxes 3–6 nullable on `W2Income`); rest is frontend wiring + new fields.

## Last session recap (2026-05-07 Session G) — EIN/Employer database + W-2 autofill
- **Goal:** Build a federal-EIN-keyed Employer database, bulk-import 3,832 employers from a TaxWise CSV export, and wire EIN-based autofill into the W-2 entry UI on the 1040 module. Plus: a learning loop that promotes user-typed W-2 employers into the central database for future autofill.
- **Range pushed to origin/main:** `911b014..<HEAD>` (5 new commits).

| # | SHA | Phase | Message |
|---|-----|-------|---|
| 1 | `edc2ecb` | 1–3 | feat(employers): Employer + EmployerStateAccount models, bulk import command, parser utilities |
| 2 | `3f4c450` | 6 | feat(employers): GET /api/v1/employers/lookup/ autofill endpoint |
| 3 | `e56e993` | 7a | feat(w2): employer-snapshot + Box 15 fields with learning loop on save |
| 4 | `7914389` | 7b | feat(client): EIN autofill on W-2 entry — populates employer name/address from EIN database |
| 5 | (next) | 8 | chore(memory): update STATUS.md and MEMORY.md after Session G |

### Numbers
| Metric | Value |
|---|---|
| `employers_employer` rows after real import | **3,828** ✅ (3,832 CSV − 4 malformed-EIN errors = 3,828) |
| Real-import error rate | 0.10% (4 / 3,832) |
| Records flagged with `parse_warning` | 223 (5.8%) — line-2 detection 197, unparseable city/state/zip 16, etc. |
| `employers_employerstateaccount` rows | 0 (state IDs accumulate via learning loop only) |
| Pytest across the session | **71 / 71 passing** (32 parser + 14 import + 13 API/autofill-flow + 12 W-2 learning) |
| New TypeScript errors | 0 (verified via stash + tsc) |

### Schema
- New app: `apps.employers`. Two models — `Employer` (1 row per EIN, universal across firms) and `EmployerStateAccount` (1 row per `(employer, state)`, many states per employer for the TaxWise-bug case where Acme has GA + SC + TN accounts).
- RLS enabled on both new tables in migration 0001 to match the April 21 audit policy (default-deny, no policies; Django superuser bypasses).
- W2Income migration 0034 adds 6 fields: `employer_street/city/state/zip` (snapshot — frozen at entry time per tax-law historical-accuracy requirement) plus `state_box15` and `state_id_number` (Box 15).

### Autofill flow
- `GET /api/v1/employers/lookup/?ein=<value>` returns 200 with full employer payload + nested state_accounts; 404 if not found; 400 if EIN malformed; 401/403 if unauthenticated. Permission: `IsFirmMember`.
- W-2 entry component (`FormEditor.tsx` `W2IncomeSection`) was rewritten as a card-per-W-2 layout with three rows: identity+amounts / address / Box 15. EIN-onBlur fires the lookup; Box-15-state-onBlur uses cached `state_accounts` (no extra API call). Yellow text on autofilled fields per CLAUDE.md color convention; red border on EIN input when lookup returns 400; green text on user-entered. Yellow indicator is session-scoped (resets on page reload — persistent yellow tracking is a future polish).

### Learning loop
- `apps/employers/learning.py::sync_w2_to_employer_db` is called from the W-2 viewset on create + update.
- Idempotent: `get_or_create` for both Employer and EmployerStateAccount. **Never** overwrites existing rows (so verified=true canonical rows from the bulk import stay untouched).
- Best-effort by contract: helper has internal try/except, view has outer try/except. A learning-loop failure can never roll back the W-2 save.

### Notes & quirks from this session
- **Source CSV path mismatch.** The plan referenced `EIN_Database.csv` (underscore); actual file at `EIN Database.csv` (space). Used the actual filename.
- **RLS-enable RunSQL** added to the new app's `0001_initial` migration without explicit pre-approval — judgment call based on the April 21 audit policy. Flagged at Checkpoint 1; Ken approved by saying "yes" to proceed.
- **Test-DB pooler stickiness** required a couple of MCP-driven kills mid-session (Supavisor reconnects fast). Documented; tied to the long-pending test-DB strategy decision.
- **Address line-2 false-positive risk.** The "starts with number under 100" heuristic likely catches some legitimate addresses like "50 Main St" — but it's only a `parse_warning` flag, not a rejection. Preparers can review later.
- **Snapshot semantics.** W2Income.employer_* fields are frozen at entry time. If Acme moves their HQ in 2027, the 2025 W-2 record stays correct. Autofill writes initial values; user edits are independent thereafter.
- **`source` field semantics.** `source="taxwise_import"` for the 3,828 bulk-imported rows, `source="user_entered"` for everything created via the learning loop. Today both default to `verified=False` — a future polish session could let preparers mark records verified after first review.

## Previous session recap (2026-05-05 Session F) — TTS favicon
- **Commit:** `5d8eb1a`. New SVG at `client/src/renderer/public/favicon.svg`, `<link>` tag added to `index.html`. Blue-800 background, white "TTS" wordmark, scales cleanly to 16×16. Smoke-tested via vite dev server.

> Sessions D + E (Lacerte parser dry-run + real import) detail lives in MEMORY.md.

## Recently completed
- **2026-05-07 (Session G)** — EIN/Employer database + W-2 autofill. 5 commits pushed. 3,828 employers in DB; W-2 entry UI now autofills name+address from EIN; learning loop promotes user-typed employers and state-IDs.
- **2026-05-05 (Session F)** — TTS favicon (blue-800 background, white mark). 1 commit pushed: `5d8eb1a`.
- **2026-05-05 (Session E)** — Lacerte client-list import (real, `--commit --no-sanitize`). 121 individual TaxReturns now in DB for TY 2025. `created=13, updated=109, errors=0`. No code changes; memory update only.
- **2026-05-05 (Session D)** — Lacerte importer dry-run against real PDF. 122 records parsed; 95–100% field accuracy; 2 bounded parser bugs identified for a future targeted-fix session. No commits except memory update.
- **2026-05-05 (Session C)** — Code-drift commits 10–14 + Phase 0. 6 commits pushed to origin/main.
- **2026-04-28 (Session B)** — Cleanup commits 1, 2, 3, 5, 6, 7, 8, 9 (Commit 4 deferred). 8 commits pushed to origin/main as `a385720..ba7649d`.
- **2026-04-28 (Session A)** — PII extraction; 295 files + ~448.9 MiB moved to `D:\tax-test-data\`; `.gitignore` hardened. Janitorial only — no commits, no push.
- **2026-04-24** — Reconciled repo with April 21 Cowork security audit. 4 commits pushed to origin (`7ba4f1f`, `ff30f28`, `7afb4a8`, `a385720`). Supabase verification: 76/76 public-schema tables have `rowsecurity=true`.
- **2026-04-21** — 4-phase Supabase security audit (Cowork): RLS enabled on all 52 Django-owned public tables, 1099-app tenant isolation restored, leaked-password protection enabled, docs cleaned.
- **2026-04-12** — 1040 rough draft (individual return skeleton) — commit `509f79e`.

## Suggested next sessions
1. **1040 UI — finish the entry surface.** Taxpayer info tab (real fields, not placeholders), W-2 boxes 3–6 / 12 / 13 / 14 / 18–20, interest income tab beyond a payer + amount, dependents UI. Most of the backend exists (`W2Income` already has nullable boxes 3–6; `Taxpayer` has a full field surface). Pure frontend wiring with maybe 1–2 small model additions.
2. **Cut B — preparer-side document viewer.** A read-only pane that lists W-2 PDFs / 1099 PDFs / source documents the client uploaded, indexed by Entity. Pulls from the `documents` app (Session C). The "view" side of the upload flow that's already wired.
3. **Cut B — PDF preview pane on the W-2 form.** Side-by-side: the W-2 entry card on the left, the source W-2 PDF (uploaded via the documents app) on the right. Lets preparers cross-reference while typing without alt-tabbing. Probably embeds via the same `<embed>`-based PDF viewer the Forms tab already uses (per MEMORY.md "Forms tab: Browser native PDF iframe").
4. **Lacerte parser targeted fixes** (~1–2 hours). Cleanup, not blocking. Two bounded edits to `lacerte_clientlist_parser.py`:
   - Read `LEFT_COLUMNS["sp_first"]` and `["sp_last"]` as fallback when `_parse_name_lnf` returns empty spouse parts.
   - When right-page state OR zip are empty but street/city are populated, scan one y-bucket below for the missing values.
5. **Documents app — Supabase Storage bucket + S3 keys** — backend ships with conditional STORAGES. To go live, create the `tax-documents` bucket in Supabase and add `SUPABASE_S3_ACCESS_KEY` / `SUPABASE_S3_SECRET_KEY` / `SUPABASE_URL` to the Render `.env`. Until those are set, uploads land on the local filesystem (dev only).
6. **Auto-save rendered returns to client folders** — every PDF render should drop a copy in `tax-documents/<firm>/<entity>/<year>/`. Hook lives in `renderer.render_complete_return()`.
7. **Partnership importer test coverage** — TODO from Session C. Needs synthetic xlsx fixture + extraction of the row-parser into a function.
8. **Test-DB strategy decision** — `config.settings.test` currently creates/drops `test_postgres` against the shared prod Supabase project. The harmless teardown warning in every run, plus the pooler-stickiness this session hit, both point to "fix this soon." Three options documented in `config/settings/test.py` docstring.

## Known issues / blockers
- **Lacerte parser — 2 bounded bugs documented** (Anomalies 1 and 2). 7 / 122 records have minor field gaps. Usable as-is for development data; targeted fixes queued as next-session #4.
- **Documents app — Supabase Storage not yet wired in prod.** Code is conditional on `SUPABASE_S3_ACCESS_KEY`; without it Django falls back to local FS.
- **Employer database — 4 malformed-EIN rows from the TaxWise CSV silently dropped on import.** Logged as errors in the import summary but not preserved. If those 4 employers ever get a W-2 typed in, the learning loop will create a clean record for them.
- **Partnership importer has no automated test** — TODO in commit body of `8a27ade`.
- **Test-DB teardown warning + pooler stickiness** — known intermittent issue; mid-session manual `pg_terminate_backend` may be required. Permanent fix tied to test-DB strategy decision.
- **Yellow autofill indicator is session-scoped only.** Across page reloads, the W-2 entry UI loses the yellow markers (autofilled fields render as green like user-entered ones). Persistent autofill-state tracking is a future polish.
- Empty `Lacerte Export\` dir shell at repo root persists (locked by Explorer/SearchIndexer; resolves on reboot). Invisible to git.
