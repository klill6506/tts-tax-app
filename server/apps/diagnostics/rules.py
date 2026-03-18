"""
Built-in diagnostic rules.

Each rule function receives a TaxYear instance and returns a list of
finding dicts: [{"severity": "...", "message": "...", "details": {...}}]

An empty list means the check passed.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from apps.clients.models import TaxYear
from apps.imports.models import TrialBalanceUpload, UploadStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_return_values(tax_year: TaxYear) -> tuple:
    """Get the first federal TaxReturn and its line values as a dict.
    Returns (tax_return, values_dict) or (None, {}).
    """
    from apps.returns.models import FormFieldValue, TaxReturn

    tax_return = (
        TaxReturn.objects.filter(tax_year=tax_year, federal_return__isnull=True)
        .select_related("form_definition")
        .first()
    )
    if not tax_return:
        return None, {}

    fvs = (
        FormFieldValue.objects.filter(tax_return=tax_return)
        .select_related("form_line")
    )
    values: dict[str, Decimal] = {}
    for fv in fvs:
        if fv.value:
            try:
                values[fv.form_line.line_number] = Decimal(fv.value)
            except InvalidOperation:
                pass
    return tax_return, values


def _d(values: dict[str, Decimal], line: str) -> Decimal:
    return values.get(line, Decimal("0.00"))


# ---------------------------------------------------------------------------
# Trial Balance Rules (existing)
# ---------------------------------------------------------------------------

def tb_exists_check(tax_year: TaxYear) -> list[dict]:
    """Check that at least one parsed Trial Balance exists."""
    uploads = TrialBalanceUpload.objects.filter(
        tax_year=tax_year, status=UploadStatus.PARSED
    )
    if not uploads.exists():
        return [
            {
                "severity": "error",
                "message": "No parsed Trial Balance found for this tax year.",
                "details": {"tax_year_id": str(tax_year.id), "year": tax_year.year},
            }
        ]
    return []


def tb_balance_check(tax_year: TaxYear) -> list[dict]:
    """Check that total debits equal total credits in the latest TB upload."""
    upload = (
        TrialBalanceUpload.objects.filter(
            tax_year=tax_year, status=UploadStatus.PARSED
        )
        .order_by("-created_at")
        .first()
    )
    if not upload:
        return []  # tb_exists_check will catch this

    rows = upload.rows.all()
    total_debit = sum(r.debit for r in rows)
    total_credit = sum(r.credit for r in rows)

    if total_debit != total_credit:
        diff = total_debit - total_credit
        return [
            {
                "severity": "error",
                "message": (
                    f"Trial Balance is out of balance. "
                    f"Debits: {total_debit:,.0f}, Credits: {total_credit:,.0f}, "
                    f"Difference: {abs(diff):,.0f}"
                ),
                "details": {
                    "upload_id": str(upload.id),
                    "total_debit": str(total_debit),
                    "total_credit": str(total_credit),
                    "difference": str(diff),
                },
            }
        ]
    return []


def tb_zero_rows_check(tax_year: TaxYear) -> list[dict]:
    """Flag TB rows where both debit and credit are zero."""
    upload = (
        TrialBalanceUpload.objects.filter(
            tax_year=tax_year, status=UploadStatus.PARSED
        )
        .order_by("-created_at")
        .first()
    )
    if not upload:
        return []

    zero_rows = upload.rows.filter(debit=Decimal("0"), credit=Decimal("0"))
    findings = []
    for row in zero_rows:
        findings.append(
            {
                "severity": "info",
                "message": (
                    f"Row {row.row_number} ({row.account_number} {row.account_name}) "
                    f"has zero debit and zero credit."
                ),
                "details": {
                    "row_id": str(row.id),
                    "row_number": row.row_number,
                    "account_number": row.account_number,
                },
            }
        )
    return findings


# ---------------------------------------------------------------------------
# Math Diagnostics
# ---------------------------------------------------------------------------

def math_balance_sheet_check(tax_year: TaxYear) -> list[dict]:
    """Check that Balance Sheet total assets = total liabilities + equity."""
    tax_return, values = _get_return_values(tax_year)
    if not tax_return:
        return []

    form_code = tax_return.form_definition.code
    findings = []

    if form_code == "1120-S":
        # BOY: L14a (assets) vs L27a (liabilities + equity)
        assets_boy = _d(values, "L14a")
        liab_boy = _d(values, "L27a")
        if assets_boy and liab_boy and assets_boy != liab_boy:
            diff = assets_boy - liab_boy
            findings.append({
                "severity": "error",
                "message": (
                    f"Balance Sheet (BOY) out of balance. "
                    f"Assets: {assets_boy:,.0f}, Liabilities + Equity: {liab_boy:,.0f}, "
                    f"Difference: {abs(diff):,.0f}"
                ),
                "details": {"period": "boy", "assets": str(assets_boy), "liab_equity": str(liab_boy)},
            })

        # EOY: L14d (assets) vs L27d (liabilities + equity)
        assets_eoy = _d(values, "L14d")
        liab_eoy = _d(values, "L27d")
        if assets_eoy and liab_eoy and assets_eoy != liab_eoy:
            diff = assets_eoy - liab_eoy
            findings.append({
                "severity": "error",
                "message": (
                    f"Balance Sheet (EOY) out of balance. "
                    f"Assets: {assets_eoy:,.0f}, Liabilities + Equity: {liab_eoy:,.0f}, "
                    f"Difference: {abs(diff):,.0f}"
                ),
                "details": {"period": "eoy", "assets": str(assets_eoy), "liab_equity": str(liab_eoy)},
            })

    elif form_code in ("1065", "1120"):
        # Similar check using the correct line numbers for each form
        for suffix, label in [("a", "BOY"), ("d", "EOY")]:
            if form_code == "1065":
                assets = _d(values, f"L14{suffix}")
                liab = _d(values, f"L23{suffix}")
            else:  # 1120
                assets = _d(values, f"L15{suffix}")
                liab = _d(values, f"L28{suffix}")
            if assets and liab and assets != liab:
                diff = assets - liab
                findings.append({
                    "severity": "error",
                    "message": (
                        f"Balance Sheet ({label}) out of balance. "
                        f"Assets: {assets:,.0f}, Liabilities + Equity: {liab:,.0f}, "
                        f"Difference: {abs(diff):,.0f}"
                    ),
                    "details": {"period": label.lower(), "assets": str(assets), "liab_equity": str(liab)},
                })

    return findings


def math_m1_reconciliation_check(tax_year: TaxYear) -> list[dict]:
    """Check that M-1 line 8 reconciles to Schedule K income (1120-S)."""
    tax_return, values = _get_return_values(tax_year)
    if not tax_return:
        return []

    form_code = tax_return.form_definition.code
    if form_code != "1120-S":
        return []

    m1_8 = _d(values, "M1_8")
    k18 = _d(values, "K18")

    # Only check if M-1 has been filled in (at least some data)
    has_m1_data = any(
        _d(values, ln) != 0
        for ln in ("M1_1", "M1_2", "M1_3a", "M1_3b", "M1_5", "M1_6")
    )
    if not has_m1_data:
        return []

    if m1_8 != k18:
        diff = m1_8 - k18
        return [{
            "severity": "warning",
            "message": (
                f"Schedule M-1 does not reconcile. "
                f"M-1 Line 8: {m1_8:,.0f}, Schedule K Line 18: {k18:,.0f}, "
                f"Difference: {abs(diff):,.0f}"
            ),
            "details": {"m1_8": str(m1_8), "k18": str(k18), "difference": str(diff)},
        }]
    return []


def math_m2_check(tax_year: TaxYear) -> list[dict]:
    """Check M-2 ending balance = retained earnings on balance sheet (Schedule L)."""
    tax_return, values = _get_return_values(tax_year)
    if not tax_return:
        return []

    form_code = tax_return.form_definition.code
    if form_code != "1120-S":
        return []

    m2_8 = _d(values, "M2_8a")
    # For 1120-S, retained earnings is typically L24d (Retained earnings EOY)
    retained = _d(values, "L24d")

    # Only check if both have values
    if not m2_8 and not retained:
        return []

    if m2_8 != retained:
        diff = m2_8 - retained
        return [{
            "severity": "warning",
            "message": (
                f"Schedule M-2 ending balance ({m2_8:,.0f}) does not match "
                f"Balance Sheet retained earnings L24d ({retained:,.0f}). "
                f"Difference: {abs(diff):,.0f}"
            ),
            "details": {"m2_8": str(m2_8), "l24d": str(retained), "difference": str(diff)},
        }]
    return []


def math_page1_income_check(tax_year: TaxYear) -> list[dict]:
    """Check page 1 income/deduction math adds up correctly."""
    tax_return, values = _get_return_values(tax_year)
    if not tax_return:
        return []

    form_code = tax_return.form_definition.code
    findings = []

    if form_code == "1120-S":
        # Line 6 should = lines 3 + 4 + 5
        expected_6 = _d(values, "3") + _d(values, "4") + _d(values, "5")
        actual_6 = _d(values, "6")
        if expected_6 and actual_6 != expected_6:
            findings.append({
                "severity": "error",
                "message": (
                    f"Page 1 Line 6 ({actual_6:,.0f}) does not equal "
                    f"Lines 3+4+5 ({expected_6:,.0f})."
                ),
                "details": {"line": "6", "expected": str(expected_6), "actual": str(actual_6)},
            })

        # Line 21 should = line 6 - line 20
        expected_21 = _d(values, "6") - _d(values, "20")
        actual_21 = _d(values, "21")
        if _d(values, "6") and actual_21 != expected_21:
            findings.append({
                "severity": "error",
                "message": (
                    f"Page 1 Line 21 ({actual_21:,.0f}) does not equal "
                    f"Line 6 minus Line 20 ({expected_21:,.0f})."
                ),
                "details": {"line": "21", "expected": str(expected_21), "actual": str(actual_21)},
            })

    return findings


# ---------------------------------------------------------------------------
# Missing Info Diagnostics
# ---------------------------------------------------------------------------

def missing_ein_check(tax_year: TaxYear) -> list[dict]:
    """Check that the entity has an EIN."""
    entity = tax_year.entity
    if not entity.ein or not entity.ein.strip():
        return [{
            "severity": "error",
            "message": f"Entity '{entity.name}' is missing an EIN.",
            "details": {"entity_id": str(entity.id)},
        }]
    return []


def missing_address_check(tax_year: TaxYear) -> list[dict]:
    """Check that the entity has a complete address."""
    entity = tax_year.entity
    findings = []
    missing = []
    if not entity.address_line1:
        missing.append("street address")
    if not entity.city:
        missing.append("city")
    if not entity.state:
        missing.append("state")
    if not entity.zip_code:
        missing.append("ZIP code")
    if missing:
        findings.append({
            "severity": "error",
            "message": f"Entity '{entity.name}' is missing: {', '.join(missing)}.",
            "details": {"entity_id": str(entity.id), "missing_fields": missing},
        })
    return findings


def missing_shareholders_check(tax_year: TaxYear) -> list[dict]:
    """Check that at least one shareholder/partner exists (for S-corp/partnership)."""
    from apps.returns.models import Shareholder, TaxReturn

    tax_return = (
        TaxReturn.objects.filter(tax_year=tax_year, federal_return__isnull=True)
        .select_related("form_definition")
        .first()
    )
    if not tax_return:
        return []

    form_code = tax_return.form_definition.code
    if form_code not in ("1120-S", "1065"):
        return []

    label = "shareholders" if form_code == "1120-S" else "partners"
    count = Shareholder.objects.filter(tax_return=tax_return, is_active=True).count()
    if count == 0:
        return [{
            "severity": "error",
            "message": f"No {label} entered. At least one is required for Schedule K-1.",
            "details": {"form_code": form_code},
        }]
    return []


def missing_officers_check(tax_year: TaxYear) -> list[dict]:
    """Check that at least one officer is entered (for S-corp/C-corp)."""
    from apps.returns.models import Officer, TaxReturn

    tax_return = (
        TaxReturn.objects.filter(tax_year=tax_year, federal_return__isnull=True)
        .select_related("form_definition")
        .first()
    )
    if not tax_return:
        return []

    form_code = tax_return.form_definition.code
    if form_code not in ("1120-S", "1120"):
        return []

    count = Officer.objects.filter(tax_return=tax_return).count()
    if count == 0:
        return [{
            "severity": "warning",
            "message": "No officers entered. Form 1125-E requires officer compensation details.",
            "details": {"form_code": form_code},
        }]
    return []


def missing_income_check(tax_year: TaxYear) -> list[dict]:
    """Check that at least some income or deduction has been entered."""
    tax_return, values = _get_return_values(tax_year)
    if not tax_return:
        return []

    form_code = tax_return.form_definition.code
    # Check key income/deduction lines based on form type
    income_lines = {
        "1120-S": ["1a", "1c", "2", "3", "4", "5", "6"],
        "1065": ["1a", "1c", "3", "4", "5", "6", "7", "8"],
        "1120": ["1a", "1c", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
    }
    lines_to_check = income_lines.get(form_code, [])
    has_income = any(_d(values, ln) != 0 for ln in lines_to_check)

    if not has_income:
        return [{
            "severity": "warning",
            "message": "No income has been entered on Page 1. Is this return started?",
            "details": {"form_code": form_code},
        }]
    return []


def missing_dates_check(tax_year: TaxYear) -> list[dict]:
    """Check that tax year start/end dates are set."""
    from apps.returns.models import TaxReturn

    tax_return = (
        TaxReturn.objects.filter(tax_year=tax_year, federal_return__isnull=True)
        .first()
    )
    if not tax_return:
        return []

    findings = []
    if not tax_return.tax_year_start:
        findings.append({
            "severity": "warning",
            "message": "Tax year start date is not set.",
            "details": {},
        })
    if not tax_return.tax_year_end:
        findings.append({
            "severity": "warning",
            "message": "Tax year end date is not set.",
            "details": {},
        })
    return findings


def missing_preparer_check(tax_year: TaxYear) -> list[dict]:
    """Check that a signing preparer is assigned."""
    from apps.returns.models import TaxReturn

    tax_return = (
        TaxReturn.objects.filter(tax_year=tax_year, federal_return__isnull=True)
        .first()
    )
    if not tax_return:
        return []

    if not tax_return.preparer_id:
        return [{
            "severity": "warning",
            "message": "No signing preparer assigned to this return.",
            "details": {},
        }]
    return []


def shareholder_ownership_check(tax_year: TaxYear) -> list[dict]:
    """Check that shareholder ownership percentages sum to 100%."""
    from apps.returns.models import Shareholder, TaxReturn

    tax_return = (
        TaxReturn.objects.filter(tax_year=tax_year, federal_return__isnull=True)
        .select_related("form_definition")
        .first()
    )
    if not tax_return:
        return []

    form_code = tax_return.form_definition.code
    if form_code not in ("1120-S", "1065"):
        return []

    shareholders = Shareholder.objects.filter(tax_return=tax_return, is_active=True)
    if not shareholders.exists():
        return []  # missing_shareholders_check handles this

    total_pct = sum(
        Decimal(s.ownership_percentage or "0") for s in shareholders
    )
    label = "Shareholder" if form_code == "1120-S" else "Partner"

    if total_pct != Decimal("100"):
        return [{
            "severity": "error",
            "message": (
                f"{label} ownership percentages sum to {total_pct}%, not 100%."
            ),
            "details": {"total_percentage": str(total_pct)},
        }]
    return []


def shareholder_ssn_check(tax_year: TaxYear) -> list[dict]:
    """Check that all shareholders/partners have SSNs."""
    from apps.returns.models import Shareholder, TaxReturn

    tax_return = (
        TaxReturn.objects.filter(tax_year=tax_year, federal_return__isnull=True)
        .select_related("form_definition")
        .first()
    )
    if not tax_return:
        return []

    form_code = tax_return.form_definition.code
    if form_code not in ("1120-S", "1065"):
        return []

    shareholders = Shareholder.objects.filter(tax_return=tax_return, is_active=True)
    label = "Shareholder" if form_code == "1120-S" else "Partner"
    findings = []

    for s in shareholders:
        if not s.ssn or not s.ssn.strip():
            findings.append({
                "severity": "error",
                "message": f"{label} '{s.name}' is missing an SSN/EIN (required for K-1).",
                "details": {"shareholder_id": str(s.id), "name": s.name},
            })
    return findings


# ---------------------------------------------------------------------------
# Form 4797 — Disposition Diagnostics (D001-D005 from Rule Studio spec)
# ---------------------------------------------------------------------------

def _get_disposed_assets(tax_year: TaxYear):
    """Get disposed DepreciationAssets for the first federal return."""
    from apps.returns.models import DepreciationAsset, TaxReturn

    tax_return = (
        TaxReturn.objects.filter(tax_year=tax_year, federal_return__isnull=True)
        .first()
    )
    if not tax_return:
        return []

    return list(
        DepreciationAsset.objects.filter(
            tax_return=tax_return,
            date_sold__isnull=False,
        )
    )


def f4797_missing_holding_period(tax_year: TaxYear) -> list[dict]:
    """D001: Missing holding period — dates required for Part routing."""
    assets = _get_disposed_assets(tax_year)
    findings = []
    for a in assets:
        if not a.date_acquired or not a.date_sold:
            findings.append({
                "severity": "error",
                "message": (
                    f"Disposed asset '{a.description}' is missing "
                    f"{'date acquired' if not a.date_acquired else 'date sold'}. "
                    "Holding period is required to determine correct Part routing."
                ),
                "details": {"asset_id": str(a.id), "description": a.description},
            })
    return findings


def f4797_zero_depreciation(tax_year: TaxYear) -> list[dict]:
    """D002: Depreciation not entered for depreciable property."""
    assets = _get_disposed_assets(tax_year)
    findings = []
    _depreciable_groups = {
        "Machinery and Equipment", "Furniture and Fixtures",
        "Vehicles", "Buildings", "Improvements",
        "Intangibles/Amortization",
    }
    for a in assets:
        if a.group_label not in _depreciable_groups:
            continue
        total_depr = (
            a.prior_depreciation + a.current_depreciation
            + a.bonus_amount + a.sec_179_elected
        )
        if total_depr == 0:
            findings.append({
                "severity": "warning",
                "message": (
                    f"Disposed asset '{a.description}' ({a.group_label}) has zero depreciation. "
                    "Verify this is correct — if depreciation was allowed, it must be reported "
                    "even if not claimed (depreciation 'allowable')."
                ),
                "details": {"asset_id": str(a.id), "group_label": a.group_label},
            })
    return findings


def f4797_gain_no_recapture(tax_year: TaxYear) -> list[dict]:
    """D003: Gain on §1245 property with no depreciation to recapture."""
    assets = _get_disposed_assets(tax_year)
    findings = []
    # §1245 groups = personal property (not buildings/improvements/land)
    _1245_groups = {
        "Machinery and Equipment", "Furniture and Fixtures",
        "Vehicles", "Intangibles/Amortization",
    }
    for a in assets:
        if a.group_label not in _1245_groups:
            continue
        total_depr = (
            a.prior_depreciation + a.current_depreciation
            + a.bonus_amount + a.sec_179_elected
        )
        gain = a.gain_loss_on_sale or Decimal("0")
        if gain > 0 and total_depr == 0:
            findings.append({
                "severity": "warning",
                "message": (
                    f"Disposed asset '{a.description}' has gain but no depreciation to recapture. "
                    "Verify basis and depreciation."
                ),
                "details": {"asset_id": str(a.id), "gain": str(gain)},
            })
    return findings


def f4797_zero_sale_price(tax_year: TaxYear) -> list[dict]:
    """D004: Sale price is zero — may be abandonment or casualty."""
    assets = _get_disposed_assets(tax_year)
    findings = []
    for a in assets:
        if not a.sales_price or a.sales_price == 0:
            findings.append({
                "severity": "warning",
                "message": (
                    f"Disposed asset '{a.description}' has a zero sale price. "
                    "If this was an abandonment or casualty, verify the correct reporting method."
                ),
                "details": {"asset_id": str(a.id)},
            })
    return findings


def f4797_1231_loss_lookback(tax_year: TaxYear) -> list[dict]:
    """D005: Long-term §1231 loss — check 5-year lookback rule."""
    assets = _get_disposed_assets(tax_year)
    findings = []
    for a in assets:
        if not a.date_acquired or not a.date_sold:
            continue
        months = (a.date_sold.year - a.date_acquired.year) * 12 + (a.date_sold.month - a.date_acquired.month)
        gain = a.gain_loss_on_sale or Decimal("0")
        if months > 12 and gain < 0:
            findings.append({
                "severity": "info",
                "message": (
                    f"Disposed asset '{a.description}' has a long-term §1231 loss. "
                    "Note: if there were net §1231 gains in the prior 5 years treated as "
                    "capital gains, the lookback rule under §1231(c) may require "
                    "recharacterization. Review IRC §1231(c)."
                ),
                "details": {"asset_id": str(a.id), "loss": str(gain)},
            })
    return findings


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BUILTIN_RULES = [
    # Trial Balance
    {
        "code": "TB_EXISTS",
        "name": "Trial Balance Exists",
        "description": "Checks that at least one parsed Trial Balance has been uploaded.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.tb_exists_check",
    },
    {
        "code": "TB_BALANCE",
        "name": "Trial Balance In Balance",
        "description": "Checks that total debits equal total credits.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.tb_balance_check",
    },
    {
        "code": "TB_ZERO_ROWS",
        "name": "Zero-Amount Rows",
        "description": "Flags rows where both debit and credit are zero.",
        "severity": "info",
        "rule_function": "apps.diagnostics.rules.tb_zero_rows_check",
    },
    # Math Diagnostics
    {
        "code": "MATH_BALANCE_SHEET",
        "name": "Balance Sheet Balances",
        "description": "Checks that total assets equal total liabilities + equity.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.math_balance_sheet_check",
    },
    {
        "code": "MATH_M1_RECONCILE",
        "name": "Schedule M-1 Reconciliation",
        "description": "Checks that M-1 reconciles to Schedule K total income.",
        "severity": "warning",
        "rule_function": "apps.diagnostics.rules.math_m1_reconciliation_check",
    },
    {
        "code": "MATH_M2_RETAINED",
        "name": "M-2 vs Retained Earnings",
        "description": "Checks that M-2 ending balance matches Balance Sheet retained earnings.",
        "severity": "warning",
        "rule_function": "apps.diagnostics.rules.math_m2_check",
    },
    {
        "code": "MATH_PAGE1",
        "name": "Page 1 Math",
        "description": "Verifies Page 1 income and deduction totals compute correctly.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.math_page1_income_check",
    },
    # Missing Info Diagnostics
    {
        "code": "MISSING_EIN",
        "name": "Entity EIN",
        "description": "Checks that the entity has an EIN.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.missing_ein_check",
    },
    {
        "code": "MISSING_ADDRESS",
        "name": "Entity Address",
        "description": "Checks that the entity has a complete mailing address.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.missing_address_check",
    },
    {
        "code": "MISSING_SHAREHOLDERS",
        "name": "Shareholders/Partners Entered",
        "description": "Checks that at least one shareholder or partner exists.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.missing_shareholders_check",
    },
    {
        "code": "MISSING_OFFICERS",
        "name": "Officers Entered",
        "description": "Checks that officer compensation has been entered.",
        "severity": "warning",
        "rule_function": "apps.diagnostics.rules.missing_officers_check",
    },
    {
        "code": "MISSING_INCOME",
        "name": "Income Entered",
        "description": "Checks that at least some income or deductions have been entered.",
        "severity": "warning",
        "rule_function": "apps.diagnostics.rules.missing_income_check",
    },
    {
        "code": "MISSING_DATES",
        "name": "Tax Year Dates",
        "description": "Checks that tax year start and end dates are set.",
        "severity": "warning",
        "rule_function": "apps.diagnostics.rules.missing_dates_check",
    },
    {
        "code": "MISSING_PREPARER",
        "name": "Preparer Assigned",
        "description": "Checks that a signing preparer is assigned.",
        "severity": "warning",
        "rule_function": "apps.diagnostics.rules.missing_preparer_check",
    },
    {
        "code": "OWNER_PCTS",
        "name": "Ownership Totals 100%",
        "description": "Checks that shareholder/partner ownership percentages sum to 100%.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.shareholder_ownership_check",
    },
    {
        "code": "OWNER_SSN",
        "name": "Shareholder/Partner SSNs",
        "description": "Checks that all shareholders/partners have SSN/EIN for K-1.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.shareholder_ssn_check",
    },
    # Form 4797 — Disposition Diagnostics
    {
        "code": "F4797_MISSING_DATES",
        "name": "4797: Missing Holding Period",
        "description": "Checks that disposed assets have both date acquired and date sold.",
        "severity": "error",
        "rule_function": "apps.diagnostics.rules.f4797_missing_holding_period",
    },
    {
        "code": "F4797_ZERO_DEPR",
        "name": "4797: Zero Depreciation on Depreciable Property",
        "description": "Flags depreciable disposed assets with no depreciation entered.",
        "severity": "warning",
        "rule_function": "apps.diagnostics.rules.f4797_zero_depreciation",
    },
    {
        "code": "F4797_GAIN_NO_RECAPTURE",
        "name": "4797: Gain with No Recapture",
        "description": "Flags §1245 property with gain but zero depreciation to recapture.",
        "severity": "warning",
        "rule_function": "apps.diagnostics.rules.f4797_gain_no_recapture",
    },
    {
        "code": "F4797_ZERO_SALE",
        "name": "4797: Zero Sale Price",
        "description": "Flags disposed assets with a zero sale price.",
        "severity": "warning",
        "rule_function": "apps.diagnostics.rules.f4797_zero_sale_price",
    },
    {
        "code": "F4797_1231_LOOKBACK",
        "name": "4797: §1231 Loss Lookback",
        "description": "Flags long-term §1231 losses for 5-year lookback review.",
        "severity": "info",
        "rule_function": "apps.diagnostics.rules.f4797_1231_loss_lookback",
    },
]
