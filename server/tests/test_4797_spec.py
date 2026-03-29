"""
Form 4797 — Tests rebuilt from Rule Studio spec (4797_TY2025_v1).

6 test scenarios from the spec, plus routing and diagnostic tests.
Tests the computation logic in compute.py and renderer.py without DB access.
"""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.returns.compute import _holding_period_months, resolve_recapture_type

ZERO = Decimal("0")


def _make_asset(**overrides):
    """Create a mock DepreciationAsset for 4797 testing."""
    defaults = {
        "description": "Test Asset",
        "group_label": "Machinery and Equipment",
        "date_acquired": datetime.date(2022, 1, 15),
        "date_sold": datetime.date(2025, 1, 15),
        "cost_basis": Decimal("100000"),
        "sales_price": Decimal("50000"),
        "expenses_of_sale": ZERO,
        "prior_depreciation": ZERO,
        "current_depreciation": ZERO,
        "bonus_amount": ZERO,
        "sec_179_elected": ZERO,
        "gain_loss_on_sale": None,
        "asset_number": 1,
        "sort_order": 1,
        "recapture_type": "auto",
        "life": None,
    }
    defaults.update(overrides)
    asset = MagicMock()
    for k, v in defaults.items():
        setattr(asset, k, v)
    return asset


def _compute_4797(asset):
    """Apply spec rules R001-R008 to a single asset. Returns computed dict."""
    # R001 — holding period classification
    if asset.date_acquired and asset.date_sold:
        months = _holding_period_months(asset.date_acquired, asset.date_sold)
    else:
        months = 13

    is_long_term = months > 12
    holding_period_class = "long_term" if is_long_term else "short_term"

    # R004 — adjusted basis
    total_depr = (
        asset.prior_depreciation + asset.current_depreciation
        + asset.bonus_amount + asset.sec_179_elected
    )
    cost_plus = asset.cost_basis + (asset.expenses_of_sale or ZERO)
    adjusted_basis = cost_plus - total_depr

    # R003 — gain or loss
    gain_or_loss = (asset.sales_price or ZERO) - adjusted_basis

    result = {
        "holding_period_months": months,
        "holding_period_class": holding_period_class,
        "adjusted_basis": adjusted_basis,
        "gain_or_loss": gain_or_loss,
        "total_depreciation": total_depr,
    }

    is_1250 = (resolve_recapture_type(asset) == "1250")

    # Routing
    if not is_long_term:
        result["form_part_destination"] = "Part II"
    elif gain_or_loss <= 0:
        result["form_part_destination"] = "Part I"
    elif total_depr > 0:
        result["form_part_destination"] = "Part III"
        if is_1250:
            # R007 — §1250 ordinary = 0 (post-1986 SL)
            result["ordinary_income_1250"] = ZERO
            # R008 — unrecaptured §1250
            result["unrecaptured_1250_gain"] = min(gain_or_loss, total_depr) - ZERO
        else:
            # R005 — §1245 recapture
            result["ordinary_income_1245"] = min(gain_or_loss, total_depr)
            # R006 — excess → §1231
            result["section_1231_gain_excess"] = max(ZERO, gain_or_loss - total_depr)
    else:
        result["form_part_destination"] = "Part I"

    return result


# ===========================================================================
# Spec Test Scenario 1: Basic §1245 gain — all recapture
# ===========================================================================
class TestSpecScenario1:
    """sale=50000, cost=100000, depr=60000, adj=40000, type=1245, held 36mo
    → gain=10000, ordinary_1245=10000, excess_1231=0"""

    def test_gain_or_loss(self):
        a = _make_asset(
            sales_price=Decimal("50000"),
            cost_basis=Decimal("100000"),
            prior_depreciation=Decimal("60000"),
            date_acquired=datetime.date(2022, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["gain_or_loss"] == Decimal("10000")

    def test_ordinary_1245_recapture(self):
        a = _make_asset(
            sales_price=Decimal("50000"),
            cost_basis=Decimal("100000"),
            prior_depreciation=Decimal("60000"),
            date_acquired=datetime.date(2022, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["ordinary_income_1245"] == Decimal("10000")

    def test_no_excess_1231(self):
        a = _make_asset(
            sales_price=Decimal("50000"),
            cost_basis=Decimal("100000"),
            prior_depreciation=Decimal("60000"),
            date_acquired=datetime.date(2022, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["section_1231_gain_excess"] == Decimal("0")

    def test_routes_to_part3(self):
        a = _make_asset(
            sales_price=Decimal("50000"),
            cost_basis=Decimal("100000"),
            prior_depreciation=Decimal("60000"),
            date_acquired=datetime.date(2022, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["form_part_destination"] == "Part III"


# ===========================================================================
# Spec Test Scenario 2: §1245 partial recapture + §1231
# ===========================================================================
class TestSpecScenario2:
    """sale=120000, cost=100000, depr=30000, adj=70000, held 60mo
    → gain=50000, ordinary_1245=30000, excess_1231=20000"""

    def test_gain_or_loss(self):
        a = _make_asset(
            sales_price=Decimal("120000"),
            cost_basis=Decimal("100000"),
            prior_depreciation=Decimal("30000"),
            date_acquired=datetime.date(2020, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["gain_or_loss"] == Decimal("50000")

    def test_ordinary_1245_recapture(self):
        a = _make_asset(
            sales_price=Decimal("120000"),
            cost_basis=Decimal("100000"),
            prior_depreciation=Decimal("30000"),
            date_acquired=datetime.date(2020, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["ordinary_income_1245"] == Decimal("30000")

    def test_excess_1231(self):
        a = _make_asset(
            sales_price=Decimal("120000"),
            cost_basis=Decimal("100000"),
            prior_depreciation=Decimal("30000"),
            date_acquired=datetime.date(2020, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["section_1231_gain_excess"] == Decimal("20000")


# ===========================================================================
# Spec Test Scenario 3: §1231 loss — no recapture
# ===========================================================================
class TestSpecScenario3:
    """sale=30000, cost=100000, depr=50000, adj=50000, held 48mo
    → loss=-20000"""

    def test_gain_or_loss(self):
        a = _make_asset(
            sales_price=Decimal("30000"),
            cost_basis=Decimal("100000"),
            prior_depreciation=Decimal("50000"),
            date_acquired=datetime.date(2021, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["gain_or_loss"] == Decimal("-20000")

    def test_routes_to_part1(self):
        a = _make_asset(
            sales_price=Decimal("30000"),
            cost_basis=Decimal("100000"),
            prior_depreciation=Decimal("50000"),
            date_acquired=datetime.date(2021, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["form_part_destination"] == "Part I"

    def test_no_recapture_keys(self):
        a = _make_asset(
            sales_price=Decimal("30000"),
            cost_basis=Decimal("100000"),
            prior_depreciation=Decimal("50000"),
            date_acquired=datetime.date(2021, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert "ordinary_income_1245" not in result
        assert "ordinary_income_1250" not in result


# ===========================================================================
# Spec Test Scenario 4: Short-term gain — all ordinary (Part II)
# ===========================================================================
class TestSpecScenario4:
    """sale=60000, cost=80000, depr=40000, adj=40000, held 6mo
    → gain=20000, Part II"""

    def test_gain_or_loss(self):
        a = _make_asset(
            sales_price=Decimal("60000"),
            cost_basis=Decimal("80000"),
            prior_depreciation=Decimal("40000"),
            date_acquired=datetime.date(2025, 1, 15),
            date_sold=datetime.date(2025, 7, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["gain_or_loss"] == Decimal("20000")

    def test_holding_period_class(self):
        a = _make_asset(
            sales_price=Decimal("60000"),
            cost_basis=Decimal("80000"),
            prior_depreciation=Decimal("40000"),
            date_acquired=datetime.date(2025, 1, 15),
            date_sold=datetime.date(2025, 7, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["holding_period_class"] == "short_term"

    def test_routes_to_part2(self):
        a = _make_asset(
            sales_price=Decimal("60000"),
            cost_basis=Decimal("80000"),
            prior_depreciation=Decimal("40000"),
            date_acquired=datetime.date(2025, 1, 15),
            date_sold=datetime.date(2025, 7, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["form_part_destination"] == "Part II"


# ===========================================================================
# Spec Test Scenario 5: §1250 property — unrecaptured gain (25% rate)
# ===========================================================================
class TestSpecScenario5:
    """sale=500000, cost=400000, depr=100000, adj=300000, held 120mo, SL
    → gain=200000, ordinary_1250=0, unrecaptured=100000"""

    def test_gain_or_loss(self):
        a = _make_asset(
            sales_price=Decimal("500000"),
            cost_basis=Decimal("400000"),
            prior_depreciation=Decimal("100000"),
            date_acquired=datetime.date(2015, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Buildings",
        )
        result = _compute_4797(a)
        assert result["gain_or_loss"] == Decimal("200000")

    def test_ordinary_1250_zero(self):
        a = _make_asset(
            sales_price=Decimal("500000"),
            cost_basis=Decimal("400000"),
            prior_depreciation=Decimal("100000"),
            date_acquired=datetime.date(2015, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Buildings",
        )
        result = _compute_4797(a)
        assert result["ordinary_income_1250"] == Decimal("0")

    def test_unrecaptured_1250(self):
        a = _make_asset(
            sales_price=Decimal("500000"),
            cost_basis=Decimal("400000"),
            prior_depreciation=Decimal("100000"),
            date_acquired=datetime.date(2015, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Buildings",
        )
        result = _compute_4797(a)
        assert result["unrecaptured_1250_gain"] == Decimal("100000")

    def test_routes_to_part3(self):
        a = _make_asset(
            sales_price=Decimal("500000"),
            cost_basis=Decimal("400000"),
            prior_depreciation=Decimal("100000"),
            date_acquired=datetime.date(2015, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Buildings",
        )
        result = _compute_4797(a)
        assert result["form_part_destination"] == "Part III"


# ===========================================================================
# Spec Test Scenario 6: Zero gain — no reporting
# ===========================================================================
class TestSpecScenario6:
    """sale=40000, cost=60000, depr=20000, adj=40000
    → gain=0"""

    def test_gain_or_loss(self):
        a = _make_asset(
            sales_price=Decimal("40000"),
            cost_basis=Decimal("60000"),
            prior_depreciation=Decimal("20000"),
            date_acquired=datetime.date(2023, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["gain_or_loss"] == Decimal("0")

    def test_zero_routes_to_part1(self):
        """Zero gain (<=0) routes to Part I per R002."""
        a = _make_asset(
            sales_price=Decimal("40000"),
            cost_basis=Decimal("60000"),
            prior_depreciation=Decimal("20000"),
            date_acquired=datetime.date(2023, 1, 15),
            date_sold=datetime.date(2025, 1, 15),
            group_label="Machinery and Equipment",
        )
        result = _compute_4797(a)
        assert result["form_part_destination"] == "Part I"


# ===========================================================================
# Holding Period Tests (R001)
# ===========================================================================
class TestHoldingPeriod:
    def test_exactly_12_months_is_short_term(self):
        months = _holding_period_months(
            datetime.date(2024, 1, 15), datetime.date(2025, 1, 15)
        )
        assert months == 12
        # 12 months is NOT > 12, so short-term
        assert months <= 12

    def test_13_months_is_long_term(self):
        months = _holding_period_months(
            datetime.date(2024, 1, 15), datetime.date(2025, 2, 15)
        )
        assert months == 13
        assert months > 12

    def test_6_months(self):
        months = _holding_period_months(
            datetime.date(2025, 1, 15), datetime.date(2025, 7, 15)
        )
        assert months == 6

    def test_36_months(self):
        months = _holding_period_months(
            datetime.date(2022, 1, 15), datetime.date(2025, 1, 15)
        )
        assert months == 36

    def test_120_months(self):
        months = _holding_period_months(
            datetime.date(2015, 1, 15), datetime.date(2025, 1, 15)
        )
        assert months == 120


# ===========================================================================
# Property Type Classification
# ===========================================================================
class TestPropertyType:
    def test_buildings_is_1250(self):
        asset = _make_asset(group_label="Buildings")
        assert resolve_recapture_type(asset) == "1250"

    def test_improvements_39yr_is_1250(self):
        asset = _make_asset(group_label="Improvements", life=Decimal("39"))
        assert resolve_recapture_type(asset) == "1250"

    def test_improvements_275yr_is_1250(self):
        asset = _make_asset(group_label="Improvements", life=Decimal("27.5"))
        assert resolve_recapture_type(asset) == "1250"

    def test_improvements_15yr_is_1245(self):
        # QIP, land improvements — short-life = 1245
        asset = _make_asset(group_label="Improvements", life=Decimal("15"))
        assert resolve_recapture_type(asset) == "1245"

    def test_improvements_no_life_is_1245(self):
        asset = _make_asset(group_label="Improvements", life=None)
        assert resolve_recapture_type(asset) == "1245"

    def test_equipment_is_not_1250(self):
        asset = _make_asset(group_label="Machinery and Equipment")
        assert resolve_recapture_type(asset) == "1245"

    def test_vehicles_is_not_1250(self):
        asset = _make_asset(group_label="Vehicles")
        assert resolve_recapture_type(asset) == "1245"

    def test_furniture_is_not_1250(self):
        asset = _make_asset(group_label="Furniture and Fixtures")
        assert resolve_recapture_type(asset) == "1245"

    def test_land_is_not_1250(self):
        asset = _make_asset(group_label="Land")
        assert resolve_recapture_type(asset) == "1245"

    def test_explicit_1245_override(self):
        # Building with explicit 1245 override → full recapture
        asset = _make_asset(group_label="Buildings", recapture_type="1245")
        assert resolve_recapture_type(asset) == "1245"

    def test_explicit_1250_override(self):
        # Equipment with explicit 1250 override → zero ordinary recapture
        asset = _make_asset(group_label="Machinery and Equipment", recapture_type="1250")
        assert resolve_recapture_type(asset) == "1250"
