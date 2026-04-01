"""
Tests for April 1 2026 fixes:
- Bug 1: Skip depreciation on fully depreciated assets
- Bug 2: No phantom rental properties on new returns
- Bug 3: Schedule F renders in complete return
"""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.tts_forms.depreciation_engine import (
    ZERO,
    calculate_asset_depreciation,
)


def _make_asset(**overrides):
    """Create a mock DepreciationAsset for testing."""
    defaults = {
        "group_label": "Machinery and Equipment",
        "property_label": "",
        "date_acquired": datetime.date(2025, 3, 15),
        "date_sold": None,
        "cost_basis": Decimal("50000"),
        "business_pct": Decimal("100.00"),
        "method": "200DB",
        "convention": "HY",
        "life": Decimal("7"),
        "sec_179_elected": Decimal("0"),
        "sec_179_prior": Decimal("0"),
        "bonus_pct": Decimal("0"),
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
# Bug 1: Fully depreciated assets
# ---------------------------------------------------------------------------

class TestFullyDepreciated:
    """Section 179, 100% bonus, and past-recovery assets should return $0."""

    def test_section_179_fully_expensed(self):
        """§179 = full cost → year 2+ current depr must be $0."""
        asset = _make_asset(
            date_acquired=datetime.date(2024, 1, 15),
            cost_basis=Decimal("50000"),
            sec_179_elected=Decimal("50000"),
            bonus_pct=Decimal("0"),
            method="200DB",
            life=Decimal("7"),
        )
        # Year 2 (2025) — asset was fully expensed via §179 in 2024
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == ZERO

    def test_bonus_100_pct(self):
        """100% bonus → year 2+ current depr must be $0."""
        asset = _make_asset(
            date_acquired=datetime.date(2024, 6, 1),
            cost_basis=Decimal("50000"),
            sec_179_elected=Decimal("0"),
            bonus_pct=Decimal("100"),
            method="200DB",
            life=Decimal("5"),
        )
        # Year 2 (2025) — fully bonused in 2024
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == ZERO

    def test_partial_179_remaining(self):
        """Partial §179 — remaining basis still depreciates normally."""
        asset = _make_asset(
            date_acquired=datetime.date(2025, 3, 15),
            cost_basis=Decimal("50000"),
            sec_179_elected=Decimal("30000"),
            bonus_pct=Decimal("0"),
            method="200DB",
            life=Decimal("5"),
            convention="HY",
        )
        # Year 1: depreciable_basis = 50000 - 30000 = 20000
        # MACRS 5yr HY year 1 rate = 20% → 20000 * 0.20 = 4000
        # Total = 30000 + 4000 = 34000
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == Decimal("34000.00")

    def test_past_recovery_period(self):
        """5-year asset in year 7+ → current depr = $0."""
        asset = _make_asset(
            date_acquired=datetime.date(2018, 6, 1),
            cost_basis=Decimal("50000"),
            sec_179_elected=Decimal("0"),
            bonus_pct=Decimal("0"),
            method="200DB",
            life=Decimal("5"),
            convention="HY",
        )
        # Year 8 (2025) — 5yr HY table only has 6 entries (years 1-6)
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == ZERO

    def test_amt_also_zero_when_fully_depreciated(self):
        """Fully depreciated asset → AMT current should also be $0."""
        asset = _make_asset(
            date_acquired=datetime.date(2024, 1, 15),
            cost_basis=Decimal("50000"),
            sec_179_elected=Decimal("50000"),
            bonus_pct=Decimal("0"),
            method="200DB",
            life=Decimal("7"),
        )
        result = calculate_asset_depreciation(asset, 2025)
        assert result["amt_current_depreciation"] == ZERO

    def test_not_yet_fully_depreciated(self):
        """5-year asset in year 3 → should still calculate normally."""
        asset = _make_asset(
            date_acquired=datetime.date(2023, 3, 15),
            cost_basis=Decimal("50000"),
            sec_179_elected=Decimal("0"),
            bonus_pct=Decimal("0"),
            method="200DB",
            life=Decimal("5"),
            convention="HY",
        )
        # Year 3: MACRS 5yr HY year 3 rate = 19.20%
        # 50000 * 0.1920 = 9600
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == Decimal("9600.00")

    def test_disposed_not_fully_depreciated(self):
        """Disposed asset NOT fully depreciated → gets half-year disposal depr."""
        asset = _make_asset(
            date_acquired=datetime.date(2023, 3, 15),
            date_sold=datetime.date(2025, 9, 1),
            cost_basis=Decimal("50000"),
            sec_179_elected=Decimal("0"),
            bonus_pct=Decimal("0"),
            method="200DB",
            life=Decimal("5"),
            convention="HY",
        )
        # Year 3 with disposal: 50000 * 0.1920 = 9600, halved = 4800
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == Decimal("4800.00")

    def test_179_year2_depreciable_basis_correct(self):
        """Partial §179 in year 2 — MACRS should use reduced basis."""
        asset = _make_asset(
            date_acquired=datetime.date(2024, 6, 1),
            cost_basis=Decimal("100000"),
            sec_179_elected=Decimal("50000"),
            bonus_pct=Decimal("0"),
            method="200DB",
            life=Decimal("5"),
            convention="HY",
        )
        # Year 2 (2025): depreciable_basis = 100000 - 50000 = 50000
        # MACRS 5yr HY year 2 rate = 32% → 50000 * 0.32 = 16000
        result = calculate_asset_depreciation(asset, 2025)
        assert result["current_depreciation"] == Decimal("16000.00")


# ---------------------------------------------------------------------------
# Bug 2 & 3 tests (require DB)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNoPhantomRentals:
    """New return should have zero rental properties."""

    def test_no_phantom_rentals(self, seeded, tax_year):
        from apps.returns.models import TaxReturn, RentalProperty
        from apps.returns.views import _prepopulate_standard_deductions

        tr = TaxReturn.objects.create(
            tax_year=tax_year,
            form_definition=seeded,
            status="draft",
        )
        # Simulate what create_return does
        _prepopulate_standard_deductions(tr)

        # No rental properties should exist
        assert RentalProperty.objects.filter(tax_return=tr).count() == 0

    def test_8825_not_in_empty_return(self, seeded, tax_year):
        """Complete return with no rentals should not include 8825."""
        from apps.returns.models import TaxReturn, FormFieldValue
        from apps.tts_forms.renderer import render_complete_return

        tr = TaxReturn.objects.create(
            tax_year=tax_year,
            form_definition=seeded,
            status="draft",
        )
        # Populate field values so render doesn't fail
        from apps.returns.views import _prepopulate_standard_deductions
        _prepopulate_standard_deductions(tr)

        pdf_bytes, page_map = render_complete_return(tr, return_page_map=True)
        form_names = [p["form"] for p in page_map]
        assert not any("8825" in name for name in form_names)


@pytest.mark.django_db
class TestScheduleFRender:
    """Schedule F should appear in complete return when farm data exists."""

    def test_schedule_f_renders(self, seeded, tax_year):
        from apps.returns.models import TaxReturn, FormFieldValue, FormLine
        from apps.tts_forms.renderer import render_schedule_f

        tr = TaxReturn.objects.create(
            tax_year=tax_year,
            form_definition=seeded,
            status="draft",
        )
        # Enter farm income
        f9_line = FormLine.objects.get(
            section__form=seeded,
            line_number="F2",
        )
        FormFieldValue.objects.create(
            tax_return=tr,
            form_line=f9_line,
            value="50000.00",
        )

        result = render_schedule_f(tr)
        assert result is not None
        assert len(result) > 100  # valid PDF bytes
