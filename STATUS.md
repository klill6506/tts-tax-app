# TTS Tax App — Status

## Last updated
2026-04-28

## Currently in progress
- (stub — populate at end of active-work sessions)

## Last session recap (2026-04-28 Session B) — Cleanup commits 1–9 (8 of 9 shipped, Commit 4 deferred)
- **Goal:** Take the inventory plan from Session A and ship the deletion / doc-move / .gitignore / reference-data commits. Defer Commits 10–14 (substantial code drift) to later sessions.
- **Range pushed to origin/main:** `a385720..ba7649d` (8 new commits).

| # | SHA | Message |
|---|-----|---|
| 1 | `5fa5f34` | chore: remove dev-artifact PDFs not caught by /*.pdf |
| 2 | `fc98e57` | chore: remove ad-hoc dev scripts from server/scripts/ |
| 3 | `5f6b9dd` | chore: dedupe partnership importer (3 broken copies) |
| — | _deferred_ | (Commit 4 — `scripts/sherpa_1099_phase2_rls_hardening.sql` deletion blocked, see flags) |
| 5 | `d638d01` | chore: complete DECISIONS.md migration to repo root |
| 6 | `1742159` | chore: drop superseded specs |
| 7 | `893817c` | chore: commit four-file system memory artifacts; drop stale cowork_sessions.md |
| 8 | `347dbc3` | chore(gitignore): IDE state, reference dirs, drop stale Docker comments |
| 9 | `ba7649d` | feat: commit reference data (specs, AcroForm field dumps, design notes) |

- **Working-tree files removed (most were untracked, removed via `rm`):**
  - 4 dev-artifact PDFs (Commit 1): `server/ga600s_calibration.pdf`, `server/test_ga600s_overlay.pdf`, `resources/irs_forms/2025/f1120s_print.pdf.bak`, the long-named `server/pdf_templates/2025_600S_..._12.23.25.pdf`
  - 29 dev scripts under `server/scripts/` (Commit 2): all `add_/check_/debug_/extract_/fix_/inspect_/test_/verify_` and the two `import_partnerships*.py` duplicates
  - 1 management-command duplicate (Commit 3): `server/apps/returns/management/commands/import_partnerships_cmd.py`
  - 2 superseded specs (Commit 6): root `4797_TY2025_v1_spec.json`, `server/specs/new_flow_assertions_8825_schedL.json`
  - `cowork_sessions.md` (Commit 7) — stale since 2026-03-22, superseded by four-file system
  - `scripts/download_fillable.py` (Commit 9, untracked) — superseded by `scripts/update_irs_forms.py`

- **Tracked-file changes:**
  - `.gitignore` (Commits 1, 2, 8): added dev-artifact-PDF patterns, ad-hoc-script patterns, reference-design-dir patterns, IDE-state pattern; removed stale Docker comment block
  - `.claude/settings.local.json`: `git rm --cached` (98 lines untracked, file kept on disk) — Commit 8
  - `memory/DECISIONS.md` → `DECISIONS.md` rename (Commit 5) — git detected as 100% identical, no content drift

- **Adds (Commits 7 and 9):**
  - `MEMORY.md`, `STATUS.md` at repo root (Commit 7)
  - `server/specs/schedule_l_4col_TY2025_v2_spec.json` (Commit 9)
  - 7 `*.fields.json` files in `resources/irs_forms/2025/` (Commit 9): f1120s_fillable, f1125a, f4562, f4797, f7004, f7203, f8825
  - `server/scripts/kill_sessions.py` (Commit 9)
  - `docs/specs/2026-03-21-editorial-gold-palette-design.md` (Commit 9, after renaming `docs/superpowers/` → `docs/specs/` and flattening the unnecessary nested `specs/` subdir)

- **Notes & quirks from this session:**
  - Commits 3 and 6 are **`--allow-empty`** — all the relevant files were untracked, so the deletion left no diff. The empty commits preserve the audit trail and rationale in git history.
  - Commit 1 swept up the prior session's uncommitted `.gitignore` changes (the 2026-04-28 unscoped `*.csv`/`*.xlsx`/`/*.pdf` rules) along with the new PDF patterns. Functionally correct, just slightly conflated with Session A's intent.
  - Step 1 from Session A was completed at the top of this session: `D:\dev\tts-tax-app\server\scripts\TTS Partnerships.xlsx` → `D:\tax-test-data\import-sources\TTS Partnerships.xlsx` (15,565 B). All client-bearing data files now live outside the repo.

## 🚩 Open flag — Commit 4 deferred
**`scripts/sherpa_1099_phase2_rls_hardening.sql` (6,336 B) deletion is paused.** Header says it was applied to Supabase 2026-04-21 by Cowork as part of the 1099 audit, and "owned by the 1099 repo." But search of `D:\dev\sherpa-1099\` turned up only similarly-themed files:

- `database/001c_rls_policies.sql`
- `database/002_fix_references_and_rls.sql`
- `database/migrations/005_tenant_rls.sql`

None matches the filename and 2026-04-21 timing. **Need Ken to confirm** the SQL is preserved (in 1099 repo under another name, or an out-of-band archive) before deleting from this repo. Until then the file stays untracked here as a safety copy.

## Next up — Commits 10–14 from the original plan (deferred)
Each has a blocker that prevented shipping in Session B:

| # | Plan | Blocker |
|---|------|---------|
| 10 | `feat(returns): add Taxpayer.spouse_date_of_birth (migration 0033)` — adds `models.py` change + `migrations/0033_add_spouse_date_of_birth.py` | Migration is already applied to Supabase (2026-04-21). Safe to commit anytime. |
| 11 | `feat: settings, deps, and pytest config for Supabase Storage and faker test fixtures` — `pyproject.toml` + `poetry.lock` + `base.py` + `prod.py` + new `test.py` | Must commit all 5 files together. `pyproject.toml` switches pytest to `config.settings.test`, which only works once `test.py` ships. Defensive: re-run `poetry install` to confirm the lock-file diff matches a clean regen. |
| 12 | `feat(documents): add document management app with folder UI` — full `apps/documents/` + URL wiring + frontend pages | **Documents app has zero tests** — violates CLAUDE.md "Tests required" rule. Either write `test_documents.py` (~150 LOC for happy-path API coverage) before this commit, or explicitly waive the rule. Migration 0001 was applied to Supabase 2026-04-02. |
| 13 | `feat(imports): add Lacerte client-list demographics importer` — parsers, sanitizer, mgmt cmd, 3 tests | Code hasn't been executed since first written. **Need to run `pytest tests/test_lacerte_*` against the synthetic-PDF fixtures** to confirm tests pass before committing. Depends on Commit 10 (`spouse_date_of_birth` field) and Commit 11 (`faker` dev-dep). |
| 14 | `feat(imports): add partnership importer as management command` — fixed-up `apps/returns/management/commands/import_partnerships.py` | **Code refactor required**: hardcoded path → `--xlsx-file` CLI arg (mirroring Lacerte importer). File currently non-functional as committed. |

## Recently completed
- **2026-04-28 (Session B)** — Cleanup commits 1, 2, 3, 5, 6, 7, 8, 9 (Commit 4 deferred). 8 commits pushed to origin/main as `a385720..ba7649d`.
- **2026-04-28 (Session A)** — PII extraction; 295 files + ~448.9 MiB moved to `D:\tax-test-data\`; `.gitignore` hardened. Janitorial only — no commits, no push.
- **2026-04-24** — Reconciled repo with April 21 Cowork security audit. 4 commits on main, pushed to origin (`7ba4f1f`, `ff30f28`, `7afb4a8`, `a385720`). Supabase verification: 76/76 public-schema tables have `rowsecurity=true`.
- **2026-04-21** — 4-phase Supabase security audit (Cowork): RLS enabled on all 52 Django-owned public tables, 1099-app tenant isolation restored, leaked-password protection enabled, docs cleaned.
- **2026-04-12** — 1040 rough draft (individual return skeleton) — commit `509f79e`.

## Known issues / blockers
- Code drift staged for Commits 10–14 (above). Working tree shows 7 modified files + 13 untracked items, all expected.
- **Commit 4 deferred** (sherpa-1099 RLS SQL preservation unconfirmed). See open flag above.
- **Commit 12 / documents app**: zero tests. Will need test_documents.py before merge per CLAUDE.md "Tests required" rule, or an explicit waiver.
- **Commit 14 / partnership importer**: file at `apps/returns/management/commands/import_partnerships.py` is non-functional — hardcoded path looks for `TTS_Partnerships.xlsx` (underscore, wrong filename) inside the repo (file moved to `D:\tax-test-data\import-sources\`). Refactor required before committing as feature.
- Empty `Lacerte Export\` dir shell at repo root persists (locked by Explorer/SearchIndexer; resolves on reboot). Invisible to git.
- ~~`server/scripts/TTS Partnerships.xlsx` still inside repo~~ — moved 2026-04-28 (Session B).
- ~~`server/NUL` stray Windows-shell artifact~~ — deleted 2026-04-28 (Session A).
