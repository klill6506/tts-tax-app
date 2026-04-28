# TTS Tax App — Status

## Last updated
2026-04-28

## Currently in progress
- (stub — populate at end of active-work sessions)

## Last session recap (2026-04-28) — PII extraction, no commits
- **Goal:** get all client-data files out of the repo and harden `.gitignore` against accidental future commits. Janitorial only — no code changes, no commits, no push.
- **Moved out of repo to `D:\tax-test-data\`:** 295 files totaling ~448.9 MiB.
  - `Lacerte Export/` (279 PDFs, 446.5 MiB) → `D:\tax-test-data\lacerte-export\Lacerte Export\` via `robocopy /MOVE` (plain `mv` failed twice with "Device or resource busy" — Explorer/SearchIndexer holding the dir handle).
  - In-repo `tax-test-data/lacerte_pdfs/` (1 PDF, 86 KB) → `D:\tax-test-data\lacerte_pdfs\`.
  - 9 root-level files → `D:\tax-test-data\misc\`: 1120S Deductions.xlsx, SCorp_Forms_List.xlsx, TTS Tax App Steps Remaining.xlsx, six `test_*.pdf` render artifacts (treated as PII since rendered against prod DB).
  - 7 root-level files → `D:\tax-test-data\import-sources\`: clients_import.csv/.xlsx, scorps_import.csv, shareholders_import.csv, Single Page Form for MWELDING.txt, Depreciation PDF.pdf, Diagnostics.pdf.
- **Deleted:** `server/NUL` (120 B Windows shell artifact). No `.DS_Store` / `Thumbs.db` / `desktop.ini` found anywhere.
- **`.gitignore` updated** (lines 45–60 added): unscoped `*.csv`, `*.xlsx`, `*.xls`; root-only `/*.pdf`, `/Lacerte Export/`, `/tax-test-data/`, `/lacerte_pdfs/`; plus `NUL`. Inline note documents the unscoped-pattern tradeoff (use `!` exception or `git add -f` for legitimate fixtures). Verified zero tracked files matched the new rules.
- **Working tree state:** PII data files no longer at repo root; `git status` now shows only legitimate code drift (modified files, new `documents/` app, migration 0033, importer code, memory files, etc.). Nothing committed — STATUS.md update included.
- **Empty `Lacerte Export\` dir shell** at repo root persists (locked by Explorer/SearchIndexer; will resolve on reboot). Invisible to git.

## Next session — first task before any commit work
**🚩 Address flag #1: `server/scripts/TTS Partnerships.xlsx`** (15,565 B, partnership source data per MEMORY.md, 31 records). The new `*.xlsx` rule silently ignores it from `git status`, but the file is still physically inside the repo. Move it to `D:\tax-test-data\import-sources\` before doing any commit work — it defeats the spirit of "PII out of repo" to leave it in place.

## Flags queued from 2026-04-28 session
1. **🚩 PRIORITY — `server/scripts/TTS Partnerships.xlsx` still inside repo** (silently ignored, not deleted). Move to `D:\tax-test-data\import-sources\` first thing.
2. Empty directory shell `D:\dev\tts-tax-app\Lacerte Export\` — locked by Explorer at move time, didn't `rmdir`. Invisible to git. Will clear on reboot. No action needed.
3. Two near-duplicate partnership importers — `import_partnerships.py` (7,086 B) and `import_partnerships_cmd.py` (6,249 B) — both exist under `server/scripts/` AND `server/apps/returns/management/commands/`. De-dup needed before committing the importer work; decide which is canonical.
4. Dev-artifact PDFs in subdirs not caught by root-scoped `/*.pdf`: `server/ga600s_calibration.pdf`, `server/test_ga600s_overlay.pdf`, `resources/irs_forms/2025/f1120s_print.pdf.bak`, and the misnamed `server/pdf_templates/2025_600S_..._12.23.25.pdf`. Decide per-file: move out, delete, or scope-add to `.gitignore`.
5. Stale `.gitignore` comment on lines 26–27 (`# Docker / # (docker-compose.yml IS committed)`) — wrong since `docker-compose.yml` was deleted in commit `7afb4a8`. Trivial cleanup, deferred.
6. `memory/DECISIONS.md` deletion + new root-level `DECISIONS.md` are paired changes (per global CLAUDE.md migration). Belongs in one rename-style commit when the commit sequence is planned.

## Recently completed
- **2026-04-24** — Reconciled repo with April 21 Cowork security audit. 4 commits on main, pushed to origin:
  - `7ba4f1f` docs: remove Docker references from CLAUDE.md (web app only, Supabase direct)
  - `ff30f28` docs: update .env.example to Supabase connection pattern
  - `7afb4a8` chore: remove inert docker-compose.yml (no longer used)
  - `a385720` feat(core): capture April 21 RLS state as reversible migration (`server/apps/core/migrations/0001_enable_rls_on_public_tables.py`, 52 Django-owned tables, idempotent + reversible, 1099 tables excluded)
  - Supabase verification (`tmqypsbmswishqkngbrl`): 76/76 public-schema tables have `rowsecurity=true`. All 52 tables in the migration's `RLS_TABLES` list are present and enabled.
  - `server/pyproject.toml` test config confirmed as `DJANGO_SETTINGS_MODULE = "config.settings.dev"`. `config/settings/test.py` exists locally but is not in repo and not wired into pytest — left alone per Ken's Step 5 instruction.
- **2026-04-21** — 4-phase Supabase security audit (Cowork): RLS enabled on all 52 Django-owned public tables, 1099-app tenant isolation restored, leaked-password protection enabled via dashboard, docs cleaned.
- **2026-04-12** — 1040 rough draft (individual return skeleton) — commit `509f79e`.

## Next up
- (stub — populate as sessions define next steps)

## Known issues / blockers
- Significant uncommitted code drift remains, awaiting a deliberate commit-sequencing session: modified `client/src/renderer/main.tsx`, `server/apps/returns/models.py`, `server/config/settings/base.py`, `server/config/settings/prod.py`, `server/config/urls.py`, `server/pyproject.toml`, `server/poetry.lock`, `.gitignore`; untracked new app `server/apps/documents/`, new migration `returns/0033_add_spouse_date_of_birth.py`, new client pages `ClientFolders.tsx` / `FolderDetail.tsx`, Lacerte import parsers + management commands + tests, ~30 debug scripts under `server/scripts/`, root-level memory/index files (`MEMORY.md`, `STATUS.md`, `DECISIONS.md`, `cowork_sessions.md`), assorted spec exports, and the `memory/DECISIONS.md` deletion (paired with the new root `DECISIONS.md`). Loose CSV/XLSX/PDF data files at repo root resolved 2026-04-28 (moved to `D:\tax-test-data\`) — see "Last session recap".
- `server/config/settings/test.py` exists locally but is not in the repo; `pyproject.toml` currently uses `config.settings.dev` for pytest, so test.py is not wired up. Decide before committing.
- ~~`server/NUL` stray Windows-shell artifact~~ — deleted 2026-04-28.
