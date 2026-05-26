# TTS Tax App — Status

## Last updated
2026-05-20

## Currently in progress
- Nothing in progress. Session H landed on main 2026-05-20.

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
1. **1040 — CTC/ACTC compute wiring.** Dependents model + UI persist `qualifies_ctc` / `qualifies_odc` flags via serializer, but `compute.py` does not yet calculate Line 19 (CTC) or Line 28 (ACTC). Add formulas to `FORMULAS_1040` and the bracket-aware reduction at higher AGI.
2. **Cut B — preparer-side document viewer.** A read-only pane that lists W-2 PDFs / 1099 PDFs / source documents the client uploaded, indexed by Entity. Pulls from the `documents` app (Session C). The "view" side of the upload flow that's already wired.
3. **Cut B — PDF preview pane on the W-2 form.** Side-by-side: the W-2 entry card on the left, the source W-2 PDF (uploaded via the documents app) on the right. Lets preparers cross-reference while typing without alt-tabbing. Probably embeds via the same `<embed>`-based PDF viewer the Forms tab already uses (per MEMORY.md "Forms tab: Browser native PDF iframe").
4. **Lacerte parser targeted fixes** (~1–2 hours). Cleanup, not blocking. Two bounded edits to `lacerte_clientlist_parser.py`:
   - Read `LEFT_COLUMNS["sp_first"]` and `["sp_last"]` as fallback when `_parse_name_lnf` returns empty spouse parts.
   - When right-page state OR zip are empty but street/city are populated, scan one y-bucket below for the missing values.
5. **Documents app — Supabase Storage bucket + S3 keys** — backend ships with conditional STORAGES. To go live, create the `tax-documents` bucket in Supabase and add `SUPABASE_S3_ACCESS_KEY` / `SUPABASE_S3_SECRET_KEY` / `SUPABASE_URL` to the Render `.env`. Until those are set, uploads land on the local filesystem (dev only).
6. **Auto-save rendered returns to client folders** — every PDF render should drop a copy in `tax-documents/<firm>/<entity>/<year>/`. Hook lives in `renderer.render_complete_return()`.
7. **Partnership importer test coverage** — TODO from Session C. Needs synthetic xlsx fixture + extraction of the row-parser into a function.
8. **Test-DB strategy decision** — `config.settings.test` currently creates/drops `test_postgres` against the shared prod Supabase project. The harmless teardown warning in every run, plus the pooler-stickiness this session hit, both point to "fix this soon." Three options documented in `config/settings/test.py` docstring.
9. **N+1 cleanup on retrieve serializer.** Pre-existing — `w2_incomes` and `interest_incomes` are not in the `prefetch_related` list on `TaxReturnViewSet.get_queryset()` retrieve branch. One-line fix; final review flagged it but it pre-dated this branch and wasn't blocking.

## Known issues / blockers

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
