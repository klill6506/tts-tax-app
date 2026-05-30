# TTS Tax App — Status

## Last updated
2026-05-28

## Currently in progress
- (none — Session K Part 2 merged `feat/sch-8812-ctc-actc` to main.)

## Last session recap (2026-05-28 Session K, Part 2 of 2) — Schedule 8812 render + merge

- **Goal:** Close the render half of the Schedule 8812 verification
  chain: download the IRS PDF, build the f1040s8 field map, wire Lines
  19 + 28 on Form 1040, integrate Sch 8812 into `render_complete_return`,
  build end-to-end render assertions, parameterize the OBBBA cap by
  tax year, and merge the branch.
- **Branch:** `feat/sch-8812-ctc-actc`, merged to main 2026-05-28.

### What landed
- **OBBBA cap is now tax-year-parameterized.** `_constants_for_year(tax_year)` in `apps/returns/compute_8812.py`. TY 2025+ → $2,200 / $1,700; TY 2024 → $2,000 / $1,700. Module-level constants still defined as TY 2025+ aliases for any external imports. 5 regression tests in `test_compute_8812_year_constants.py`.
- **`resources/irs_forms/2025/f1040s8.pdf`** downloaded + recorded in `forms_manifest.json` (24 entries total — was 22 with a pre-existing test failure). SHA256 verified.
- **`apps/tts_forms/field_maps/f1040s8_2025.py`** — 32 line entries + header. Keys match `seed_sch_8812`'s `line_number` format (`L_1`, `L_2a`, `L_16a`, `L_16b_qc_count`, …).
- **`f1040_2025.py` FIELD_MAP gained Lines 19 + 28.** Line 19 → `f2_11`, Line 28 → `f2_24`. (Other lines in that field map are wrong for the 2025 PDF — audit queued separately.)
- **`render_sch_8812(tax_return)`** in `renderer.py` reads SCH_8812 FormFieldValues (which live on the parent 1040 TaxReturn), builds header from Taxpayer, mirrors Line 4 → Line 16b count, returns None when no data exists. Wired into `render_complete_return` step 1a (between main 1040 and Form 8879-S).
- **3 end-to-end PDF render assertions** in `tests/test_sch_8812_render.py`:
  - CTC-only (MFJ + 2 QC + ample tax) — Line 14 = $4,400 lands on Sch 8812 page 1; Form 1040 Line 19 = $4,400 on page 2.
  - ACTC-eligible (MFJ + 3 QC + AGI $30K + tax $1K) — Line 14 = $1,000, Line 27 = $4,125 on Sch 8812; matching $1K / $4,125 on Form 1040 Lines 19 + 28.
  - Form 2555 zero-out (TS13) — Line 14 = $4,400 still renders (CTC unaffected), L_16a + L_27 + Form 1040 Line 28 are blank (per IRS convention — `format_currency("0") == ""`).
- **New helper `assert_value_at_widget_position`** in `apps/returns/verification.py`. AcroForm widgets are flattened to text spans during rendering — looking up by `widget.field_name` post-render fails. Position-based search (x, y with tolerances) works.
- **`family_with_kids.json` fixture updated.** `expected[19]` = $4,400 (OBBBA), Line 22 = $12,268, Line 34 = $5,232. `relationship` values switched from `"son"`/`"daughter"` to the strict-choice `"child"` (Session K Part 1 migration 0041 made the field a choice).
- **`test_manifest_is_valid_json`** updated to `len(forms) == 24` — pre-existing fail (was 22 expected vs 23 actual) plus the f1040s8 add.

### Test results
- Targeted (`test_sch_8812_scenarios + test_flow_assertions + test_compute_8812_year_constants + test_sch_8812_render + test_tts_forms.TestManifest + test_1040 + test_dependents + test_render_verification`): all green.
- Full DB suite: see "Known issues / blockers" below — the pre-existing failures (`test_apr01_fixes` fixtures, `test_w2_employer_learning` pooler stickiness) are documented carry-overs from Part 1, not new.

## Last session recap (2026-05-27 Session K, Part 1 of 2) — Schedule 8812 input + compute

- **Goal:** Implement CTC + ACTC + ODC per the SCH_8812_TY2025 Rule
  Studio spec (Session 14). Per Ken's scope direction, Session K is
  split across two CC sessions on `feat/sch-8812-ctc-actc`. Part 1 =
  input + compute + flow assertions + spec scenarios. Part 2 = render
  + merge to main.
- **Branch (NOT merged):** `feat/sch-8812-ctc-actc`. 6 commits on top of
  `ec625ad` (the Session J head).

| # | SHA | Message |
|---|-----|---------|
| 1 | `a3ec6ad` | feat(1040): Dependent model 8812 classification expansion (migration 0041) |
| 2 | `f592eb0` | feat(1040): Taxpayer 8812 inputs + placeholders for Sch 1/2/3/SE/8959/EITC (migration 0042) |
| 3 | `abb2cae` | feat(1040): seed SCH_8812 + extend seed_1040 for Lines 17-23 + 28 |
| 4 | `9e26a7b` | feat(1040): compute_8812 — all 30 rules from SCH_8812 Rule Studio spec |
| 5 | `d9fdf18` | test(1040): wire 13 SCH_8812 flow assertions — all passing |
| 6 | `3825444` | test(1040): 17 SCH_8812 spec scenarios passing end-to-end + compute_8812 ACTC overflow fix |

### What landed (Session K, Part 1)

- **Migrations 0041 + 0042.** 7 new Dependent fields including
  strict-choice `relationship` (8 codes from spec). 18 new Taxpayer
  fields — 10 real return-level facts (SSN validity, Form 2555 inputs,
  combat pay, etc.) + 8 preparer-entered placeholders for Sch 1/2/3/SE/
  8959/EITC totals (default 0, all on `Taxpayer` until those forms
  land).
- **Seeds.** `seed_1040` extended with Lines 17, 18, 19, 20, 21, 22,
  23, 28 (now 27 lines total). New `seed_sch_8812` (32 lines across 3
  sections — Part I + Part II-A + Part II-B).
- **`apps.returns.compute_8812`** — all 30 spec rules implemented.
  Hooked into `compute_return()` for `form_code=="1040"` between two
  downstream-formula passes.
- **All 13 flow assertions pass** (replaced Session J's empty stub).
  11 new `kind`-based sub-runners added to `_run_sch_8812_assertion`.
- **17 of 18 spec scenarios pass end-to-end** in
  `tests/test_sch_8812_scenarios.py`. TS_WSB_TBD (Worksheet B)
  deferred per spec note + Ken's direction.

### Tests
- `test_sch_8812_scenarios.py`: 17 active + 1 sanity = 18 pass.
- `test_flow_assertions.py`: 20 1120-S + 13 1040 + 2 meta = 35 pass.
- `test_dependents.py`: 13 pass (10 existing + 3 new for the strict
  choice + Sch 8812 classification fields).
- `test_1040.py`: 13/13 pass (no regressions from the L_18/L_22/L_24/L_33
  formula additions).
- **Full DB suite at session close: 1166 passed, 15 skipped, 1 failure,
  15 errors in 5h 5min against shared Supabase.** None of the failures
  are caused by this session:
  - 1 pre-existing failure: `test_tts_forms.TestManifest.test_manifest_is_valid_json`
    asserts `len(data["forms"]) == 22` but the manifest has 23 entries
    (someone added a form without updating the test). 1-line fix.
  - 3 pre-existing fixture errors in `test_apr01_fixes.py`
    (`seeded` / `tax_year` fixtures don't exist anywhere in conftest).
  - 12 environmental errors in `test_w2_employer_learning.py` — these
    PASS in isolation; the 5-hour run hit the documented pooler-stickiness
    issue with `test_postgres`. Not a code defect.

### Deferrals (carried into Session K Part 2 or beyond)
**Part 2 (next CC session, same branch):**
- Schedule 8812 PDF — download `f1040s8.pdf` 2025, add to
  `forms_manifest.json`, dump AcroForm fields, build field map.
- Form 1040 field map: add Lines 19 + 28 entries to
  `f1040_2025.py`.
- `render_complete_return()` extension — include Schedule 8812 for
  1040 returns.
- End-to-end render verification using
  `assert_value_at_pdf_location` from Session J.
- Session J `family_with_kids.json` fixture: update `expected[19]` from
  pre-OBBBA $4,000 to OBBBA $4,400 (2 × $2,200).
- Final memory updates + merge `feat/sch-8812-ctc-actc` to main.

**Beyond this branch (see DECISIONS.md 2026-05-27):**
- Worksheet B (other-credits competition).
- Full Earned Income Worksheet decomposition.
- Form 2555 (full form vs. boolean toggle).
- Schedule 1 / 2 / 3 / SE / 8959 / EITC — the placeholder fields on
  Taxpayer naturally fall away once those forms land.
- 1040 diagnostics framework — 12 diagnostics defined in the spec
  (D001-D012), none seeded yet.

## Last session recap (2026-05-26 Session J) — Input/Compute/Render Verification rule + 1040 harness Phase 1

- **Goal:** Adopt a stricter "Input/Compute/Render Verification" rule
  (so Session H–style deferred compute can't slip in silently again),
  build the 1040 verification harness scaffolding, and audit Session H's
  deferred work. Light on new code, heavy on guardrails.
- **Range pushed to `origin/main`:** `7784b13..c1f79c3` (6 commits).

| # | SHA       | Message |
|---|-----------|---------|
| 1 | `6bc80fb` | docs: add Input/Compute/Render Verification rule to CLAUDE.md |
| 2 | `cfd6b6e` | docs: record Input/Compute/Render Verification decision in DECISIONS.md |
| 3 | `f073a0d` | feat(1040): verification harness infrastructure (test fixtures + render verification helper + flow assertion stubs) |
| 4 | `a309ee6` | docs(status): audit Session H deferred compute/render work for 1040 |
| 5 | `c1f79c3` | docs(status): document Ken's Rule Studio TODO for 1040 verification gating |
| 6 | (this commit) | chore(memory): record verification rule + 1040 audit findings |

### What landed
- **New verification rule** in `CLAUDE.md` (after "Flow Assertions —
  MANDATORY GATE"). Every input field that affects computed values must
  close (spec, compute, render, flow assertion) in one session, or
  flag the deferral explicitly in this file.
- **Decision entry** in `DECISIONS.md` (2026-05-26) with the Session H
  context that motivated the rule.
- **Harness infrastructure** under `server/`:
  - `tests/fixtures/test_returns/1040/` — README + 3 JSON fixtures
    (simple_w2_only, family_with_kids, retiree_1099s), each pairing
    inputs with expected tax-line outputs, plus a `gaps_today` field
    flagging what won't pass until deferred work lands.
  - `apps/returns/verification.py` — `assert_value_at_pdf_location()`
    pymupdf-based helper, 5-px vertical alignment tolerance.
  - `specs/flow_assertions_1040.json` — empty stub awaiting Ken's
    Rule Studio export.
  - `tests/test_flow_assertions.py` updated to load 1120-S AND 1040
    files, emits a UserWarning when 1040 is empty.
  - `tests/test_render_verification.py` — 8 unit tests for the helper.
- **Per-field audit** in this file's "1040 verification gap" section
  documenting which Session H additions have compute/render today vs.
  which don't (every Dependent field, every W-2 Box 12 code, every
  new InterestIncome box).
- **Ken's TODO** in this file's "1040 — Ken's TODO (Rule Studio work)"
  section listing the 6 priority specs Ken needs to author before
  further 1040 compute/render work can be properly gated.

### Test results
- `tests/test_render_verification.py`: 8/8 passing.
- `tests/test_flow_assertions.py`: 22 passed, 1 skipped (pre-existing),
  1 UserWarning (the expected "1040 stub is empty" notice).
- No other tests touched in this session.

### Notes
- **Plan text correction:** The plan said "W2Income Box 4 (`federal_income_tax_withheld`)
  not wired to Line 25b" — that conflated two boxes. W-2 Box 2
  (`federal_tax_withheld`) IS wired to Line 25a today; the real gap is
  1099-INT Box 4 (also called `federal_tax_withheld`, on
  `InterestIncome`) → Line 25b (which is itself missing from the seed
  + FORMULAS_1040 + FIELD_MAP). The audit reflects what's actually true.
- **No compute or render field-map changes this session.** That's
  explicitly out of scope until Ken authors 1040 Rule Studio specs.

## Last session recap (2026-05-20 Session H) — 1040 entry surface completion

- **Goal:** Finish the 1040 individual return entry surface — Dependents (net-new), full 1099-INT box surface, full W-2 box surface (Box 3-6 wire-up + 7-11 + 13 + 18-20 flat + Box 12/14 coded sub-models), and surface `standard_deduction_override`.
- **Branch:** `claude/reverent-wescoff-950afe` — **13 commits**, base `c634c38`, head `a0baa1f`. **Merged fast-forward to main on 2026-05-20.**
- **Spec / plan:** `docs/superpowers/specs/2026-05-19-1040-entry-surface-design.md` + `docs/superpowers/plans/2026-05-19-1040-entry-surface.md`.

| # | SHA | Message |
|---|-----|---------|
| 1 | `169f1ae` | feat(1040): Dependent model + CRUD + DependentsSection UI |
| 2 | `092fe87` | fix(1040): tighten Dependent CTC/ODC compute methods |
| 3 | `54b3f73` | fix(1040): code review fixes on Dependent model |
| 4 | `882ba7e` | feat(1040): expand InterestIncome to full 1099-INT box surface |
| 5 | `873f6fe` | fix(1040): Box 3 treasury interest flows to Line 2b |
| 6 | `9062b5b` | feat(1040): expand W2Income flat fields (boxes 7-11 + 13 + 18-20) |
| 7 | `cb8448d` | fix(1040): restore autofill coloring on W-2 Box 1/2 + correct expand label |
| 8 | `adc1201` | fix(1040): W-2 expansion help_text + inputCls consistency |
| 9 | `7630146` | feat(1040): W2Box12Entry + W2Box14Entry models + nested endpoints + UI |
| 10 | `a321320` | fix(1040): prefetch box entries + firm-scoping test + Box 14 blank |
| 11 | `5493f7a` | feat(1040): surface standard_deduction_override in Taxpayer Info |
| 12 | `732162d` | chore(memory): update STATUS.md + MEMORY.md after 1040 entry surface session |
| 13 | `a0baa1f` | fix(1040): Taxpayer save triggers recompute + interest footer includes Box 3 |

### Numbers
| Metric | Value |
|---|---|
| Migrations added | 6 (0035, 0036, 0037, 0038, 0039, 0040) |
| New backend models | 3 (`Dependent`, `W2Box12Entry`, `W2Box14Entry`) |
| Tests added | ~30 across 4 new test files (test_dependents, test_interest_income_expansion, test_w2_expansion, test_w2_box_entries) |
| New TypeScript errors | 0 |
| Flow-assertion gate | Not triggered (no compute.py aggregates touched that the 1120-S gate checks) |

### Schema highlights
- `Dependent`: FK to TaxReturn with `related_name="dependents"`. `ctc_override` / `odc_override` are `BooleanField(null=True, default=None)` — None = use computed (under 17 at year-end based on DOB).
- `InterestIncome` shape changed. `amount`+`is_tax_exempt` boolean was migrated into separate `interest_income` (Box 1) + `tax_exempt_interest` (Box 8) decimal fields by migration 0036. Added payer EIN + payer address snapshot + Boxes 2-17.
- `W2Income`: 10 new flat fields (Boxes 7/8/10/11, 3 booleans for Box 13, Box 18/19/20). Migration 0037. `help_text` retroactively added in 0038.
- `W2Box12Entry` / `W2Box14Entry`: nested under W2Income via FK + related_name. Box 12 codes validated against IRS 29-code list at the serializer (codes A-HH minus I/O/U/X/CC).

### Notes
- **CTC compute deferred.** Dependents persist and surface CTC/ODC flags via serializer, but `compute.py` does not yet calculate the credit. Future session.
- **`aggregate_1040_income()` updated** to split Lines 2a/2b from the new `tax_exempt_interest` and `interest_income` fields, plus a follow-up fix to include `treasury_interest` (Box 3) in Line 2b.
- **No flow-assertion impact.** None of this work touches `compute.py` aggregate paths that the 1120-S flow-assertion gate checks.
- **Per-W-2 expand state for "less-common boxes"** is component-local; resets on page navigation. Acceptable for v1 — future polish could persist to localStorage.
- **N+1 prefetch** added to `TaxReturnViewSet.get_queryset()` retrieve branch and the `w2_incomes` GET endpoint for `box_12_entries` / `box_14_entries` / `dependents`. Caught during code review.

## Previous session recap (2026-05-07 Session G) — EIN/Employer database + W-2 autofill
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
- **2026-05-26 (Session J)** — Input/Compute/Render Verification rule + 1040 harness Phase 1. 6 commits pushed directly to `main` (`7784b13..<HEAD>`). Documentation + scaffolding only: new rule in CLAUDE.md + DECISIONS.md, test fixtures + render verification helper + empty 1040 flow assertion stub, full audit of Session H's deferred work, Ken's Rule Studio TODO list. 9 new tests (8 helper + 1 stub guard), 30 passing total in this scope, 0 failures.
- **2026-05-20 (Session H)** — 1040 entry surface completion. 13 commits merged to main fast-forward from `claude/reverent-wescoff-950afe`. 3 new models (Dependent, W2Box12Entry, W2Box14Entry). 6 migrations (0035-0040). ~30 new tests across 4 files. Full backend + UI for Dependents, full 17-box 1099-INT, full W-2 box surface (including Box 12/14 sub-models), and `standard_deduction_override` polish.
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
1. **1040 verification gap closing — Line 19 (CTC).** Blocked on Ken
   authoring the Line 19 spec in Rule Studio (see "1040 — Ken's TODO"
   above). Once exported, wire the CTC compute (Dependent under-17
   eligibility from DOB, $2,000/child base, $400K MFJ / $200K else
   phaseout, refundable portion is ACTC on Line 28), add Line 19 + 22
   + 28 to `seed_1040` + `FIELD_MAP`, add the flow assertion, and
   confirm the `family_with_kids.json` fixture passes end-to-end.
2. **1040 verification gap closing — Line 25b withholding.** Sum
   1099-INT Box 4 (`federal_tax_withheld`) into Line 25b. Add Line 25b
   to `seed_1040` + `FORMULAS_1040` + `FIELD_MAP`. Confirm
   `retiree_1099s.json` passes. Same Rule Studio spec dependency.
3. **1040 verification gap closing — Lines 2a/2b/12a flow assertions.**
   These are wired in compute today but not gated. Once Ken authors
   the specs, exporting them gives us trip-wires for any future
   regression. No code change needed beyond the flow assertion JSON.
4. **Cut B — preparer-side document viewer.** A read-only pane that
   lists W-2 PDFs / 1099 PDFs / source documents the client uploaded,
   indexed by Entity. Pulls from the `documents` app (Session C).
5. **Cut B — PDF preview pane on the W-2 form.** Side-by-side: the W-2
   entry card on the left, the source W-2 PDF (uploaded via the
   documents app) on the right. Lets preparers cross-reference while
   typing without alt-tabbing. Probably embeds via the same `<embed>`-based
   PDF viewer the Forms tab already uses.
6. **Lacerte parser targeted fixes** (~1–2 hours). Cleanup, not
   blocking. Two bounded edits to `lacerte_clientlist_parser.py`:
   - Read `LEFT_COLUMNS["sp_first"]` and `["sp_last"]` as fallback when
     `_parse_name_lnf` returns empty spouse parts.
   - When right-page state OR zip are empty but street/city are populated,
     scan one y-bucket below for the missing values.
7. **Documents app — Supabase Storage bucket + S3 keys** — backend
   ships with conditional STORAGES. To go live, create the
   `tax-documents` bucket in Supabase and add `SUPABASE_S3_ACCESS_KEY` /
   `SUPABASE_S3_SECRET_KEY` / `SUPABASE_URL` to the Render `.env`.
   Until those are set, uploads land on the local filesystem (dev only).
8. **Auto-save rendered returns to client folders** — every PDF render
   should drop a copy in `tax-documents/<firm>/<entity>/<year>/`. Hook
   lives in `renderer.render_complete_return()`.
9. **Partnership importer test coverage** — TODO from Session C. Needs
   synthetic xlsx fixture + extraction of the row-parser into a function.
10. **Test-DB strategy decision** — `config.settings.test` currently
    creates/drops `test_postgres` against the shared prod Supabase
    project. The harmless teardown warning in every run, plus the
    pooler-stickiness recent sessions have hit, both point to "fix
    this soon." Three options documented in `config/settings/test.py`
    docstring.
11. **N+1 cleanup on retrieve serializer.** Pre-existing — `w2_incomes`
    and `interest_incomes` are not in the `prefetch_related` list on
    `TaxReturnViewSet.get_queryset()` retrieve branch. One-line fix.

## 1040 — Ken's TODO (Rule Studio work)

Before any further 1040 compute or render work can be properly gated,
Ken needs to author Rule Studio specs for the 1040 lines Session H
touched. Priority order:

1. **Line 19 — CTC (Child Tax Credit)** — most urgent; Dependents UI
   exists but no compute. Authority: IRC §24, Pub 972, 2025 1040
   instructions.
2. **Line 25a/25b — Withholding aggregation** — W-2 Box 2 sums to 25a;
   W-2 Box 4 sums to 25b; 1099 Box 4 sums to 25b. Currently W-2 Box 4
   not wired.
3. **Line 12a — Standard deduction** — surface override flag exists in
   UI; need the spec for default-from-filing-status logic.
4. **Lines 2a/2b — Interest aggregation** — already wired in compute
   per Session H, but no spec/flow assertion to gate it.
5. **Lines 1a-1z — Wage aggregation** — W-2 Box 1 sums to 1a; allocated
   tips (Box 8) flow to 1g.
6. **Line 28 — ACTC (Additional CTC, refundable portion)** — depends on
   Line 19 CTC compute being done first.

Once specs exist in Rule Studio, run:
  curl -s https://sherpa-tax-rule-studio.onrender.com/api/flow-assertions/export/?entity_type=1040 > server/specs/flow_assertions_1040.json

Then the next session can wire compute + render with flow-assertion
gating in place.

## Known issues / blockers

### Pre-existing test failures surfaced by Session K full-suite run
- **`test_tts_forms.TestManifest.test_manifest_is_valid_json`** — asserts
  `len(data["forms"]) == 22` but the manifest has 23 entries. 1-line
  fix; not done this session per scope. Pre-dates Session K.
- **`test_apr01_fixes.py`** — 3 ERROR collections: `seeded` and
  `tax_year` fixtures referenced but not defined anywhere in conftest.
  Pre-dates Session K.
- **`test_w2_employer_learning.py`** — 12 ERROR collections under long
  suite runs. PASSES in isolation. Pooler-stickiness on shared
  Supabase `test_postgres` during 5h+ runs. Documented intermittent
  issue.

### 1040 verification gap (Session H deferred work — audit 2026-05-26)

Session H added input UI + models for the 1040 module without closing
the Input/Compute/Render chain. The new verification rule
(`CLAUDE.md` "Input/Compute/Render Verification — MANDATORY") makes
this gap explicit. Below is the per-field inventory.

**Legend:** ✅ wired today / ❌ deferred / N/A no impact on federal compute.

#### `Dependent` model (Session H, migration 0035)
| Field          | Compute                              | Render                              | Flow assertion |
|----------------|--------------------------------------|-------------------------------------|----------------|
| first/middle/last name, ssn | N/A — identity only       | ❌ no Dependents block in `f1040_2025.py` field map (max 4 IRS slots) | N/A |
| relationship   | N/A                                  | ❌ same                              | N/A |
| date_of_birth  | ❌ feeds CTC age test (under-17) — Line 19 unimplemented | ❌ no Dependents block | ❌ |
| ctc_override / odc_override | ❌ should override DOB-based CTC eligibility for Line 19 / Line 28 | ❌ no Dependents block | ❌ |
| **Line 19 (CTC)** target | ❌ not in `FORMULAS_1040`, not in seed_1040 | ❌ not in `FIELD_MAP` (Line 16 → 24, skips 17-23) | ❌ |
| **Line 22 subtotal** | ❌ not in `FORMULAS_1040`, not in seed | ❌ not in FIELD_MAP | ❌ |
| **Line 28 (ACTC, refundable)** | ❌ not in `FORMULAS_1040`, not in seed | ❌ not in FIELD_MAP | ❌ |

#### `W2Income` Session H additions (migrations 0037/0038)
| Field (Box)                          | Compute                                  | Render                | Flow assertion |
|--------------------------------------|------------------------------------------|-----------------------|----------------|
| Box 2 `federal_tax_withheld` (pre-Session H, but worth listing) | ✅ summed to Line 25a in `aggregate_1040_income` | ✅ in FIELD_MAP | ❌ no 1040 assertions |
| Box 3 `social_security_wages`        | N/A federal — used for SS-tax reconciliation only | N/A | N/A |
| Box 4 `social_security_tax`          | ❌ Excess-SS credit on Schedule 3 Line 11 — not built; plan text "W2Income Box 4 → Line 25b" was incorrect (that's a 1099-INT Box 4 issue, see below) | N/A on 1040 directly | ❌ |
| Box 5 `medicare_wages`               | N/A federal flow                          | N/A | N/A |
| Box 6 `medicare_tax`                 | N/A federal flow (Add'l Medicare on 8959) | N/A on 1040 directly | N/A |
| Box 7 `social_security_tips`         | N/A federal flow                          | N/A | N/A |
| Box 8 `allocated_tips`               | ❌ should add to Line 1g (allocated tips); today only Line 1a is summed | ❌ no Line 1g in FIELD_MAP | ❌ |
| Box 10 `dependent_care_benefits`     | ❌ Form 2441 input; affects Line 1e — not built | ❌ no Line 1e | ❌ |
| Box 11 `nonqualified_plans`          | N/A — informational on the W-2 only       | N/A | N/A |
| Box 13 `statutory_employee` (bool)   | ❌ should re-route wages to Schedule C — not built | N/A | ❌ |
| Box 13 `retirement_plan` (bool)      | N/A — affects IRA deduction calc on Schedule 1 (not built) | N/A | N/A |
| Box 13 `third_party_sick_pay` (bool) | N/A — informational                       | N/A | N/A |
| Box 16/17 `state_*`                  | N/A federal                              | N/A on 1040; state form | N/A |
| Box 18/19/20 `local_*`               | N/A federal                              | N/A | N/A |

#### `W2Box12Entry` codes (Session H, migration 0039)
All 29 codes persisted; **none are compute-wired today.** Per IRS Pub 15-B / 2025 1040 instructions, code-by-code impact:

| Code  | What it is                                  | Federal 1040 compute impact (target) | Wired? |
|-------|---------------------------------------------|--------------------------------------|--------|
| A, B  | Uncollected SS / Medicare on tips           | Adds to Line 16 via Schedule 2 Line 13 | ❌ |
| C     | GTL > $50K coverage cost                    | Informational (already in Box 1)      | ❌ |
| D     | 401(k) elective deferral                    | Informational (already excluded from Box 1) — but used for retirement-savings-credit lookback | ❌ |
| E     | 403(b) elective deferral                    | Same as D                             | ❌ |
| F     | 408(k)(6) SARSEP                            | Same as D                             | ❌ |
| G     | 457(b) elective deferral                    | Same as D                             | ❌ |
| H     | 501(c)(18)(D) tax-exempt org elective       | Adjustment on Schedule 1 Line 24f (not built) | ❌ |
| J     | Nontaxable sick pay                         | Informational                         | ❌ |
| K     | 20% golden-parachute excise                 | Adds to Line 17 (additional taxes from Schedule 2) | ❌ |
| L     | Substantiated employee biz expense reimbursements | Informational                  | ❌ |
| M, N  | Uncollected SS / Medicare on GTL > $50K (former employee) | Schedule 2 Line 13          | ❌ |
| P     | Excludable moving exp reimbursements (Armed Forces) | Informational                  | ❌ |
| Q     | Nontaxable combat pay                       | EIC / additional CTC computation       | ❌ |
| R     | Archer MSA employer contributions           | Form 8853 input                       | ❌ |
| S     | 408(p) SIMPLE retirement elective           | Like D                                | ❌ |
| T     | Adoption benefits                           | Form 8839 input                       | ❌ |
| V     | NQSO income (incl. in Box 1)                | Informational                         | ❌ |
| W     | HSA employer + employee contributions       | Form 8889 input → Schedule 1 Line 13 HSA deduction | ❌ |
| Y     | Section 409A nonqualified deferred comp     | Informational                         | ❌ |
| Z     | Section 409A income not satisfying 409A     | Schedule 2 Line 8 (20% additional tax) | ❌ |
| AA    | Roth contribution to 401(k)                 | Saver's-credit lookback               | ❌ |
| BB    | Roth contribution to 403(b)                 | Saver's-credit lookback               | ❌ |
| DD    | Employer-sponsored health coverage          | Informational only                    | N/A |
| EE    | Roth contribution to governmental 457(b)    | Saver's-credit lookback               | ❌ |
| FF    | QSEHRA permitted benefit                    | Informational                         | ❌ |
| GG    | Qualified equity grants under §83(i)        | Schedule 1 Line 8u                     | ❌ |
| HH    | Aggregate deferrals under §83(i)            | Informational                         | ❌ |

**None of the above are compute-wired today.** Highest-value to wire next: W (HSA), D/E/F/G/S (saver's credit lookbacks), AA/BB/EE (saver's credit), Q (combat-pay EIC).

#### `W2Box14Entry` (Session H, migration 0039)
Free-text description + amount. **No federal 1040 compute impact** in general; some descriptions (e.g., NJ FLI, CA SDI, NY PFL) affect state returns. **N/A** for the 1040 verification gap audit. Render: not currently rendered to Form 1040 — `f1040_2025.py` has no Box-14 block (the IRS form has 4 Box-14 slots per W-2, currently blank).

#### `InterestIncome` Session H expansion (migration 0036)
| Field (Box)                          | Compute                                       | Render            | Flow assertion |
|--------------------------------------|------------------------------------------------|-------------------|----------------|
| Box 1 `interest_income`              | ✅ summed to Line 2b in `aggregate_1040_income` (incl. Box 3) | ✅ in FIELD_MAP | ❌ |
| Box 2 `early_withdrawal_penalty`     | ❌ should flow to Schedule 1 Line 18 — not built | N/A on 1040 directly | ❌ |
| Box 3 `treasury_interest`            | ✅ summed into Line 2b alongside Box 1 (fixed in commit `a0baa1f`) | ✅ via Line 2b   | ❌ |
| Box 4 `federal_tax_withheld`         | ❌ should sum to Line 25b — **the actual Session H deferral** (Line 25b is also missing from seed_1040 + FORMULAS_1040 + FIELD_MAP) | ❌ Line 25b not in FIELD_MAP | ❌ |
| Box 5 `investment_expenses`          | N/A — Schedule A info only (TCJA suspended)  | N/A | N/A |
| Box 6 `foreign_tax_paid`             | ❌ Schedule 3 Line 1 / Form 1116 — not built  | N/A on 1040 directly | ❌ |
| Box 7 `foreign_country`              | N/A — Form 1116 metadata                       | N/A | N/A |
| Box 8 `tax_exempt_interest`          | ✅ summed to Line 2a in `aggregate_1040_income` | ✅ in FIELD_MAP | ❌ |
| Box 9 `pab_interest`                 | ❌ AMT preference (Form 6251 Line 2g) — not built | N/A on 1040 directly | ❌ |
| Box 10 `market_discount`             | ❌ Schedule B input — not built                | N/A | ❌ |
| Box 11 `bond_premium`                | ❌ reduces taxable interest on Schedule B — not built | N/A | ❌ |
| Box 12 `treasury_bond_premium`       | ❌ same logic for treasury portion — not built | N/A | ❌ |
| Box 13 `tax_exempt_bond_premium`     | ❌ reduces Box 8 → Line 2a — not built         | N/A | ❌ |
| Box 14 `cusip_number`                | N/A — Schedule B metadata                      | N/A | N/A |
| Box 15-17 (state)                    | N/A federal                                    | N/A on 1040 directly | N/A |

#### `Taxpayer.standard_deduction_override` (Session H, surface)
- Compute: ✅ honored by `aggregate_1040_income` Line 12 path.
- Render: ✅ Line 12 in `FIELD_MAP`.
- Flow assertion: ❌ none.

#### Summary by 1040 line
| Line | Description                | Compute | Render | Notes |
|------|----------------------------|---------|--------|-------|
| 1a   | W-2 wages                  | ✅      | ✅     | covered |
| 1e   | Dependent care benefits taxable | ❌  | ❌     | W-2 Box 10 |
| 1g   | Allocated tips             | ❌      | ❌     | W-2 Box 8 |
| 1z   | Wage subtotal              | ✅ (= 1a today) | ✅ | covered for the simple case |
| 2a   | Tax-exempt interest        | ✅      | ✅     | covered |
| 2b   | Taxable interest           | ✅      | ✅     | covered |
| 8    | Other income (Sched 1)     | N/A (Schedule 1 not built) | ✅ in FIELD_MAP | upstream missing |
| 11   | AGI                        | ✅      | ✅     | covered |
| 12   | Standard / itemized deduction | ✅   | ✅     | override honored |
| 13   | QBI                        | N/A (input only) | ✅ | manual entry |
| 15   | Taxable income             | ✅      | ✅     | covered |
| 16   | Tax                        | ✅ (brackets only — no Sch D / 8814 / cap gain worksheet) | ✅ | covered for ordinary income |
| 17   | Sched 2 Line 3 amount      | ❌      | ❌ not in FIELD_MAP | Sched 2 not built |
| **19** | **Child tax credit**     | ❌      | ❌ not in FIELD_MAP | **#1 priority** |
| 20   | Sched 3 Line 8 credits     | ❌      | ❌ | Sched 3 not built |
| 21   | Add credits                | ❌      | ❌ | depends on 19, 20 |
| **22** | **Line 16 + 17 − 21**    | ❌      | ❌ not in FIELD_MAP | depends on 19, 20, 21 |
| 24   | Total tax                  | ✅ (= 16 today) | ✅ | wrong once 17/22/23 are real |
| 25a  | W-2 withholding            | ✅      | ✅     | covered |
| **25b** | **1099 withholding**    | ❌      | ❌ not in seed + FIELD_MAP | from 1099-INT Box 4 |
| 25c  | Other forms withholding    | ❌      | ❌ | not in seed |
| 25d  | Total withholding          | ✅ (= 25a today) | ✅ | wrong until 25b/25c land |
| **28** | **Additional CTC (refundable)** | ❌ | ❌ not in seed/FIELD_MAP | depends on Line 19 |
| 33   | Total payments             | ✅ (= 25d today) | ✅ | wrong without credits/EIC/Sched 3 |
| 34   | Overpaid                   | ✅      | ✅     | recursively wrong |
| 37   | Owed                       | ✅      | ✅     | recursively wrong |

**Net: 1040 has compute wired for 9 lines (1a, 1z, 2a, 2b, 9, 11, 12, 14, 15, 16, 24, 25a, 25d, 33, 34, 37), with gaps in 1e, 1g, 17, 19, 20, 21, 22, 25b, 25c, 28 — plus the entire CTC dependent logic + Schedule 1/2/3 framework.** No 1040 flow assertions exist.

- **Lacerte parser — 2 bounded bugs documented** (Anomalies 1 and 2). 7 / 122 records have minor field gaps. Usable as-is for development data; targeted fixes queued as next-session #4.
- **Documents app — Supabase Storage not yet wired in prod.** Code is conditional on `SUPABASE_S3_ACCESS_KEY`; without it Django falls back to local FS.
- **Employer database — 4 malformed-EIN rows from the TaxWise CSV silently dropped on import.** Logged as errors in the import summary but not preserved. If those 4 employers ever get a W-2 typed in, the learning loop will create a clean record for them.
- **Partnership importer has no automated test** — TODO in commit body of `8a27ade`.
- **Test-DB teardown warning + pooler stickiness** — known intermittent issue; mid-session manual `pg_terminate_backend` may be required. Permanent fix tied to test-DB strategy decision.
- **Yellow autofill indicator is session-scoped only.** Across page reloads, the W-2 entry UI loses the yellow markers (autofilled fields render as green like user-entered ones). Persistent autofill-state tracking is a future polish.
- Empty `Lacerte Export\` dir shell at repo root persists (locked by Explorer/SearchIndexer; resolves on reboot). Invisible to git.
