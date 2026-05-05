# TTS Tax App — Status

## Last updated
2026-05-05

## Currently in progress
- (none — Session E completed the Lacerte demographics import; Session F (favicon) starting next)

## Last session recap (2026-05-05 Session E) — Lacerte client-list import (real, --commit)
- **Goal:** Promote Session D's validated dry-run to a real import. `--commit --no-sanitize` against the same 86-KB Lacerte PDF.
- **Single commit this session:** the memory update at the end. Working tree was clean throughout.
- **Importer summary:** `Imported: created=13, updated=109, nochange=0, errors=0` — exact match to Session D's prediction.
- **Verification (data + API + Supabase MCP all agree):**
  - 121 `returns_taxpayer` rows globally
  - 121 individual TaxReturns for tax_year=2025 (firm-scoped)
  - 690 individual entities firm-wide (most pre-existing from S-corp / partnership relations)
  - Return Manager dashboard "Individual" tab count: **121** — confirmed by replicating `TaxReturnViewSet.list()`'s aggregation. The data layer + API layer both produce 121 individual returns; a browser refresh of the Return Manager will show the same.
- **One soft anomaly:** importer processed 122 records, but only 121 Taxpayer rows resulted. Source PDF has 122 distinct SSNs (no duplicates), so the collision happened during upsert. Most likely cause: two records share the same `Client.name` (the third-fallback lookup after `Taxpayer.ssn` and `Entity.ein` both miss); two distinct people with identical "LAST, FIRST [M]" name strings would collide on the third lookup, share an Entity, and produce one Taxpayer for both. Doesn't affect the user-visible count (Individual tab shows 121); flagged for awareness, not investigated further this session.
- **Diagnostic artifacts:** `D:\tax-test-data\_session_e_logs\` (`step2_real_import.log` with REAL PII; `verify.py`, `dashboard_counts.py`, `dup_check.py` — counts only, no PII output). Keep until Session D's parser-fix session lands; delete after.

## Previous session recap (2026-05-05 Session D) — Lacerte importer dry-run against real PDF
- **Goal:** Diagnostic-only run of the Lacerte client-list importer against the real Lacerte custom-report PDF (`D:\tax-test-data\lacerte_pdfs\2025 Custom Reports - Ken's client list.pdf`, 86,070 B). No DB writes, no code edits. The synthetic ReportLab fixtures the parser tests use never exercised real-PDF column geometry.
- **No commits this session except the memory update at the end.** Working tree was clean throughout.

### Numbers
| Metric | Value |
|---|---|
| Records parsed | 122 |
| Parser-emitted warnings | 0 |
| Records with all expected fields filled | 115 |
| Records with at least one structural defect | 7 |
| Importer errors | 0 |
| Filing-status split | 82 mfj / 40 single (HOH and MFS not inferred — known limitation) |
| `--no-sanitize` dry-run summary | `created=13, updated=109, nochange=0, errors=0` (transaction rolled back) |

### Field-extraction quality (across all 122 records)
| Field | Filled | Notes |
|---|---|---|
| `tp_ssn`, `tp_dob`, `street`, `city`, `preparer` | 122 / 122 | 100% |
| `state`, `zip` | 120 / 122 | 2 records affected by Anomaly 1 |
| `tp_email` | 52 / 122 | 39% mfj, 50% single — typical for older client lists, not a bug |
| `sp_dob` | 82 / 82 mfj | 100% of mfj records |
| `sp_ssn` | 81 / 82 mfj | 1 record asymmetric (sp_dob present, no sp_ssn) |
| `sp_first_name` | 78 / 82 mfj | 4 records affected by Anomaly 2 |

### Two bounded parser bugs identified
1. **Anomaly 1 — address wrap drops state and zip.** When a right-page address wraps to two visual lines, `_bucket_rows` pairs the wrong y-bucket; street and city extract from one line, state and zip from a different (paired) line. Affects 2 / 122 records.
2. **Anomaly 2 — spouse names dropped when not in LNF "AND" structure.** `LEFT_COLUMNS["sp_first"]` and `LEFT_COLUMNS["sp_last"]` are defined in the parser but **never read**. Spouse names live in dedicated columns on the left page, but the parser only reads them out of the LNF "AND ..." form. When Lacerte writes spouse names in the dedicated columns instead, the parser silently drops them. Affects 4 / 122 records (2 with `AND` in LNF that fails the regex, 2 with no `AND` where dedicated columns hold the data).

A 3rd minor anomaly — 1 record with `sp_dob` extracted but no `sp_ssn` and no `sp_first_name` — is plausibly the Anomaly 1 root cause hitting spouse columns instead of address columns, or a real edge case (deceased spouse / no SSN on file). Not separately actionable.

### Notes & quirks from this session
- **Parser is silent on every error path.** `rec.warnings` exists and gets populated for malformed SSN/DOB, but the management command never prints it. None of those code paths fired on the real PDF (zero malformed SSNs, zero unparseable DOBs), so we'd never know if they were broken either. Worth surfacing warnings in a `--verbose` flag sometime.
- **Importer change-log shows `filing_status: FilingStatus.SINGLE -> 'mfj'`** — model default is the `FilingStatus` enum but the importer assigns a string. Cosmetic, not functional.
- **`LEFT_COLUMNS["sp_first"]` and `["sp_last"]` are dead code** — the parser docstring even mentions the columns exist in the report layout. Removing them or actually using them are both fine; mixed state is what produced Anomaly 2.
- Diagnostic artifacts (logs + ad-hoc Python) live at `D:\tax-test-data\_session_d_logs\` outside the repo. Keep until the parser-fix session lands; delete afterward.

## Recently completed
- **2026-05-05 (Session E)** — Lacerte client-list import (real, `--commit --no-sanitize`). 121 individual TaxReturns now in DB for TY 2025. `created=13, updated=109, errors=0`. No code changes; memory update only.
- **2026-05-05 (Session D)** — Lacerte importer dry-run against real PDF. 122 records parsed; 95–100% field accuracy; 2 bounded parser bugs identified for a future targeted-fix session. No commits except memory update. Working tree clean throughout.
- **2026-05-05 (Session C)** — Code-drift commits 10–14 + Phase 0. 6 commits pushed to origin/main.
- **2026-04-28 (Session B)** — Cleanup commits 1, 2, 3, 5, 6, 7, 8, 9 (Commit 4 deferred). 8 commits pushed to origin/main as `a385720..ba7649d`.
- **2026-04-28 (Session A)** — PII extraction; 295 files + ~448.9 MiB moved to `D:\tax-test-data\`; `.gitignore` hardened. Janitorial only — no commits, no push.
- **2026-04-24** — Reconciled repo with April 21 Cowork security audit. 4 commits pushed to origin (`7ba4f1f`, `ff30f28`, `7afb4a8`, `a385720`). Supabase verification: 76/76 public-schema tables have `rowsecurity=true`.
- **2026-04-21** — 4-phase Supabase security audit (Cowork): RLS enabled on all 52 Django-owned public tables, 1099-app tenant isolation restored, leaked-password protection enabled, docs cleaned.
- **2026-04-12** — 1040 rough draft (individual return skeleton) — commit `509f79e`.

## Suggested next sessions
1. **1040 UI work** — taxpayer info / W-2 / interest tabs are skeleton-only. Now that demographics can be imported and the parser is validated as good-enough, the data-entry surface is the actual bottleneck for using a 1040. **This is the highest-value next session.**
2. **Lacerte parser targeted fixes** (~1–2 hours). Cleanup, not blocking. Two bounded edits to `lacerte_clientlist_parser.py`:
   - Read `LEFT_COLUMNS["sp_first"]` and `["sp_last"]` as fallback when `_parse_name_lnf` returns empty spouse parts.
   - When right-page state OR zip are empty but street/city are populated, scan one y-bucket below for the missing values.
   Add corresponding test cases to the synthetic fixture (one row per fix). Re-run Session D's diagnostic afterward to confirm anomaly counts drop.
3. **Documents app — Supabase Storage bucket + S3 keys** — backend ships with conditional STORAGES. To go live, create the `tax-documents` bucket in Supabase and add `SUPABASE_S3_ACCESS_KEY` / `SUPABASE_S3_SECRET_KEY` / `SUPABASE_URL` to the Render `.env`. Until those are set, uploads land on the local filesystem (dev only).
4. **Auto-save rendered returns to client folders** — every PDF render should drop a copy in the appropriate `tax-documents/<firm>/<entity>/<year>/` path. Hook lives in `renderer.render_complete_return()`.
5. **Partnership importer test coverage** — TODO from Session C. Needs synthetic xlsx fixture + extraction of the row-parser into a function. Pattern to mirror: `test_lacerte_clientlist_parser.py` (synthetic ReportLab PDF) and the documents app test approach.
6. **Test-DB strategy decision** — `config.settings.test` currently creates/drops `test_postgres` against the shared prod Supabase project. The harmless teardown warning in every run reminds us this isn't ideal. Three options documented in `config/settings/test.py` docstring; decision still pending.

## Known issues / blockers
- **Lacerte parser — 2 bounded bugs documented** (Anomalies 1 and 2 above). 7 / 122 records have minor field gaps. Usable as-is for development data; targeted fixes queued as suggested-next-session #2.
- **Documents app — Supabase Storage not yet wired in prod**. Code is conditional on `SUPABASE_S3_ACCESS_KEY`; without it Django falls back to local FS. Needs bucket + keys before the docs UI is usable on Render.
- **Partnership importer has no automated test** — TODO in commit body of `8a27ade`. Refactor needed (extract row-parser, add synthetic xlsx fixture).
- **Test-DB teardown warning** — every pytest run reports `OperationalError('database "test_postgres" is being accessed by other users')`. The conftest hook handles it post-run, but it's noisy. Permanent fix tied to the test-DB strategy decision above.
- Empty `Lacerte Export\` dir shell at repo root persists (locked by Explorer/SearchIndexer; resolves on reboot). Invisible to git.
