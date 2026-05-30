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

### 2026-05-29 — Form 1040 (2025) field map keys: semantic, not syntactic

**Decision:** When the IRS form renumbers or sub-letters a line, we keep
the existing internal key (used by `seed_1040` + `compute.py`) and
point it at the 2025 widget that holds the same semantic value. We do
NOT refactor seed + compute to track IRS sub-letters.

**Context:** The 2025 IRS Form 1040 was substantially redesigned for
OBBBA. AGI is labeled "11a" (not "11"); standard deduction is "12e"
(not "12"); QBI is "13a" (not "13"); Lines 14-15 moved from page 1 to
page 2; and "13b" (Senior Bonus Deduction) is new. The 2026-05-29
field-map audit found 17 of 19 FIELD_MAP entries pointed at wrong
widgets — partly because of these renumbers + reorderings.

**Trade-off:** This preserves the seed → compute → render contract
exactly as it was. Renderer reads `FormFieldValue.value` keyed by
the legacy line_number and places it at whatever widget the 2025 PDF
expects. Compute code remains unaware of the IRS sub-lettering. The
cost is a small comment burden in `f1040_2025.py` documenting which
internal key → which 2025 IRS label.

**When to revisit:** If/when a future year's form materially changes
the semantic flow (not just the label) — e.g., AGI gets split into two
separate inputs, or QBI moves out of the deductions section — we'd
need to refactor compute. Until then, semantic keys are stable across
IRS form revisions and the seed → compute pipeline stays untouched.

### Render assertion gate for AcroForm field maps

**Decision:** Any new or revised AcroForm `FIELD_MAP` (or `HEADER_MAP`)
must be locked in with a parametrized render assertion test using
`assert_value_at_widget_position`. Each FIELD_MAP key gets one test
case that writes a distinct, identifiable value to a FormFieldValue
row and asserts it lands at the declared widget rect on the rendered
PDF.

**Context:** Distinct values per line (e.g., 1a=100001, 1z=100002,
2a=203) are not just defensive — they're load-bearing. A mis-routed
mapping that puts Line 1z's value at Line 1a's widget would
silently pass a single shared value, but with distinct values per
key it fails because the wrong value lands at the wrong position.

**Trade-off:** The test adds one render per N lines (parametrized
sweep), which is a few seconds. Worth it — Form 1040's pre-audit
mappings were 89% wrong (17 of 19), and the rendered PDFs would have
shipped misaligned without a position-based gate. The same gate
should apply prospectively to every other AcroForm field map (1120S,
1065, 1120, etc.) — not retroactively required, but new edits to
those files trigger the rule.

### 2026-05-27 — Schedule 8812 (CTC/ACTC/ODC) compute model — Session K (1)

**Decision:** Schedule 8812 (TY 2025) is implemented as its own
`FormDefinition` (code `SCH_8812`, 32 lines across 3 sections — Part I,
Part II-A, Part II-B). Its `FormFieldValue` rows are stored on the
parent 1040 `TaxReturn` (same `tax_return` FK), not on a separate
sibling return. The `FormLine.section.form` distinction preserves the
cross-form semantics for flow assertions; avoiding a new `parent_return`
FK on `TaxReturn` keeps the data model simple.

**Compute lives in `apps.returns.compute_8812`.** All 30 spec rules
(R001-R030) translated. Entry point `compute_sch_8812(tax_return)` is
called from `compute_return()` for `form_code=="1040"` between the
first downstream-formula pass (which sets Line 18 = `tax_before_ctc`)
and a second downstream pass (which propagates Lines 19 + 28 to 21 /
22 / 24 / 33 / 34 / 37).

**Spec ground truth wins where rules and scenarios disagree.** Spec
rule R018 reads `L_16a = … if actc_eligible else 0`, but scenarios TS09b
+ TS13 disambiguate the gate as `NOT files_form_2555 AND
return_ssn_eligible` (not the full `actc_eligible` which also requires
`count_qualifying_children > 0`). Implementation follows the scenarios.

**Constants from spec (TY 2025 / OBBBA §70104):**
- QC credit = $2,200 (per qualifying child with valid SSN)
- ODC credit = $500 (per other dependent)
- Phaseout thresholds: $400K MFJ / $200K other
- ACTC per-child cap: $1,700
- ACTC earned-income floor: $2,500; 15% method

### Session 2 (2026-05-28) — Closed (merged to main)

**All items from the Session 2 list landed:**
- Schedule 8812 PDF `f1040s8.pdf` (2025) — in manifest + at
  `resources/irs_forms/2025/f1040s8.pdf` (SHA recorded).
- `field_maps/f1040s8_2025.py` — 32-line AcroForm field map.
- Form 1040 field map (`f1040_2025.py`) — Lines 19 (CTC) + 28 (ACTC)
  added. (Note: the other 1040 line mappings are wrong for the 2025
  PDF — that's a pre-existing audit item, separate from this session.)
- `render_sch_8812(tax_return)` + integration into `render_complete_return`
  as step 1a (after main 1040, before Form 8879-S).
- `assert_value_at_widget_position` helper added in
  `apps/returns/verification.py` (AcroForm widgets are flattened to
  text spans during rendering — position-based lookup is what works
  post-render).
- Three end-to-end render assertions in `tests/test_sch_8812_render.py`
  (CTC-only, ACTC-eligible, Form 2555 zero-out).
- `family_with_kids.json` updated for OBBBA $4,400 + the strict-choice
  `"child"` relationship code.
- OBBBA $2,200 cap is now tax-year-parameterized via
  `apps.returns.compute_8812._constants_for_year(tax_year)`. TY 2024
  returns produce the pre-OBBBA $2,000 cap; TY 2025+ produce the
  OBBBA $2,200 cap.

### Deferrals — still open (beyond Session 2)

**Deferred beyond this branch (intentional):**
- **Worksheet B** (other credits competing for the CLW-A cap — Form
  8396 / 8839 / 5695 Part I / 8859). Today uses standard L_13 formula.
  Diagnostic D009 fires when `claims_credits_requiring_worksheet_b`
  is set, but Worksheet B math is not modeled.
- **Earned Income Worksheet** (full decomposition). Today uses the
  simplified path: W-2 wages + `(deductible_se_tax_half * 2)` SE proxy
  + `nontaxable_combat_pay`. The full worksheet adds nontaxable
  retirement / disability / minister housing / 911 adjustments.
- **Form 2555 itself** — modeled as a boolean toggle
  (`Taxpayer.files_form_2555`) + a placeholder excluded amount field.
  The full Form 2555 (foreign earned income exclusion, housing
  exclusion / deduction) is its own future spec.
- **Schedule 1 / Schedule 2 / Schedule 3** — not yet built. Schedule 8812
  reads the totals it needs as preparer-entered placeholder fields on
  `Taxpayer`:
  - `schedule_3_pre_ctc_credits_total` (Sch 3 lines 1-6 sum)
  - `additional_medicare_tax_amount` (Form 8959 line 7)
  - `deductible_se_tax_half` (Sch 1 line 15)
  - `se_tax_total` (Sch 2 line 5)
  - `unreported_ss_medicare_tax` (Sch 2 line 6)
  - `other_employment_taxes` (Sch 2 line 13)
  - `eitc_claimed` (Form 1040 Line 27a)
  - `excess_ss_rrta_withheld` (Sch 3 line 11)
  - 1040 Lines 17, 20, 23 (also preparer-entered).
  All default to 0 — the placeholder values fall away naturally when
  the underlying forms land.
- **Diagnostic framework for 1040** — spec defines 12 diagnostics
  (D001-D012) covering "taxpayer SSN missing", "MAGI near phaseout",
  "Part II-B verify path", etc. The 1040 module has no
  `DiagnosticRule` rows seeded yet (1120-S has 40+). Scenarios that
  expect `D###_fires` are silently un-asserted by the test runner
  today; the assertions are documented in the spec and tracked as a
  follow-up.

### 2026-05-26 — Input/Compute/Render Verification rule adopted

**Decision:** Every input field added to a tax form must be wired to
compute and render in the same session, gated by flow assertions. No
more "deferred compute" debt allowed to accumulate without an explicit
flag in STATUS.md.

**Context:** Session H (2026-05-20) added a substantial 1040 entry
surface — Dependents, full 1099-INT box surface, full W-2 box surface
including Box 12/14 sub-models — but explicitly deferred CTC compute,
W-2 Box 4 → Line 25b withholding, and any verification that new fields
render correctly. The 1040 module had no Rule Studio specs and no flow
assertions, so the deferrals weren't caught by any automated check.
A return with dependents under 17 would silently produce wrong Line 19
(CTC) values.

**Trade-off:** Sessions become smaller in scope. One input + its compute
+ its render + its flow assertion is a lot for one session. This is
acceptable because tax-law accuracy is the #1 priority per CLAUDE.md.

**Infrastructure required for the 1040:**
- 1040 Rule Studio specs (Ken authors; parallel to existing 1120-S
  specs)
- 1040 flow assertions exported from Rule Studio into this repo
- A 1040 render verification mechanism (programmatic check that values
  land in correct PDF coordinates)
- Test return fixtures (defined in `server/tests/fixtures/test_returns/1040/`)

**Backfill required:** Session H's deferred compute + render work
(see STATUS.md "1040 verification gap" section).

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
