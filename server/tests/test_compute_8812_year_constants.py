"""Regression tests for Schedule 8812 year-keyed constants (OBBBA parameterization).

OBBBA §70104(a)(2) raised the per-QC credit from $2,000 to $2,200 for
TY 2025+ (permanent). TY 2024 must still use the pre-OBBBA $2,000.
"""
from decimal import Decimal

from apps.returns.compute_8812 import _constants_for_year


def test_ty2025_uses_obbba_qc_amount():
    c = _constants_for_year(2025)
    assert c["QC_AMOUNT"] == Decimal("2200")
    assert c["ACTC_PER_CHILD_CAP"] == Decimal("1700")


def test_ty2024_uses_pre_obbba_qc_amount():
    c = _constants_for_year(2024)
    assert c["QC_AMOUNT"] == Decimal("2000")
    assert c["ACTC_PER_CHILD_CAP"] == Decimal("1700")


def test_future_years_default_to_obbba():
    # Future years (2026+) should continue to use OBBBA values until a
    # subsequent law change is recorded here.
    assert _constants_for_year(2026)["QC_AMOUNT"] == Decimal("2200")


def test_phaseout_thresholds_stable_across_supported_years():
    # TCJA values — same for both 2024 and 2025.
    for year in (2024, 2025):
        c = _constants_for_year(year)
        assert c["PHASEOUT_THRESHOLD_MFJ"] == Decimal("400000")
        assert c["PHASEOUT_THRESHOLD_OTHER"] == Decimal("200000")
        assert c["PHASEOUT_RATE"] == Decimal("0.05")


def test_actc_method_constants_stable():
    # 15% method + $2,500 earned-income floor unchanged.
    for year in (2024, 2025):
        c = _constants_for_year(year)
        assert c["ACTC_EARNED_INCOME_FLOOR"] == Decimal("2500")
        assert c["ACTC_PERCENT"] == Decimal("0.15")
