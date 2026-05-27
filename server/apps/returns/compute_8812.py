"""
Schedule 8812 (CTC + ACTC + ODC) compute module — TY 2025.

Implements all 30 rules from SCH_8812_TY2025 Rule Studio spec (Session 14).

Architecture
------------
- Schedule 8812 lines live in their own FormDefinition (`code="SCH_8812"`),
  but their values are stored on the PARENT 1040 TaxReturn — i.e., the
  same `FormFieldValue.tax_return` as the 1040 lines, just with
  `FormFieldValue.form_line` pointing at an SCH_8812 `FormLine`. This
  avoids a parent_return FK on TaxReturn while preserving the spec's
  cross-form semantics (FormLine.section.form is still distinct).
- All 30 rules are implemented in a single `compute_sch_8812(tax_return)`
  entry point. It is called from `compute_return()` for `form_code=="1040"`
  AFTER `_compute_1040_tax()` has set Line 16, and BEFORE the downstream
  1040 formula re-evaluation that propagates Lines 19/28 to 21/22/24/33.

Deferrals (per Ken's Session 1 scope direction)
-----------------------------------------------
- Earned Income Worksheet: uses the SIMPLIFIED path (W-2 wages +
  nontaxable combat pay) instead of full Worksheet B. SE earnings are
  pulled from `Taxpayer.deductible_se_tax_half * 2` if non-zero (rough
  approximation pending Schedule SE).
- Worksheet B (other credits competing for the Credit Limit Worksheet A
  cap) is fully deferred — `claims_credits_requiring_worksheet_b`
  diagnostic remains in seed; compute uses the standard L_13 formula.
- Schedules 1/2/3, Form 8959, Schedule SE, EITC: preparer-entered
  placeholder totals on Taxpayer (default 0).
"""
from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import Iterable

ZERO = Decimal("0")
QC_AMOUNT = Decimal("2200")      # OBBBA §70104 — TY 2025+
ODC_AMOUNT = Decimal("500")      # IRC §24(h)(4)
PHASEOUT_RATE = Decimal("0.05")  # IRC §24(b)(2)
PHASEOUT_THRESHOLD_MFJ = Decimal("400000")
PHASEOUT_THRESHOLD_OTHER = Decimal("200000")
ACTC_PER_CHILD_CAP = Decimal("1700")  # IRS 2025 Sch 8812 Instructions
ACTC_EARNED_INCOME_FLOOR = Decimal("2500")
ACTC_PERCENT = Decimal("0.15")


# ---------------------------------------------------------------------------
# Per-dependent classification — R001 (CTC) + R002 (ODC)
# ---------------------------------------------------------------------------

def _age_at_eoy(dependent, tax_year: int) -> int | None:
    """Age at the end of the tax year (Dec 31). None if no DOB."""
    if not dependent.date_of_birth:
        return None
    return tax_year - dependent.date_of_birth.year


def classify_dependent_ctc(dependent, tax_year: int) -> bool:
    """R001 — CTC qualifying child (7-test classification).

    Honors `ctc_override` if set; otherwise applies the spec formula.
    """
    if dependent.ctc_override is not None:
        return dependent.ctc_override

    age = _age_at_eoy(dependent, tax_year)
    if age is None:
        return False

    return (
        age < 17
        and dependent.relationship not in ("", "other")
        and (dependent.months_resided_with_taxpayer or 0) > 6
        and not dependent.provided_over_half_own_support
        and not dependent.filed_joint_return
        and dependent.citizenship_status in ("us_citizen", "us_national", "us_resident_alien")
        and dependent.tin_type == "valid_ssn"
    )


def classify_dependent_odc(dependent, tax_year: int, qualifies_ctc: bool) -> bool:
    """R002 — Credit for Other Dependents.

    A dependent qualifies for ODC iff they are claimed AND don't already
    qualify for CTC AND meet the citizenship + TIN bars.
    """
    if dependent.odc_override is not None:
        return dependent.odc_override
    if qualifies_ctc:
        return False
    if dependent.citizenship_status not in ("us_citizen", "us_national", "us_resident_alien"):
        return False
    if dependent.tin_type not in ("valid_ssn", "itin", "atin"):
        return False
    return True


# ---------------------------------------------------------------------------
# Helpers for FormFieldValue I/O against SCH_8812 + 1040
# ---------------------------------------------------------------------------

def _to_decimal(raw) -> Decimal:
    if raw is None or raw == "":
        return ZERO
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return ZERO


def _backfill_sch_8812_values(tax_return, form_def):
    """Ensure FormFieldValue rows exist for every SCH_8812 line on this return."""
    from .models import FormFieldValue, FormLine

    existing = set(
        FormFieldValue.objects.filter(
            tax_return=tax_return,
            form_line__section__form=form_def,
        ).values_list("form_line_id", flat=True)
    )
    missing_lines = FormLine.objects.filter(
        section__form=form_def,
    ).exclude(id__in=existing)
    if missing_lines.exists():
        FormFieldValue.objects.bulk_create([
            FormFieldValue(tax_return=tax_return, form_line=ln, value="")
            for ln in missing_lines
        ])


def _earned_income_simplified(tax_return, taxpayer) -> Decimal:
    """Simplified Earned Income for ACTC — W-2 wages + ~SE earnings + combat pay.

    Per Ken's Session 1 direction: skip the full Earned Income
    Worksheet (and Worksheet B). Real Schedule SE not yet modeled.
    `deductible_se_tax_half * 2` is a rough proxy for net SE earnings
    pending the real form. Returns ZERO when nothing is available.
    """
    from .models import W2Income

    wages = sum(
        (w.wages for w in W2Income.objects.filter(tax_return=tax_return)),
        ZERO,
    )
    combat = taxpayer.nontaxable_combat_pay or ZERO
    se_proxy = (taxpayer.deductible_se_tax_half or ZERO) * Decimal("2")
    return wages + se_proxy + combat


def _ss_medicare_withheld(tax_return) -> Decimal:
    """Sum of W-2 Box 4 (social_security_tax) + Box 6 (medicare_tax) across all W-2s.

    Spec fact `ss_medicare_taxes_withheld`. Spec language says "both
    spouses if MFJ" — the W-2 rows on this return cover whichever
    spouse(s) the preparer entered.
    """
    from .models import W2Income

    total = ZERO
    for w in W2Income.objects.filter(tax_return=tax_return):
        total += (w.social_security_tax or ZERO) + (w.medicare_tax or ZERO)
    return total


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_sch_8812(tax_return) -> int:
    """Compute all 30 Schedule 8812 rules + write Lines 19/28 on 1040.

    Returns the number of FormFieldValue rows updated.
    """
    from .models import (
        Dependent,
        FormDefinition,
        FormFieldValue,
        FormLine,
        Taxpayer,
    )

    tax_year = tax_return.tax_year.year

    try:
        form_8812 = FormDefinition.objects.get(
            code="SCH_8812",
            tax_year_applicable=tax_year,
        )
    except FormDefinition.DoesNotExist:
        return 0  # Schedule 8812 not seeded for this year — nothing to do.

    _backfill_sch_8812_values(tax_return, form_8812)

    try:
        taxpayer = tax_return.taxpayer
    except Taxpayer.DoesNotExist:
        return 0  # No Taxpayer record — can't classify; skip.

    # ---- Per-dependent classification (R001, R002, R004, R005) ----
    deps = list(Dependent.objects.filter(tax_return=tax_return))
    classifications: list[tuple[bool, bool]] = []
    qc_count = 0
    odc_count = 0
    for dep in deps:
        is_ctc = classify_dependent_ctc(dep, tax_year)
        is_odc = classify_dependent_odc(dep, tax_year, is_ctc)
        classifications.append((is_ctc, is_odc))
        if is_ctc:
            qc_count += 1
        if is_odc:
            odc_count += 1

    # ---- R003: return-level SSN eligibility ----
    filing_status = (taxpayer.filing_status or "single").lower()
    return_ssn_eligible = (
        bool(taxpayer.taxpayer_has_valid_ssn)
        or (filing_status == "mfj" and bool(taxpayer.spouse_has_valid_ssn))
    )

    # ---- Read 1040 Line 11 (AGI) + Line 18 (tax before CTC) ----
    fv_1040 = {
        fv.form_line.line_number: fv
        for fv in FormFieldValue.objects.filter(
            tax_return=tax_return,
            form_line__section__form__code="1040",
        ).select_related("form_line__section__form")
    }
    agi_line_11 = _to_decimal(fv_1040.get("11").value if fv_1040.get("11") else ZERO)
    tax_before_ctc = _to_decimal(fv_1040.get("18").value if fv_1040.get("18") else ZERO)
    sch_3_pre_ctc = taxpayer.schedule_3_pre_ctc_credits_total or ZERO

    # ---- R006-R013: MAGI + pre-phaseout + threshold + reduction ----
    L_2a = taxpayer.puerto_rico_excluded_income or ZERO
    L_2b = taxpayer.form_2555_excluded_amount or ZERO
    L_2c = taxpayer.form_4563_excluded_income or ZERO
    L_2d = L_2a + L_2b + L_2c
    L_1 = agi_line_11
    L_3 = L_1 + L_2d              # R007 (MAGI)
    L_4 = Decimal(qc_count)        # R004
    L_5 = L_4 * QC_AMOUNT          # R008
    L_6 = Decimal(odc_count)       # R005
    L_7 = L_6 * ODC_AMOUNT         # R009
    L_8 = L_5 + L_7                # R010

    if filing_status == "mfj":
        L_9 = PHASEOUT_THRESHOLD_MFJ
    else:
        L_9 = PHASEOUT_THRESHOLD_OTHER  # R011

    raw_excess = L_3 - L_9
    if raw_excess <= 0:
        L_10 = ZERO
    else:
        # Round UP to next $1,000 — R012 ("any non-zero excess rounds UP").
        L_10 = Decimal(math.ceil(raw_excess / Decimal("1000"))) * Decimal("1000")

    L_11 = (L_10 * PHASEOUT_RATE).quantize(Decimal("0.01"))    # R013
    L_12 = max(ZERO, L_8 - L_11)                                # R014
    L_13 = max(ZERO, tax_before_ctc - sch_3_pre_ctc)            # R015
    L_14 = min(L_12, L_13)                                      # R016
    L_15 = ZERO  # Reserved per spec.

    # ---- R017: ACTC eligibility ----
    actc_eligible = (
        L_12 > 0
        and not bool(taxpayer.files_form_2555)
        and return_ssn_eligible
        and qc_count > 0
    )

    # ---- R018-R020: ACTC standard path ----
    # Spec rule R018 reads "L_16a = ... if actc_eligible else 0", but
    # scenarios disambiguate the conditions:
    #   TS09b (QC=0, no 2555): L_16a=300 ← gating ignores QC count
    #   TS13  (QC=2, 2555=Y) : L_16a=0   ← Form 2555 zeros L_16a
    # The effective gate is `NOT files_form_2555 AND return_ssn_eligible`.
    # Full actc_eligible (which also requires QC > 0) gates L_27 via R029.
    actc_overflow_gate = (
        not bool(taxpayer.files_form_2555) and return_ssn_eligible
    )
    L_16a = max(ZERO, L_12 - L_14) if actc_overflow_gate else ZERO
    L_16b = Decimal(qc_count) * ACTC_PER_CHILD_CAP
    L_17 = min(L_16a, L_16b)

    # ---- R021-R022: Earned-income 15% method ----
    earned_income = _earned_income_simplified(tax_return, taxpayer)
    L_18a = earned_income
    L_18b = taxpayer.nontaxable_combat_pay or ZERO
    L_19 = max(ZERO, earned_income - ACTC_EARNED_INCOME_FLOOR) if actc_eligible else ZERO
    L_20 = (L_19 * ACTC_PERCENT).quantize(Decimal("0.01")) if actc_eligible else ZERO

    # ---- R023: Part II-B trigger ----
    actc_part_iib_triggered = (qc_count >= 3 and L_20 < L_17)

    # ---- R024-R028: Part II-B path ----
    L_21 = _ss_medicare_withheld(tax_return) + (
        (taxpayer.additional_medicare_tax_amount or ZERO) * Decimal("0.5")
    )
    L_22 = (
        (taxpayer.deductible_se_tax_half or ZERO)
        + (taxpayer.se_tax_total or ZERO)
        + (taxpayer.unreported_ss_medicare_tax or ZERO)
        + (taxpayer.other_employment_taxes or ZERO)
    )
    L_23 = L_21 + L_22                                           # R026
    L_24 = (taxpayer.eitc_claimed or ZERO) + (taxpayer.excess_ss_rrta_withheld or ZERO)
    L_25 = max(ZERO, L_23 - L_24)                                # R028 part 1
    L_26 = max(L_20, L_25)                                       # R028 part 2

    # ---- R029: final ACTC ----
    if not actc_eligible:
        L_27 = ZERO
    elif actc_part_iib_triggered:
        L_27 = min(L_17, L_26)
    else:
        L_27 = min(L_17, L_20)

    # ---- R030: taxpayer SSN gate (return-level override) ----
    if not return_ssn_eligible:
        L_14 = ZERO
        L_27 = ZERO

    # ---- Write SCH_8812 form lines ----
    values_to_write = {
        "L_1": L_1, "L_2a": L_2a, "L_2b": L_2b, "L_2c": L_2c, "L_2d": L_2d,
        "L_3": L_3, "L_4": L_4, "L_5": L_5, "L_6": L_6, "L_7": L_7, "L_8": L_8,
        "L_9": L_9, "L_10": L_10, "L_11": L_11, "L_12": L_12, "L_13": L_13,
        "L_14": L_14, "L_15": L_15,
        "L_16a": L_16a, "L_16b": L_16b, "L_17": L_17,
        "L_18a": L_18a, "L_18b": L_18b, "L_19": L_19, "L_20": L_20,
        "L_21": L_21, "L_22": L_22, "L_23": L_23, "L_24": L_24,
        "L_25": L_25, "L_26": L_26, "L_27": L_27,
    }

    fv_8812 = {
        fv.form_line.line_number: fv
        for fv in FormFieldValue.objects.filter(
            tax_return=tax_return,
            form_line__section__form=form_8812,
        ).select_related("form_line")
    }

    updates = 0
    quant = Decimal("0.01")
    for line_number, val in values_to_write.items():
        fv = fv_8812.get(line_number)
        if not fv:
            continue
        if isinstance(val, Decimal):
            new_val = str(val.quantize(quant))
        else:
            new_val = str(val)
        if fv.value != new_val:
            fv.value = new_val
            fv.save(update_fields=["value", "updated_at"])
            updates += 1

    # ---- Cross-form flow: SCH_8812 L_14 → 1040 L_19; L_27 → 1040 L_28 ----
    for line_1040, val in (("19", L_14), ("28", L_27)):
        fv = fv_1040.get(line_1040)
        if not fv:
            continue
        new_val = str(val.quantize(quant))
        if fv.value != new_val:
            fv.value = new_val
            fv.save(update_fields=["value", "updated_at"])
            updates += 1

    return updates


# ---------------------------------------------------------------------------
# Convenience: classification helpers exposed for tests / serializers
# ---------------------------------------------------------------------------

def classify_dependents(tax_return) -> list[tuple[object, bool, bool]]:
    """Return [(dependent, qualifies_ctc, qualifies_odc), ...] for a 1040 return."""
    from .models import Dependent

    tax_year = tax_return.tax_year.year
    results = []
    for dep in Dependent.objects.filter(tax_return=tax_return):
        is_ctc = classify_dependent_ctc(dep, tax_year)
        is_odc = classify_dependent_odc(dep, tax_year, is_ctc)
        results.append((dep, is_ctc, is_odc))
    return results
