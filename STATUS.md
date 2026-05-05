# TTS Tax App — Status

## Last updated
2026-05-05

## Currently in progress
- (stub — populate at end of active-work sessions)

## Last session recap (2026-05-05 Session F) — TTS favicon
- **Goal:** Replace the default empty favicon with a TTS wordmark using the project's brand colors.
- **One commit shipped:** `5d8eb1a` (`feat(client): add TTS favicon — blue-800 background, white mark`). Pushed to `origin/main`.
- **Files changed:** `client/src/renderer/public/favicon.svg` (new, 426 B) and `client/src/renderer/index.html` (+1 line — `<link rel="icon" type="image/svg+xml" href="/favicon.svg" />`).
- **Design choices:**
  - Background `#1e40af` (Tailwind blue-800, the documented brand color in CLAUDE.md "Blue-800 nav, white cards").
  - Wordmark "TTS" in white, weight 800, font stack `Manrope, "Segoe UI", system-ui, …` (Manrope preferred but unreliable — favicons load before web fonts — so the system-ui fallback is the realistic primary).
  - 32×32 viewBox, 2px corner radius, scales cleanly to 16×16.
  - Initially drafted in Charcoal & Gold (the default theme); switched to blue/white after eyeball review since blue is the documented brand color across the app.
- **Vite path note:** the project's Vite `root` is `client/src/renderer/`, so the convention public dir is `client/src/renderer/public/` (not `client/public/`). No `vite.config.ts` change needed — Vite copies it to `dist-web/` on build.
- **Smoke test:** spun up `vite` dev server, `GET /favicon.svg` returned `200 OK` + `Content-Type: image/svg+xml` + matching body, and the served `/` HTML contained the new `<link>` tag. Both background tasks stopped cleanly.
- Browser favicon caches aggressively — Ctrl+Shift+R on the dashboard to see the new icon.

## Previous session recap (2026-05-05 Session E) — Lacerte client-list import (real, --commit)
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

> Session D (parser dry-run, 2026-05-05) detail lives in MEMORY.md — the field-quality table, the two bounded-bug write-ups, and the diagnostic-artifact location. One-liner in "Recently completed" below.

## Recently completed
- **2026-05-05 (Session F)** — TTS favicon (blue-800 background, white mark). 1 commit pushed: `5d8eb1a`. Two files: `client/src/renderer/public/favicon.svg` (new) + `client/src/renderer/index.html` (+1 link tag).
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
