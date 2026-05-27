"""
End-to-end Schedule 8812 (CTC + ACTC + ODC) test scenarios.

Translates the 18 test scenarios in
`exports/session14/SCH_8812_TY2025_spec.json` -> `tests[]`
into pytest cases. For each scenario:

1. Build the minimal DB graph (Firm, Client, Entity, TaxYear, 1040
   TaxReturn, Taxpayer, N qualifying-child Dependents, N other-dependent
   Dependents, an optional W-2 sized to hit `earned_income_for_actc`).
2. Set FormFieldValue rows for Form 1040 Line 11 (AGI) and Line 16
   (tax_before_ctc — Line 18 = Line 16 + Line 17 with Line 17 default 0).
3. Set the Taxpayer placeholder fields directly (eitc_claimed,
   deductible_se_tax_half, se_tax_total, files_form_2555,
   form_2555_excluded_amount, etc).
4. Call `compute_sch_8812(tax_return)` directly (skip compute_return so
   the bracket-derived Line 16 doesn't overwrite what we set).
5. Compare each `expected_outputs` line — keys without prefix are
   SCH_8812 lines; keys prefixed with `1040.` map to the 1040 form.

Notes on what's NOT asserted:
- `D####_fires` — diagnostic firing tests need the diagnostics framework
  (not built for 1040 yet). Documented in the spec note; tracked as a
  follow-up.
- `actc_*`, `return_ssn_eligible_for_ctc_actc`, etc. — internal
  classification flags that aren't persisted. Their effect is verified
  indirectly via the line values.
- `TS_WSB_TBD` — Worksheet B is deferred per spec + Ken's direction.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth.models import User

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.compute_8812 import compute_sch_8812
from apps.returns.models import (
    Dependent,
    FormDefinition,
    FormFieldValue,
    FormLine,
    Taxpayer,
    TaxReturn,
    W2Income,
)

SPEC_PATH = Path(__file__).parent.parent / "specs"

# Lookup from the canonical Session 14 export. We point at the in-repo
# specs/ folder since that's the source of truth the implementation
# follows. (server/specs/8812_spec.json doesn't exist yet — we read the
# scenarios from a check-in copy we'll add as part of this commit.)
_SCH8812_EXPORT = (
    Path("D:/dev/sherpa-tax-rule-studio/exports/session14/SCH_8812_TY2025_spec.json")
)


def _load_scenarios() -> list[dict]:
    with open(_SCH8812_EXPORT) as f:
        data = json.load(f)
    return list(data["tests"])


# Skip TS_WSB_TBD (Worksheet B deferred per spec note + Ken's direction).
_SCENARIOS = [
    t for t in _load_scenarios() if not t["inputs"].get("_deferred")
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def seeded_forms(django_db_setup, django_db_blocker):
    """Ensure SCH_8812 + 1040 form definitions exist for TY 2025."""
    from django.core.management import call_command

    with django_db_blocker.unblock():
        call_command("seed_1040", "--year", "2025")
        call_command("seed_sch_8812", "--year", "2025")


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Firm SCH 8812")


@pytest.fixture
def user(firm):
    u = User.objects.create_user(username="sch8812_preparer", password="x")
    FirmMembership.objects.create(user=u, firm=firm, role=Role.PREPARER)
    return u


@pytest.fixture
def form_1040(seeded_forms):
    return FormDefinition.objects.get(code="1040", tax_year_applicable=2025)


@pytest.fixture
def form_8812(seeded_forms):
    return FormDefinition.objects.get(code="SCH_8812", tax_year_applicable=2025)


# ---------------------------------------------------------------------------
# Helpers — translate abstract scenario inputs into DB rows
# ---------------------------------------------------------------------------

def _qc_dep(tax_return, idx):
    """Build a Dependent that classifies as a CTC qualifying child."""
    return Dependent.objects.create(
        tax_return=tax_return,
        first_name=f"QC{idx}",
        relationship="child",
        date_of_birth=date(2018, 1, 1),  # age 7 in 2025
        months_resided_with_taxpayer=12,
        provided_over_half_own_support=False,
        filed_joint_return=False,
        citizenship_status="us_citizen",
        tin_type="valid_ssn",
    )


def _odc_dep(tax_return, idx):
    """Build a Dependent that classifies as ODC (qualifying relative)."""
    return Dependent.objects.create(
        tax_return=tax_return,
        first_name=f"ODC{idx}",
        relationship="child",
        date_of_birth=date(2018, 1, 1),  # young enough to be a child...
        months_resided_with_taxpayer=12,
        provided_over_half_own_support=False,
        filed_joint_return=False,
        citizenship_status="us_citizen",
        tin_type="itin",  # ...but ITIN-only, so falls back to ODC
    )


def _build_scenario(firm, user, form_1040, scenario):
    """Construct the full DB graph for one scenario. Returns the TaxReturn."""
    inputs = scenario["inputs"]

    cl = Client.objects.create(firm=firm, name=f"Client {scenario['scenario_name']}"[:255])
    ent = Entity.objects.create(
        client=cl,
        name="Sample Filer",
        entity_type=EntityType.INDIVIDUAL,
    )
    ty = TaxYear.objects.create(entity=ent, year=2025)
    tr = TaxReturn.objects.create(
        tax_year=ty,
        form_definition=form_1040,
        created_by=user,
    )

    # Translate filing_status spelling — spec uses "MFJ"/"Single"/"HOH"/"MFS".
    fs_map = {"MFJ": "mfj", "Single": "single", "HOH": "hoh", "MFS": "mfs"}
    filing_status = fs_map.get(inputs["filing_status"], inputs["filing_status"].lower())

    tp = Taxpayer.objects.create(
        tax_return=tr,
        filing_status=filing_status,
        first_name="Sample",
        last_name="Filer",
        taxpayer_has_valid_ssn=inputs.get("taxpayer_has_valid_ssn", True),
        spouse_has_valid_ssn=inputs.get("spouse_has_valid_ssn", True),
        files_form_2555=inputs.get("files_form_2555", False),
        form_2555_excluded_amount=Decimal(str(inputs.get("form_2555_excluded_amount", 0))),
        form_4563_excluded_income=Decimal(str(inputs.get("form_4563_excluded_income", 0))),
        puerto_rico_excluded_income=Decimal(str(inputs.get("puerto_rico_excluded_income", 0))),
        nontaxable_combat_pay=Decimal(str(inputs.get("nontaxable_combat_pay", 0))),
        deductible_se_tax_half=Decimal(str(inputs.get("deductible_se_tax_half", 0))),
        se_tax_total=Decimal(str(inputs.get("se_tax_total", 0))),
        eitc_claimed=Decimal(str(inputs.get("eitc_claimed", 0))),
        excess_ss_rrta_withheld=Decimal(str(inputs.get("excess_ss_rrta_withheld", 0))),
        additional_medicare_tax_amount=Decimal(str(inputs.get("additional_medicare_tax_amount", 0))),
        unreported_ss_medicare_tax=Decimal(str(inputs.get("unreported_ss_medicare_tax", 0))),
        other_employment_taxes=Decimal(str(inputs.get("other_employment_taxes", 0))),
        schedule_3_pre_ctc_credits_total=Decimal(str(inputs.get("schedule_3_pre_ctc_credits_total", 0))),
    )

    # Dependents
    for i in range(inputs.get("count_qualifying_children", 0)):
        _qc_dep(tr, i)
    for i in range(inputs.get("count_other_dependents", 0)):
        _odc_dep(tr, i)

    # W-2 sized so the simplified earned-income calc equals
    # inputs["earned_income_for_actc"]:
    #   earned = wages + (deductible_se_tax_half * 2) + nontaxable_combat_pay
    earned = Decimal(str(inputs.get("earned_income_for_actc", 0)))
    se_proxy = (tp.deductible_se_tax_half or Decimal("0")) * Decimal("2")
    combat = tp.nontaxable_combat_pay or Decimal("0")
    wage_amount = earned - se_proxy - combat
    if wage_amount < 0:
        wage_amount = Decimal("0")

    if earned > 0 or "ss_medicare_taxes_withheld" in inputs:
        ss_med = Decimal(str(inputs.get("ss_medicare_taxes_withheld", 0)))
        W2Income.objects.create(
            tax_return=tr,
            employer_name="Test Employer",
            employer_ein="00-0000000",
            wages=wage_amount,
            federal_tax_withheld=Decimal("0"),
            social_security_tax=ss_med,  # all in box 4 for simplicity
            medicare_tax=Decimal("0"),
        )

    # Backfill all 1040 FormFieldValue rows so we can set Line 11 + Line 16.
    lines_1040 = FormLine.objects.filter(section__form=form_1040)
    FormFieldValue.objects.bulk_create(
        [FormFieldValue(tax_return=tr, form_line=ln, value="") for ln in lines_1040]
    )

    # Set 1040 Line 11 (AGI) + Line 16 (tax). The compute_8812 module
    # reads Line 18, but Line 18 is computed = Line 16 + Line 17, and
    # Line 17 defaults to "" (= 0). We need a quick formula pass to
    # populate Line 18 from Line 16. Simplest: set Line 18 directly too.
    agi = Decimal(str(inputs["agi_line_11"]))
    tax_before = Decimal(str(inputs["tax_before_ctc"]))

    line_map = {
        fv.form_line.line_number: fv
        for fv in FormFieldValue.objects.filter(tax_return=tr).select_related("form_line")
    }
    line_map["11"].value = str(agi)
    line_map["11"].save(update_fields=["value"])
    line_map["16"].value = str(tax_before)
    line_map["16"].save(update_fields=["value"])
    line_map["18"].value = str(tax_before)
    line_map["18"].save(update_fields=["value"])

    return tr


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def _is_assertable_key(key: str) -> bool:
    """Filter out diagnostic + classification-flag keys we can't assert on."""
    if key.endswith("_fires"):
        return False
    if key in (
        "return_ssn_eligible_for_ctc_actc",
        "actc_eligible",
        "actc_part_iib_triggered",
        "ODC",  # used in TS10 as a meta-flag, not a line value
    ):
        return False
    return True


def _get_line_value(tax_return, key: str) -> Decimal:
    """Look up the FormFieldValue for the given key.

    Keys without prefix are SCH_8812 lines (L_3, L_8, etc).
    Keys with `1040.` prefix are Form 1040 lines.
    """
    if key.startswith("1040."):
        form_code = "1040"
        line_no = key.split(".", 1)[1].replace("L_", "")
    else:
        form_code = "SCH_8812"
        line_no = key  # already shaped as L_3, L_8, etc.

    fv = FormFieldValue.objects.filter(
        tax_return=tax_return,
        form_line__line_number=line_no,
        form_line__section__form__code=form_code,
    ).first()
    if fv is None:
        raise AssertionError(f"FormFieldValue not found: {form_code}.{line_no}")
    if not fv.value:
        return Decimal("0")
    return Decimal(fv.value)


# ---------------------------------------------------------------------------
# The parametrized scenario test
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize(
    "scenario",
    _SCENARIOS,
    ids=lambda s: s["scenario_name"].split(" — ")[0],
)
def test_sch_8812_scenario(scenario, firm, user, form_1040, form_8812):
    """Run a single Schedule 8812 spec scenario end-to-end."""
    tr = _build_scenario(firm, user, form_1040, scenario)

    updates = compute_sch_8812(tr)
    assert updates >= 0  # sanity — compute ran without raising

    expected = scenario["expected_outputs"]
    mismatches: list[str] = []
    for key, raw_expected in expected.items():
        if not _is_assertable_key(key):
            continue
        expected_val = Decimal(str(raw_expected))
        try:
            actual = _get_line_value(tr, key)
        except AssertionError as exc:
            mismatches.append(str(exc))
            continue
        if actual != expected_val:
            mismatches.append(
                f"{key}: expected {expected_val}, got {actual}"
            )

    if mismatches:
        joined = "\n  - ".join(mismatches)
        pytest.fail(
            f"{scenario['scenario_name']}\n  - {joined}"
        )


def test_scenarios_loaded():
    """Sanity — 17 active scenarios + 1 deferred (TS_WSB_TBD)."""
    all_t = _load_scenarios()
    assert len(all_t) == 18, f"expected 18 scenarios, got {len(all_t)}"
    deferred = [t for t in all_t if t["inputs"].get("_deferred")]
    assert len(deferred) == 1, f"expected 1 deferred scenario, got {len(deferred)}"
    assert len(_SCENARIOS) == 17, f"expected 17 active scenarios, got {len(_SCENARIOS)}"
