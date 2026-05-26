## 1040 Test Return Fixtures

These JSON files describe full 1040 input scenarios and the tax-line
values they should produce. They drive the verification harness Phase 1
(see DECISIONS.md 2026-05-26 entry and STATUS.md "1040 verification
gap").

### Purpose
For each fixture, future tests will:

1. Load the JSON.
2. Create a TaxReturn + Taxpayer + Dependents + W-2s + 1099-INTs from the
   `input` section.
3. Run `aggregate_1040_income()` then `compute_return()`.
4. Assert every key in `expected` matches the FormFieldValue at that
   line number.
5. Render the 1040 PDF and use
   `apps.returns.verification.assert_value_at_pdf_location()` to confirm
   each expected value lands at the right spot on the page.

Step 4 catches compute regressions. Step 5 catches render regressions.

### Naming convention
`{scenario}_{filing_status}.json` where scenario is a short slug. Use
synthetic names and fake SSNs (xxx-xx-xxxx style) per CLAUDE.md
no-PII rule.

### Schema (top-level keys)
- `description` — one-line human summary
- `input` — Taxpayer (incl. address, filing status, DOB), `spouse` (if
  MFJ), `dependents[]`, `w2_incomes[]`, `interest_incomes[]`
- `expected` — tax-line values keyed by 1040 line number as string
  (e.g., `"1a"`, `"11"`, `"19"`, `"25b"`)

### Current fixtures
- `simple_w2_only.json` — single filer, one W-2, standard deduction,
  no dependents
- `family_with_kids.json` — MFJ, 2 kids under 17, 2 W-2s, itemized
  deduction override
- `retiree_1099s.json` — single, multiple 1099-INT/DIV/R, no W-2

These are intentionally diverse to exercise the compute paths Session H
left open: CTC (`family_with_kids`), 1099-INT Box 4 withholding
(`retiree_1099s`), standard-deduction override (`family_with_kids`).

### What's missing today
- No 1099-DIV or 1099-R models exist yet — the retiree fixture lists
  them in the `input` block so the test author knows the intent, but
  loaders should skip what the models don't yet support and the
  `expected` block only covers what's compute-wired today.
- 1040 has no Rule Studio spec, so `expected` values were derived
  manually from IRS 2025 1040 instructions + Rev. Proc. 2024-40
  brackets. Re-derive against the spec once Ken authors one.
