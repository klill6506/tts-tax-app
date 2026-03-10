"""
Tests for depreciation calculation engine.

Tests MACRS tables, bonus depreciation, AMT, Georgia state, amortization,
and luxury auto limits.
"""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.tts_forms.depreciation_engine import (
    FEDERAL_179_LIMIT,
    GA_179_LIMIT,
    ZERO,
    _macrs_pct,
    _year_in_service,
    calculate_asset_depreciation,
    suggest_bonus_pct,
)


def _make_asset(**overrides):
    """Create a mock DepreciationAsset for testing."""
    defaults = {
        "group_label": "Machinery and Equipment",
        "property_label": "",
        "date_acquired": datetime.date(2025, 3, 15),
        "date_sold": None,
        "cost_basis": Decimal("100000"),
        "business_pct": Decimal("100.00"),
        "method": "200DB",
        "convention": "HY",
        "life": Decimal("7"),
        "sec_179_elected": Decimal("0"),
        "sec_179_prior": Decimal("0"),
        "bonus_pct": Decimal("100"),
        "bonus_amount": Decimal("0"),
        "prior_depreciation": Decimal("0"),
        "current_depreciation": Decimal("0"),
        "amt_method": "",
        "amt_life": None,
        "amt_prior_depreciation": Decimal("0"),
        "amt_current_depreciation": Decimal("0"),
        "state_method": "",
        "state_life": None,
        "state_prior_depreciation": Decimal("0"),
        "state_current_depreciation": Decimal("0"),
        "state_bonus_disallowed": Decimal("0"),
        "flow_to": "page1",
        "is_listed_property": False,
        "vehicle_miles_total": None,
        "vehicle_miles_business": None,
        "is_amortization": False,
        "amort_code": "",
        "amort_months": None,
    }
    defaults.update(overrides)
    asset = MagicMock()
    for k, v in defaults.items():
        setattr(asset, k, v)
    return asset


# ---------------------------------------------------------------------------
# MACRS Table Tests
# ---------------------------------------------------------------------------

class TestMACRSTables:
    def test_200db_hy_5yr_year1(self):
        pct = _macrs_pct("200DB", 5, "HY", 1)
        assert pct == Decimal("0.2000")

    def test_200db_hy_5yr_year2(self):
        pct = _macrs_pct("200DB", 5, "HY", 2)
        assert pct == Decimal("0.3200")

    def test_200db_hy_7yr_year1(self):
        pct = _macrs_pct("200DB", 7, "HY", 1)
        assert pct == Decimal("0.1429")

    def test_200db_hy_7yr_all_sum_to_1(self):
        total = sum(_macrs_pct("200DB", 7, "HY", y) for y in range(1, 9))
        assert total == Decimal("1.0002") or abs(total - Decimal("1")) < Decimal("0.001")

    def test_150db_hy_15yr_year1(self):
        pct = _macrs_pct("150DB", 15, "HY", 1)
        assert pct == Decimal("0.0500")

    def test_sl_hy_5yr_year1(self):
        pct = _macrs_pct("SL", 5, "HY", 1)
        assert pct == Decimal("0.1000")

    def test_sl_hy_5yr_year2(self):
        pct = _macrs_pct("SL", 5, "HY", 2)
        assert pct == Decimal("0.2000")

    def test_sl_mm_39yr_jan(self):
        pct = _macrs_pct("SL", 39.0, "MM", 1, month_placed=1)
        assert pct == Decimal("0.02461")

    def test_sl_mm_275yr_jul(self):
        pct = _macrs_pct("SL", 27.5, "MM", 1, month_placed=7)
        assert pct == Decimal("0.01667")

    def test_200db_hy_beyond_life_returns_zero(self):
        # 5-year has 6 entries, year 7 = 0
        pct = _macrs_pct("200DB", 5, "HY", 7)
        assert pct == ZERO


# ---------------------------------------------------------------------------
# Year in Service
# ---------------------------------------------------------------------------

class TestYearInService:
    def test_same_year(self):
        assert _year_in_service(datetime.date(2025, 6, 1), 2025) == 1

    def test_second_year(self):
        assert _year_in_service(datetime.date(2025, 6, 1), 2026) == 2


# ---------------------------------------------------------------------------
# Bonus Suggestion
# ---------------------------------------------------------------------------

class TestBonusSuggestion:
    def test_post_obbba(self):
        assert suggest_bonus_pct(datetime.date(2025, 2, 1)) == Decimal("100")

    def test_pre_obbba(self):
        assert suggest_bonus_pct(datetime.date(2025, 1, 15)) == Decimal("40")

    def test_on_cutoff(self):
        # Jan 20, 2025 is the cutoff — on that date = 40%
        assert suggest_bonus_pct(datetime.date(2025, 1, 20)) == Decimal("40")

    def test_land(self):
        assert suggest_bonus_pct(datetime.date(2025, 6, 1), group_label="Land") == ZERO

    def test_amortization(self):
        assert suggest_bonus_pct(datetime.date(2025, 6, 1), is_amortization=True) == ZERO


# ---------------------------------------------------------------------------
# Full Asset Calculation
# ---------------------------------------------------------------------------

class TestCalculateAsset:
    def test_land_no_depreciation(self):
        asset = _make_asset(group_label="Land")
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == ZERO

    def test_none_method_no_depreciation(self):
        asset = _make_asset(method="NONE")
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == ZERO

    def test_future_asset_no_depreciation(self):
        asset = _make_asset(date_acquired=datetime.date(2026, 1, 1))
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == ZERO

    def test_100pct_bonus_first_year(self):
        """100% bonus: entire basis is expensed in year 1."""
        asset = _make_asset(
            cost_basis=Decimal("50000"),
            bonus_pct=Decimal("100"),
            method="200DB",
            life=Decimal("7"),
        )
        result = calculate_asset_depreciation(asset, 2025)
        # 100% bonus on full basis = $50,000
        assert result["bonus_amount"] == Decimal("50000.00")
        assert result["current_depreciation"] == Decimal("50000.00")

    def test_no_bonus_macrs_200db_7yr(self):
        """No bonus, 7-yr 200DB HY: year 1 = 14.29%."""
        asset = _make_asset(
            cost_basis=Decimal("100000"),
            bonus_pct=Decimal("0"),
            method="200DB",
            life=Decimal("7"),
        )
        result = calculate_asset_depreciation(asset, 2025)
        assert result["bonus_amount"] == ZERO
        assert result["current_depreciation"] == Decimal("14290.00")

    def test_179_reduces_basis(self):
        """Section 179 reduces depreciable basis before bonus."""
        asset = _make_asset(
            cost_basis=Decimal("100000"),
            sec_179_elected=Decimal("50000"),
            bonus_pct=Decimal("100"),
        )
        result = calculate_asset_depreciation(asset, 2025)
        # 179 = $50k, bonus on remaining $50k = $50k, total = $100k
        assert result["current_depreciation"] == Decimal("100000.00")
        assert result["bonus_amount"] == Decimal("50000.00")

    def test_40pct_bonus(self):
        """40% bonus (pre-OBBBA): partial bonus + MACRS on remainder."""
        asset = _make_asset(
            cost_basis=Decimal("100000"),
            bonus_pct=Decimal("40"),
            method="200DB",
            life=Decimal("5"),
        )
        result = calculate_asset_depreciation(asset, 2025)
        # Bonus = 40% of $100k = $40k
        assert result["bonus_amount"] == Decimal("40000.00")
        # Remaining $60k at 200DB 5-yr HY year 1 = 20% = $12k
        # Total = $40k + $12k = $52k
        assert result["current_depreciation"] == Decimal("52000.00")

    def test_business_pct_50(self):
        """50% business use reduces all calculations."""
        asset = _make_asset(
            cost_basis=Decimal("100000"),
            business_pct=Decimal("50.00"),
            bonus_pct=Decimal("0"),
            method="200DB",
            life=Decimal("7"),
        )
        result = calculate_asset_depreciation(asset, 2025)
        # Depreciable basis = $50k, 14.29% = $7,145
        assert result["current_depreciation"] == Decimal("7145.00")

    def test_sold_in_prior_year(self):
        """Asset sold in prior year: no depreciation."""
        asset = _make_asset(
            date_acquired=datetime.date(2020, 1, 1),
            date_sold=datetime.date(2024, 6, 15),
        )
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == ZERO

    def test_sl_mm_39yr(self):
        """39-year S/L MM property placed in service March."""
        asset = _make_asset(
            cost_basis=Decimal("500000"),
            bonus_pct=Decimal("0"),
            method="SL",
            convention="MM",
            life=Decimal("39"),
            date_acquired=datetime.date(2025, 3, 1),
        )
        result = calculate_asset_depreciation(asset, 2025)
        # First year rate for March = 0.02033 * $500k = $10,165
        assert result["current_depreciation"] == Decimal("10165.00")


# ---------------------------------------------------------------------------
# AMT Depreciation
# ---------------------------------------------------------------------------

class TestAMT:
    def test_200db_uses_150db_for_amt(self):
        """200DB assets use 150DB for AMT."""
        asset = _make_asset(
            cost_basis=Decimal("100000"),
            bonus_pct=Decimal("0"),
            method="200DB",
            life=Decimal("7"),
        )
        result = calculate_asset_depreciation(asset, 2025)
        # Federal: 200DB 7yr HY year 1 = 14.29% = $14,290
        assert result["current_depreciation"] == Decimal("14290.00")
        # AMT: 150DB 7yr HY year 1 = 10.71% = $10,710
        assert result["amt_current_depreciation"] == Decimal("10710.00")

    def test_sl_same_for_amt(self):
        """SL assets have same AMT as regular."""
        asset = _make_asset(
            cost_basis=Decimal("500000"),
            bonus_pct=Decimal("0"),
            method="SL",
            convention="MM",
            life=Decimal("39"),
            date_acquired=datetime.date(2025, 3, 1),
        )
        result = calculate_asset_depreciation(asset, 2025)
        # For SL, AMT should equal current depreciation
        # The _calculate_amt function returns ZERO for SL because no preference
        # Actually for SL it returns the current_depreciation value
        # SL has no AMT preference, so AMT = regular
        assert result["amt_current_depreciation"] == result["current_depreciation"]


# ---------------------------------------------------------------------------
# Georgia State Depreciation
# ---------------------------------------------------------------------------

class TestGeorgiaState:
    def test_bonus_disallowed(self):
        """Georgia disallows all federal bonus depreciation."""
        asset = _make_asset(
            cost_basis=Decimal("100000"),
            bonus_pct=Decimal("100"),
        )
        result = calculate_asset_depreciation(asset, 2025)
        # Federal gets full bonus
        assert result["bonus_amount"] == Decimal("100000.00")
        # Georgia disallows it
        assert result["state_bonus_disallowed"] == Decimal("100000.00")
        # Georgia calculates depreciation on full basis without bonus
        # $100k at 200DB 7yr HY year 1 = 14.29% = $14,290
        assert result["state_current_depreciation"] == Decimal("14290.00")

    def test_no_bonus_state_equals_federal(self):
        """When no bonus, state depreciation equals federal."""
        asset = _make_asset(
            cost_basis=Decimal("100000"),
            bonus_pct=Decimal("0"),
            method="200DB",
            life=Decimal("7"),
        )
        result = calculate_asset_depreciation(asset, 2025)
        assert result["state_bonus_disallowed"] == ZERO
        assert result["state_current_depreciation"] == result["current_depreciation"]


# ---------------------------------------------------------------------------
# Amortization
# ---------------------------------------------------------------------------

class TestAmortization:
    def test_section_197_full_year(self):
        """Section 197: $180k over 180 months = $12k/year."""
        asset = _make_asset(
            group_label="Intangibles/Amortization",
            is_amortization=True,
            amort_code="197",
            amort_months=180,
            cost_basis=Decimal("180000"),
            bonus_pct=Decimal("0"),
            method="SL",
            date_acquired=datetime.date(2024, 1, 1),
            prior_depreciation=Decimal("12000"),
        )
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == Decimal("12000.00")

    def test_section_197_first_year_prorate(self):
        """First year pro-rated: acquired July = 6 months."""
        asset = _make_asset(
            group_label="Intangibles/Amortization",
            is_amortization=True,
            amort_code="197",
            amort_months=180,
            cost_basis=Decimal("180000"),
            bonus_pct=Decimal("0"),
            method="SL",
            date_acquired=datetime.date(2025, 7, 1),
            prior_depreciation=Decimal("0"),
        )
        result = calculate_asset_depreciation(asset, 2025)
        # $180k / 180 months = $1k/month * 6 months (Jul-Dec) = $6k
        assert result["current_depreciation"] == Decimal("6000.00")
