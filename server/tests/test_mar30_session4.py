"""
Mar 30 Session 4 tests:
1. 8825 single property — only column A has data
2. Building defaults — SL, MM, 39yr, AMT life 40
3. Building AMT uses regular life for SL (AMT = regular for SL assets)
4. AAA can go negative from distributions
5. 1125-A instruction page skip
"""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.core.management import call_command

from apps.returns.compute import FORMULAS_1120S, ZERO, _d, compute_return
from apps.returns.models import (
    FormDefinition,
    FormFieldValue,
    FormLine,
    TaxReturn,
)


# ===========================================================================
# Helpers
# ===========================================================================

class _DefaultZeroDict(dict):
    def __missing__(self, key):
        return Decimal("0")


def _run_formulas(inputs: dict) -> dict:
    values = _DefaultZeroDict({k: Decimal(str(v)) for k, v in inputs.items()})
    for line_number, formula_fn in FORMULAS_1120S:
        values[line_number] = formula_fn(values)
    return values


# ===========================================================================
# Test: AAA can go negative from distributions
# ===========================================================================

class TestAAANegative:
    """M2_8a should allow negative when distributions exceed AAA."""

    def test_aaa_goes_negative(self):
        """Distributions of $50k against $30k AAA = -$20k ending AAA."""
        vals = _run_formulas({
            "1a": 20000,       # income → K1 = 20000
            "M2_1a": 10000,    # beginning AAA
            "K16d": 50000,     # distributions
        })
        # M2_6a = 10000 + 20000 = 30000
        # M2_7a = K16d = 50000
        # M2_8a = 30000 - 50000 = -20000
        assert vals["M2_8a"] == Decimal("-20000"), (
            f"M2_8a should be -20000, got {vals['M2_8a']}"
        )

    def test_aaa_no_cap_at_zero(self):
        """Old behavior capped at 0. New behavior allows negative."""
        vals = _run_formulas({
            "M2_1a": 0,
            "K16d": 10000,     # distributions with no income
        })
        # M2_6a = 0, M2_7a = 10000
        # M2_8a = 0 - 10000 = -10000
        assert vals["M2_8a"] == Decimal("-10000"), (
            f"M2_8a should be -10000, got {vals['M2_8a']}"
        )


# ===========================================================================
# Test: 8825 single property rendering
# ===========================================================================

class TestRender8825Summary:
    """8825 summary lines use correct IRS line semantics."""

    def test_8825_summary_splits_income_loss(self):
        """20a = gross income, 20b = gross expenses, 23 = net (Dec 2025 revision)."""
        from unittest.mock import patch, MagicMock

        prop_a = MagicMock()
        prop_a.description = "Profit property"
        prop_a.property_type = ""
        prop_a.fair_rental_days = None
        prop_a.personal_use_days = None
        prop_a.rents_received = Decimal("24000")
        prop_a.total_expenses = Decimal("15000")
        prop_a.net_rent = Decimal("9000")  # positive
        prop_a.sort_order = 1
        for f, _ in [
            ("advertising", "3"), ("auto_and_travel", "4"),
            ("cleaning_and_maintenance", "5"), ("commissions", "6"),
            ("insurance", "7"), ("interest_mortgage", "8"),
            ("legal_and_professional", "9"), ("taxes", "10"),
            ("repairs", "11"), ("utilities", "12"),
            ("depreciation", "14"), ("other_expenses", "17"),
        ]:
            setattr(prop_a, f, Decimal("0"))

        prop_b = MagicMock()
        prop_b.description = "Loss property"
        prop_b.property_type = ""
        prop_b.fair_rental_days = None
        prop_b.personal_use_days = None
        prop_b.rents_received = Decimal("5000")
        prop_b.total_expenses = Decimal("8000")
        prop_b.net_rent = Decimal("-3000")  # negative
        prop_b.sort_order = 2
        for f, _ in [
            ("advertising", "3"), ("auto_and_travel", "4"),
            ("cleaning_and_maintenance", "5"), ("commissions", "6"),
            ("insurance", "7"), ("interest_mortgage", "8"),
            ("legal_and_professional", "9"), ("taxes", "10"),
            ("repairs", "11"), ("utilities", "12"),
            ("depreciation", "14"), ("other_expenses", "17"),
        ]:
            setattr(prop_b, f, Decimal("0"))

        captured = {}

        def mock_render(form_id, tax_year, field_values, header_data):
            captured.update(field_values)
            return b"%PDF-mock"

        props = [prop_a, prop_b]
        mock_qs = MagicMock()
        mock_qs.exists.return_value = True
        mock_qs.order_by.return_value = mock_qs
        mock_qs.__iter__ = lambda s: iter(props)
        mock_qs.__getitem__ = lambda s, idx: props[idx] if isinstance(idx, int) else props[:idx.stop] if isinstance(idx, slice) else props

        with patch("apps.tts_forms.renderer.render", side_effect=mock_render), \
             patch("apps.returns.models.RentalProperty.objects") as mock_mgr:
            mock_mgr.filter.return_value = mock_qs
            from apps.tts_forms.renderer import render_8825
            mock_tr = MagicMock()
            mock_tr.form_definition.tax_year_applicable = 2025
            mock_tr.tax_year.entity.legal_name = "Test Corp"
            mock_tr.tax_year.entity.name = "Test Corp"
            mock_tr.tax_year.entity.ein = "12-3456789"
            render_8825(mock_tr)

        # 20a = total gross income = 24000 + 5000 = 29000
        assert captured["20a"][0] == "29000"
        # 20b = total gross expenses = 15000 + 8000 = 23000
        assert captured["20b"][0] == "23000"
        # 23 = net = 29000 - 23000 = 6000
        assert captured["23"][0] == "6000"


# ===========================================================================
# Test: method_display format
# ===========================================================================

class TestMethodDisplay:
    """method_display should show 'MACRS 7yr' for default methods."""

    def test_200db_7yr_shows_macrs(self):
        from apps.returns.serializers import DepreciationAssetSerializer
        mock = MagicMock()
        mock.method = "200DB"
        mock.convention = "HY"
        mock.life = Decimal("7")
        mock.group_label = "Machinery and Equipment"
        mock.is_amortization = False
        ser = DepreciationAssetSerializer()
        assert ser.get_method_display(mock) == "MACRS 7yr"

    def test_sl_39yr_shows_macrs(self):
        from apps.returns.serializers import DepreciationAssetSerializer
        mock = MagicMock()
        mock.method = "SL"
        mock.convention = "MM"
        mock.life = Decimal("39")
        mock.group_label = "Buildings"
        mock.is_amortization = False
        ser = DepreciationAssetSerializer()
        assert ser.get_method_display(mock) == "MACRS 39yr"

    def test_sl_elected_shows_sl(self):
        from apps.returns.serializers import DepreciationAssetSerializer
        mock = MagicMock()
        mock.method = "SL"
        mock.convention = "HY"
        mock.life = Decimal("7")
        mock.group_label = "Machinery and Equipment"
        mock.is_amortization = False
        ser = DepreciationAssetSerializer()
        assert ser.get_method_display(mock) == "S/L 7yr"

    def test_150db_15yr_shows_macrs(self):
        from apps.returns.serializers import DepreciationAssetSerializer
        mock = MagicMock()
        mock.method = "150DB"
        mock.convention = "HY"
        mock.life = Decimal("15")
        mock.group_label = "Improvements"
        mock.is_amortization = False
        ser = DepreciationAssetSerializer()
        assert ser.get_method_display(mock) == "MACRS 15yr"

    def test_land_shows_dash(self):
        from apps.returns.serializers import DepreciationAssetSerializer
        mock = MagicMock()
        mock.method = "NONE"
        mock.group_label = "Land"
        mock.is_amortization = False
        ser = DepreciationAssetSerializer()
        assert ser.get_method_display(mock) == "\u2014"
