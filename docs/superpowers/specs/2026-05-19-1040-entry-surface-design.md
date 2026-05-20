# 1040 Entry Surface — Finishing Pass

**Date:** 2026-05-19
**Author:** Claude (brainstormed with Ken)
**Status:** Approved design — ready for implementation plan

## Goal

Complete the 1040 individual return entry surface so a preparer can fully type up a real W-2 + interest-income return in the Sherpa tax app. This closes the in-progress thread from STATUS.md ("1040 UI work — partially started by Session G"), picking up where the EIN/employer database + W-2 autofill work landed on 2026-05-07.

## Scope

Four pieces, all shipped in one session, sequenced as independent commits:

1. **Dependents** — new `Dependent` model + CRUD endpoints + new "Dependents" tab in the 1040 UI.
2. **Interest income** — expand `InterestIncome` to the full 17-box 1099-INT surface, rewrite the entry UI as a card-per-1099-INT (matches the W-2 layout shift from Session G).
3. **W-2 income** — surface existing nullable Box 3–6 fields in the UI; add new flat fields (Box 7/8/10/11 amounts, Box 13 booleans, Box 18–20 local); add `W2Box12Entry` and `W2Box14Entry` models for the multi-row coded entries.
4. **Taxpayer Info polish** — surface the already-existing `standard_deduction_override` field in the entry form.

Compute follow-ons are deliberately kept minimal: the `aggregate_1040_income()` change for the interest split is included in this session, but CTC/ACTC compute is deferred — Dependents persist to the DB and render in the UI but the credit calculation comes in a later session.

## Out of scope

- CTC / ACTC credit computation (dependents-driven). Surfaced in serializer + UI as a flag, not computed in `compute.py`.
- Itemized deductions, Schedules C/D/E, AMT, foreign tax credit — all still pending per the "1040 rough draft skeleton" caveat in MEMORY.md.
- Second-locality Box 18-20 set on W-2 (one set of fields only — most W-2s use one locality at most).
- Persistent autofill-origin tracking (the W-2 yellow-marker session-scoping note from MEMORY.md stays as a known polish gap).

## Data models

### New: `Dependent`

FK to `TaxReturn` (`related_name="dependents"`), one row per dependent.

| Field | Type | Notes |
|---|---|---|
| `id` | `UUIDField(primary_key=True)` | Same pattern as existing 1040 models |
| `tax_return` | `ForeignKey(TaxReturn, on_delete=CASCADE)` | `related_name="dependents"` |
| `first_name` | `CharField(max_length=100, blank=True, default="")` | |
| `middle_initial` | `CharField(max_length=1, blank=True, default="")` | |
| `last_name` | `CharField(max_length=100, blank=True, default="")` | |
| `ssn` | `CharField(max_length=11, blank=True, default="")` | XXX-XX-XXXX |
| `relationship` | `CharField(max_length=50, blank=True, default="")` | Free text — IRS form leaves this open |
| `date_of_birth` | `DateField(null=True, blank=True)` | Drives CTC/ODC default |
| `ctc_override` | `BooleanField(null=True, default=None)` | `None` = use computed default |
| `odc_override` | `BooleanField(null=True, default=None)` | `None` = use computed default |
| `order` | `IntegerField(default=0)` | Display ordering |
| `created_at` / `updated_at` | Auto timestamps | |

Computed (read-only on serializer, not stored):
- `qualifies_ctc`: `True` if dependent is under 17 at year-end (`tax_year` + 12/31), unless `ctc_override` is set. CTC override wins when not None.
- `qualifies_odc`: `True` if dependent and not CTC-eligible, unless `odc_override` is set.

UI surfaces these as checkbox state + color (yellow when computed, green when overridden). Clicking a checkbox flips it to override mode; a small "↺ reset" link clears the override back to computed.

### New: `W2Box12Entry`

FK to `W2Income` (`related_name="box_12_entries"`).

| Field | Type | Notes |
|---|---|---|
| `id` | `UUIDField(primary_key=True)` | |
| `w2_income` | `ForeignKey(W2Income, on_delete=CASCADE)` | |
| `code` | `CharField(max_length=2, choices=BOX_12_CODES)` | Full IRS list (A, B, C, D, E, F, G, H, J, K, L, M, N, P, Q, R, S, T, V, W, Y, Z, AA, BB, DD, EE, FF, GG, HH) |
| `amount` | `DecimalField(15, 2)` | |
| `order` | `IntegerField(default=0)` | |
| `created_at` / `updated_at` | Auto timestamps | |

`BOX_12_CODES` lives in `apps.returns.models` next to `FilingStatus`. No hard cap on entry count — UI shows a warning when more than 4 entries exist ("IRS Form W-2 only has 4 Box 12 slots") but does not reject.

### New: `W2Box14Entry`

FK to `W2Income` (`related_name="box_14_entries"`).

| Field | Type | Notes |
|---|---|---|
| `id` | `UUIDField(primary_key=True)` | |
| `w2_income` | `ForeignKey(W2Income, on_delete=CASCADE)` | |
| `description` | `CharField(max_length=100)` | Free text — "UNION DUES", "RR RETIREMENT", etc. |
| `amount` | `DecimalField(15, 2)` | |
| `order` | `IntegerField(default=0)` | |
| `created_at` / `updated_at` | Auto timestamps | |

### Expanded: `W2Income`

New flat fields (all `DecimalField(15, 2, null=True, blank=True)` unless noted):

- Box 7 `social_security_tips`
- Box 8 `allocated_tips`
- Box 10 `dependent_care_benefits`
- Box 11 `nonqualified_plans`
- Box 13 (3 `BooleanField(default=False)`): `statutory_employee`, `retirement_plan`, `third_party_sick_pay`
- Box 18 `local_wages`
- Box 19 `local_income_tax`
- Box 20 `locality_name` (`CharField(max_length=50, blank=True, default="")`)

Boxes 3–6 already exist as nullable on `W2Income` (per `models.py:1481-1496`) — no model change for those, just UI wire-up.

### Expanded: `InterestIncome` (with data migration)

Restructure to fit a full 1099-INT. Current `amount` + `is_tax_exempt` flag splits into two distinct amount fields because a real 1099-INT can have both taxable (Box 1) and tax-exempt (Box 8) on the same form.

**Schema change:**
- Rename `amount` → `interest_income` (Box 1).
- Drop `is_tax_exempt`.
- Add `tax_exempt_interest` (Box 8).
- Add payer EIN + payer address snapshot fields: `payer_ein`, `payer_street`, `payer_city`, `payer_state`, `payer_zip` (same snapshot pattern as W-2 employer address).
- Add remaining boxes: Box 2 `early_withdrawal_penalty`, Box 3 `treasury_interest`, Box 4 `federal_tax_withheld`, Box 5 `investment_expenses`, Box 6 `foreign_tax_paid`, Box 7 `foreign_country` (CharField), Box 9 `pab_interest`, Box 10 `market_discount`, Box 11 `bond_premium`, Box 12 `treasury_bond_premium`, Box 13 `tax_exempt_bond_premium`, Box 14 `cusip_number` (CharField), Box 15 `state_code` (CharField max 2), Box 16 `state_id_number` (CharField), Box 17 `state_tax_withheld`.

**Data migration (forward):**
For every existing row:
- If `is_tax_exempt=True`: set `tax_exempt_interest = amount`, `interest_income = 0`.
- If `is_tax_exempt=False`: set `interest_income = amount`, `tax_exempt_interest = 0` (effectively a rename).

Then drop `is_tax_exempt` and `amount`. Migration is reversible (best-effort — round-trip collapses both fields into `amount` and sets `is_tax_exempt` from whichever was non-zero; ambiguous when both are non-zero, in which case the reverse picks `interest_income` and warns).

### `Taxpayer` — no model change

`standard_deduction_override` already exists at `models.py:1447-1450`. Only the UI needs the input added.

## API surface

All endpoints follow the existing nested-under-`tax-returns` pattern from `apps.returns.views`. Permission: `IsFirmMember`. New viewsets scope to `request.firm`.

### Dependents

```
GET    /api/v1/tax-returns/{id}/dependents/
POST   /api/v1/tax-returns/{id}/dependents/
PATCH  /api/v1/tax-returns/{id}/dependents/{dep_id}/
DELETE /api/v1/tax-returns/{id}/dependents/{dep_id}/
```

Serializer returns `qualifies_ctc` / `qualifies_odc` as read-only computed fields. Uses `ctc_override` / `odc_override` when not None; otherwise computes from `date_of_birth` + the parent `TaxReturn.tax_year`.

### W-2 Box 12 / Box 14 entries

```
GET    /api/v1/tax-returns/{id}/w2-incomes/{w2_id}/box-12-entries/
POST   /api/v1/tax-returns/{id}/w2-incomes/{w2_id}/box-12-entries/
PATCH  /api/v1/tax-returns/{id}/w2-incomes/{w2_id}/box-12-entries/{entry_id}/
DELETE /api/v1/tax-returns/{id}/w2-incomes/{w2_id}/box-12-entries/{entry_id}/
```

Same shape for `box-14-entries/`.

Box 12 code field validates against `BOX_12_CODES` choices at the serializer level — invalid codes return 400 with a clear message.

### Expanded existing endpoints

`/tax-returns/{id}/w2-incomes/{...}/` and `/tax-returns/{id}/interest-incomes/{...}/` keep their routes; serializers expand to include the new fields. No URL changes for these.

### Taxpayer

No API change. The existing PATCH on `/tax-returns/{id}/taxpayer/` already covers `standard_deduction_override`.

### Learning loop interaction

The W-2 viewset's existing learning loop (`apps.employers.learning.sync_w2_to_employer_db`) is unaffected. None of the new W-2 fields are employer-level data (no new fields land on the central `Employer` table), so the helper still only writes employer name/address/EIN/Box 15 state. The new Box 12 and Box 14 entries are per-W-2 data, never promoted upstream.

## UI shape

### Tab restructure (`INDIVIDUAL_TABS`)

5 tabs (was 4):

| # | Label | Section ID |
|---|---|---|
| 1 | Taxpayer Info | `taxpayer_info` |
| 2 | **Dependents** *(new)* | `dependents` |
| 3 | W-2 Income | `w2_income` |
| 4 | Interest Income | `interest_income` |
| 5 | Tax Summary | `tax_summary` |

Order matches IRS Form 1040 reading order (filer → dependents → wages → interest → tax). The new `DependentsSection` function wires into the existing outlet switch in `FormEditor.tsx` next to the other 1040 section functions.

### TaxpayerInfoSection (small addition)

Add one input at the bottom of the Address block: **Standard Deduction Override** — currency input. Yellow tint when blank (filing-status default applies) with a hint label showing the computed default. Green tint when manually entered. All other fields remain untouched.

### DependentsSection (new)

Hand-rolled Tailwind table per DECISIONS.md "no third-party grid library." Columns:

| First | MI | Last | SSN | Relationship | DOB | CTC | ODC | Delete |
|---|---|---|---|---|---|---|---|---|

- "+ Add Dependent" button creates a row with empty defaults.
- CTC/ODC are checkboxes. They show the computed state by default with a yellow tint on the label. Clicking flips to override mode (green tint, value locked to user-chosen state). Each cell has a small "↺ reset" link that clears the override back to computed.
- Color convention follows CLAUDE.md: green = user-typed, yellow = computed/autofilled, red = error.
- Delete button per row (`text-danger` link, same pattern as `InterestIncomeSection`).

### W2IncomeSection (expanded — largest UI change)

Current Session-G layout has three rows: identity + amounts (Box 1, 2 only), employer address, Box 15. Expanded layout adds:

- **Wage boxes row (always visible)** — 4-column grid: Box 1 Wages, Box 2 Fed W/H, Box 3 SS Wages, Box 4 SS Tax, Box 5 Medicare Wages, Box 6 Medicare Tax, Box 7 SS Tips, Box 8 Allocated Tips. These are the everyday numbers — always shown.
- **Less-common row (collapsed by default with expand link)** — Box 10 Dependent Care Benefits, Box 11 Nonqualified Plans, Box 13 (3 checkboxes inline), Box 14 entries list (add/remove rows of description + amount).
- **State + local row** (extends the current Box 15 row) — state code, employer state ID (autofilled from `EmployerStateAccount` cache), Box 16 State Wages, Box 17 State Tax W/H. Below: Box 18 Local Wages, Box 19 Local Tax, Box 20 Locality Name.
- **Box 12 entries row** — small list (code dropdown + amount), "+ Add Box 12 Code" button. Code dropdown shows full IRS A–HH list. Soft warning when more than 4 entries exist.

The existing Session-G yellow autofill markers stay session-scoped (the known polish gap noted in MEMORY.md). Box 12/14 entries are user-typed, so they're always green.

### InterestIncomeSection (expanded — table → cards)

Current 3-column flat table becomes a **card per 1099-INT** (same shape shift as W-2 in Session G). With 17 boxes a table is unreadable; a card matches the visual layout of a real 1099-INT slip.

Each card:
- **Header row**: Payer Name (large), Payer EIN, Delete button.
- **Address row**: Payer street/city/state/zip (4 columns).
- **Box row**: Box 1 (taxable), Box 2 (early withdrawal), Box 3 (Treasury), Box 4 (Fed W/H), Box 5 (investment exp), Box 6 (foreign tax), Box 7 (foreign country — text), Box 8 (tax-exempt), Box 9 (PAB), Box 10 (market discount), Box 11 (bond prem), Box 12 (Treasury bond prem), Box 13 (tax-exempt bond prem), Box 14 (CUSIP — text).
- **State row**: Box 15, Box 16, Box 17.
- **Bottom summary line** (across all cards): "Taxable: $X · Tax-Exempt: $Y" — sourced from `interest_income` + `tax_exempt_interest`.

## Compute / downstream considerations

### Interest income compute change (in-session)

`aggregate_1040_income()` in `compute.py` currently sums `InterestIncome.amount` for line 2b. After the split:
- Line 2a (tax-exempt interest) sums `tax_exempt_interest`.
- Line 2b (taxable interest) sums `interest_income`.

That's a one-line change inside the same commit as the data migration (commit #2 in the walk below). No flow-assertion impact — there are no 1040 flow assertions yet.

### CTC compute deferred

Dependent model lands but `compute.py` does **not** wire CTC/ACTC this session. The 1040 is still the "rough draft skeleton" per MEMORY.md (no credits, no AMT yet). Dependents persist to the DB and appear in the UI; the actual credit calculation comes in a future session. The `qualifies_ctc` / `qualifies_odc` flags surface via the serializer so they're ready when compute catches up.

## Commit walk

Each commit is independently shippable. Push to `origin/main` per DECISIONS.md.

| # | Commit | Touches |
|---|---|---|
| 1 | `feat(1040): Dependent model + CRUD + DependentsSection UI` | New model, migration 0035, serializer, viewset, URLs, FormEditor `DependentsSection`, `INDIVIDUAL_TABS` tab insert. ~10 tests (CRUD + CTC/ODC compute + override behavior). |
| 2 | `feat(1040): expand InterestIncome to full 1099-INT box surface` | Migration 0036 (rename `amount`→`interest_income`, add `tax_exempt_interest`, drop `is_tax_exempt`, add payer EIN/address snapshot + Boxes 2–17), data migration to split existing rows, serializer + viewset expansion, card-per-1099-INT UI rewrite, `aggregate_1040_income()` line 2a/2b split. ~8 tests. |
| 3 | `feat(1040): expand W2Income flat fields (boxes 7-11 + 13 + 18-20)` | Migration 0037. Surface existing boxes 3–6 in UI plus new fields. Add the "less-common" collapsed row. ~6 tests. |
| 4 | `feat(1040): W2Box12Entry + W2Box14Entry models + nested endpoints + UI` | Migration 0038. Two nested viewsets under W-2. UI add/remove lists per W-2 card. ~8 tests. |
| 5 | `feat(1040): surface standard_deduction_override in Taxpayer Info` | Pure UI — single input added to `TaxpayerInfoSection`. ~1 test (or skip — trivial). |
| 6 | `chore(memory): update STATUS.md + MEMORY.md after 1040 entry surface session` | Memory files only. No code. |

## Testing

Each commit ships its own test file under `server/tests/`:

- `test_dependents.py` — CRUD, CTC/ODC default compute from DOB, override flips, ordering, firm scoping.
- `test_interest_income_expansion.py` — data migration splits rows correctly (rows with `is_tax_exempt=True` → `tax_exempt_interest`; others → `interest_income`), serializer round-trip with all 17 boxes, `aggregate_1040_income()` lines 2a/2b correct.
- `test_w2_expansion.py` — new fields persist, defaults sensible (null vs 0).
- `test_w2_box_entries.py` — Box 12/14 nested CRUD, Box 12 code validation (only IRS-listed codes accepted), over-4 entries allowed but flagged.

**Not running the full suite** per DECISIONS.md "Testing" rule. Fast tests only: `poetry run pytest -m "not db" --ignore=tests/test_acroform_filler.py` plus the new test files.

**Flow-assertion gate is not triggered** — none of this work touches `compute.py` aggregate functions referenced by the gate (`aggregate_1040_income` isn't covered by the 1120-S flow assertions, and there are no 1040 flow assertions yet), `renderer.py`, `k1_allocator.py`, `depreciation_engine.py`, or MACRS tables.

## Risks / known soft spots

1. **InterestIncome data migration is irreversible-in-practice.** Forward is clean. Reverse can collapse both `interest_income` and `tax_exempt_interest` back into `amount` + `is_tax_exempt`, but if a row has both fields non-zero, the reverse loses information. Acceptable: forward migration is the only direction we'll actually run, and reverse is just for migration sanity tests.
2. **Box 12 has no hard cap, only a soft warning.** A preparer could enter 10 codes. Real W-2s top out at 4. The warning is enough for now; future tightening can wait for evidence anyone actually exceeds 4.
3. **Locality is a single set of fields, not repeating.** If a real client ever has a W-2 with two localities, the preparer will have to combine or pick one. We add fields only when evidence shows the need.
4. **Yellow autofill markers stay session-scoped.** Inherited gap from Session G — fixing it would require a per-field metadata column on `W2Income`/`InterestIncome`/`Dependent`, which is its own design decision.

## References

- `STATUS.md` (project root) — current state at session start
- `MEMORY.md` (project root) — Session G EIN/W-2 autofill context, broader project state
- `DECISIONS.md` (project root) — Tech-stack lock, coding standards (no full test suite, no third-party grid library, color system, push-with-commit)
- `CLAUDE.md` (project root) — Project rules (color system, RLS, no PII)
- `server/apps/returns/models.py` — Existing `Taxpayer`, `W2Income`, `InterestIncome` model definitions
- `client/src/renderer/pages/FormEditor.tsx` — `INDIVIDUAL_TABS`, `TaxpayerInfoSection`, `W2IncomeSection`, `InterestIncomeSection`
- `server/apps/employers/learning.py` — Session G learning loop (unaffected by this work)
