# TTS Tax App — Status

## Last updated
2026-05-05

## Currently in progress
- (stub — populate at end of active-work sessions)

## Last session recap (2026-05-05 Session C) — Commits 10–14 + Phase 0 (all 6 shipped)
- **Goal:** Land the substantive code-drift commits that Session B deferred (10–14) and resolve the deferred Commit 4 from Session B (sherpa-1099 RLS SQL).
- **Range pushed to origin/main:** `4fcd33d..<HEAD>` (6 new commits + 1 memory-update commit).

| # | SHA | Phase | Message |
|---|-----|-------|---|
| 4 | `5e5ee63` | 0 | chore: drop sherpa-1099 RLS SQL (preserved in Supabase migration history) |
| 10 | `c986262` | 1 | feat(returns): add Taxpayer.spouse_date_of_birth (migration 0033) |
| 11 | `14dfe2c` | 2 | feat: settings, deps, and pytest config for Supabase Storage and faker test fixtures |
| 12 | `d39c711` | 3 | feat(documents): add document management app with folder UI and tests |
| 13 | `c54eab6` | 4 | feat(imports): add Lacerte client-list demographics importer |
| 14 | `8a27ade` | 5 | feat(imports): partnership importer accepts --xlsx-file CLI arg |

- **Test results across the session:**
  - Documents app (`tests/test_documents.py`, new): **7 passed, 1 warning** (the harmless pooler-teardown warning documented in MEMORY.md)
  - Lacerte importer (`tests/test_lacerte_*` + `tests/test_import_lacerte_clients_cmd.py`): **31 passed, 1 warning**
  - Partnership importer dry-run against real xlsx: parsed 31 partnerships, all already in DB → `Would create: 0, Skipped: 31` → transaction rolled back, no DB drift.
  - Smoke test for new `config.settings.test`: import + `django.setup()` succeeds, `storages` and `apps.documents` confirmed in `INSTALLED_APPS`.

- **Notes & quirks from this session:**
  - Initial documents-app test pass failed because `force_authenticate` bypasses Django's `AuthenticationMiddleware` so `FirmMiddleware` saw `AnonymousUser`. Switched to `APIClient.force_login()` — establishes a real session without password hashing, satisfies the "don't hit real auth" intent while letting the middleware chain run. This is now the documented pattern for future tests that need `request.firm` populated.
  - `poetry install --dry-run` reported `0 installs, 0 updates, 0 removals, 69 skipped` — lock file fully in sync with `pyproject.toml`. New deps (`boto3 1.42.82`, `botocore 1.42.82`, `faker 39.1.0`, `django-storages 1.14.6`, `jmespath 1.1.0`) all already locked.
  - Partnership importer is now atomic — the per-row work is wrapped in `transaction.atomic()` with `set_rollback(True)` on dry-run, so a partial failure no longer leaves half-imported state.
  - `pyproject.toml` ignores `tests/test_acroform_filler.py` via `addopts` (preserves Session B intent).

## Recently completed
- **2026-05-05 (Session C)** — Code-drift commits 10–14 + Phase 0. 6 commits pushed to origin/main.
- **2026-04-28 (Session B)** — Cleanup commits 1, 2, 3, 5, 6, 7, 8, 9 (Commit 4 deferred). 8 commits pushed to origin/main as `a385720..ba7649d`.
- **2026-04-28 (Session A)** — PII extraction; 295 files + ~448.9 MiB moved to `D:\tax-test-data\`; `.gitignore` hardened. Janitorial only — no commits, no push.
- **2026-04-24** — Reconciled repo with April 21 Cowork security audit. 4 commits pushed to origin (`7ba4f1f`, `ff30f28`, `7afb4a8`, `a385720`). Supabase verification: 76/76 public-schema tables have `rowsecurity=true`.
- **2026-04-21** — 4-phase Supabase security audit (Cowork): RLS enabled on all 52 Django-owned public tables, 1099-app tenant isolation restored, leaked-password protection enabled, docs cleaned.
- **2026-04-12** — 1040 rough draft (individual return skeleton) — commit `509f79e`.

## Suggested next sessions
- **1040 UI work** — taxpayer info / W-2 / interest tabs are skeleton-only. Now that demographics can be imported, the data-entry surface is the bottleneck for actually using a 1040.
- **Lacerte client-list importer dry-run against the real PDF** — parser was tested on synthetic ReportLab PDFs; first real run will surface column-geometry edge cases. Run with `--no-sanitize` against the real `2025 Custom Reports.pdf` and capture warnings.
- **Documents app — Supabase Storage bucket + S3 keys** — backend ships with conditional STORAGES. To go live, create the `tax-documents` bucket in Supabase and add `SUPABASE_S3_ACCESS_KEY` / `SUPABASE_S3_SECRET_KEY` / `SUPABASE_URL` to the Render `.env`. Until those are set, uploads land on the local filesystem (dev only).
- **Auto-save rendered returns to client folders** — every PDF render should drop a copy in the appropriate `tax-documents/<firm>/<entity>/<year>/` path. Hook lives in `renderer.render_complete_return()`.
- **Partnership importer test coverage** — TODO from this session. Needs synthetic xlsx fixture + extraction of the row-parser into a function. Pattern to mirror: `test_lacerte_clientlist_parser.py` (synthetic ReportLab PDF) and the documents app test approach.
- **Test-DB strategy decision** — `config.settings.test` currently creates/drops `test_postgres` against the shared prod Supabase project. The harmless teardown warning in every run reminds us this isn't ideal. Three options documented in `config/settings/test.py` docstring; decision still pending.

## Known issues / blockers
- **Documents app — Supabase Storage not yet wired in prod**. Code is conditional on `SUPABASE_S3_ACCESS_KEY`; without it Django falls back to local FS. Needs bucket + keys before the docs UI is usable on Render.
- **Partnership importer has no automated test** — TODO in commit body of `8a27ade`. Refactor needed (extract row-parser, add synthetic xlsx fixture).
- **Test-DB teardown warning** — every pytest run reports `OperationalError('database "test_postgres" is being accessed by other users')`. The conftest hook handles it post-run, but it's noisy. Permanent fix tied to the test-DB strategy decision above.
- Empty `Lacerte Export\` dir shell at repo root persists (locked by Explorer/SearchIndexer; resolves on reboot). Invisible to git.
