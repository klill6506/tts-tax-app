"""
Schedule L Auto-Computation + AMT to K15a Tests.

Tests:
1. Formula-level: L15a/L15d sum asset lines correctly (no DB)
2. compute_schedule_l(): EOY values from depreciation worksheet (DB)
3. AMT adjustment flows to K15a (DB)
4. SCHED_L_DEPR_TIE diagnostic fires when values don't tie (DB)
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.returns.compute import (
    FORMULAS_1120S,
    ZERO,
    _d,
    aggregate_depreciation,
    compute_return,
    compute_schedule_l,
)
from apps.returns.models import (
    DepreciationAsset,
    FormDefinition,
    FormFieldValue,
    FormLine,
    FormSection,
    TaxReturn,
)


def _run_formulas(inputs: dict[str, Decimal]) -> dict[str, Decimal]:
    """Run FORMULAS_1120S against a values dict and return final values."""
    values = {k: Decimal(str(v)) for k, v in inputs.items()}
    for line_number, formula_fn in FORMULAS_1120S:
        values[line_number] = formula_fn(values).quantize(Decimal("1"))
    return values


# ===========================================================================
# Pure Formula Tests (no DB)
# ===========================================================================

class TestScheduleLFormulas:
    """Schedule L total formulas in FORMULAS_1120S."""

    def test_l15a_total_assets_boy(self):
        """L15a = sum of BOY asset lines with contra netting."""
        vals = _run_formulas({
            "L1a": 10000,   # Cash
            "L2a": 5000,    # Receivables gross
            "L2b": 500,     # Less allowance
            "L10a": 100000, # Depreciable assets
            "L10b": 30000,  # Less accum depr
            "L12a": 25000,  # Land
            "L13a": 50000,  # Intangibles
            "L13b": 10000,  # Less accum amort
        })
        # 10000 + (5000-500) + 0 + 0 + 0 + 0 + 0 + 0 + 25000 + 0
        # + (100000-30000) + (0-0) + (50000-10000)
        assert vals["L15a"] == 149500

    def test_l15d_total_assets_eoy(self):
        """L15d = sum of EOY asset lines with contra netting."""
        vals = _run_formulas({
            "L1d": 15000,
            "L10d": 120000,
            "L10e": 45000,
            "L12d": 25000,
            "L13d": 50000,
            "L13e": 15000,
        })
        # 15000 + (120000-45000) + 25000 + (50000-15000)
        assert vals["L15d"] == 150000

    def test_l27a_total_liabilities_boy(self):
        """L27a = sum of BOY liability + equity lines less treasury stock."""
        vals = _run_formulas({
            "L16a": 5000,   # AP
            "L22a": 1000,   # Capital stock
            "L24a": 50000,  # Retained earnings
            "L26a": 0,      # Less treasury stock
        })
        assert vals["L27a"] == 56000

    def test_l27d_total_liabilities_eoy(self):
        """L27d = sum of EOY liability + equity lines."""
        vals = _run_formulas({
            "L16d": 5000,
            "L22d": 1000,
            # M2_8a/8b/8c/8d feed L24d via M-2 formulas
            "M2_1a": 40000,
            # K1 is computed from Line 21, so set upstream inputs
            "1a": 100000,       # → 1c = 100000
            "7": 40000, "8": 10000, "14": 5000,
            # → Line 20 = 55000, Line 21 = 100000 - 55000 = 45000
            # → K1 = 45000 → M2_2a = 45000
            # → M2_6a = 40000 + 45000 = 85000
            # → M2_8a = 85000 - 0 = 85000
        })
        assert vals["L24d"] == 85000
        assert vals["L27d"] == 91000  # 5000 + 1000 + 85000


# ===========================================================================
# DB-Backed Tests: compute_schedule_l()
# ===========================================================================

@pytest.fixture
def seeded_1120s(db):
    call_command("seed_1120s", verbosity=0)
    return FormDefinition.objects.get(code="1120-S")


@pytest.fixture
def tax_return(seeded_1120s):
    from apps.clients.models import Client, Entity, TaxYear
    from apps.firms.models import Firm

    firm = Firm.objects.create(name="Test Firm")
    client = Client.objects.create(firm=firm, name="Test Client")
    entity = Entity.objects.create(client=client, name="Test S-Corp")
    ty = TaxYear.objects.create(entity=entity, year=2025)
    tr = TaxReturn.objects.create(tax_year=ty, form_definition=seeded_1120s)
    # Create all FormFieldValues
    for fl in FormLine.objects.filter(section__form=seeded_1120s):
        FormFieldValue.objects.create(tax_return=tr, form_line=fl, value="")
    return tr


def _set_line(tr, line_number, value):
    """Helper to set a FormFieldValue."""
    fv = FormFieldValue.objects.get(
        tax_return=tr, form_line__line_number=line_number,
    )
    fv.value = str(value)
    fv.save(update_fields=["value"])


def _get_line(tr, line_number):
    """Helper to read a FormFieldValue."""
    fv = FormFieldValue.objects.get(
        tax_return=tr, form_line__line_number=line_number,
    )
    return Decimal(fv.value) if fv.value else Decimal("0")


@pytest.mark.django_db
class TestComputeScheduleL:
    """compute_schedule_l() auto-computes EOY balances from depreciation."""

    def test_basic_depreciable_assets(self, tax_return):
        """EOY = BOY + additions - dispositions."""
        _set_line(tax_return, "L10a", "100000")  # BOY gross
        _set_line(tax_return, "L10b", "30000")   # BOY accum depr

        # One existing asset (not acquired this year)
        DepreciationAsset.objects.create(
            tax_return=tax_return,
            asset_number=1,
            description="Existing equipment",
            group_label="Machinery and Equipment",
            cost_basis=Decimal("100000"),
            date_acquired=date(2023, 6, 1),
            prior_depreciation=Decimal("30000"),
            current_depreciation=Decimal("20000"),
        )
        # One new asset acquired this year
        DepreciationAsset.objects.create(
            tax_return=tax_return,
            asset_number=2,
            description="New equipment",
            group_label="Machinery and Equipment",
            cost_basis=Decimal("50000"),
            date_acquired=date(2025, 3, 15),
            prior_depreciation=Decimal("0"),
            current_depreciation=Decimal("10000"),
        )

        compute_schedule_l(tax_return)

        # L10d EOY gross = 100000 + 50000 (addition) = 150000
        assert _get_line(tax_return, "L10d") == 150000
        # L10e EOY accum depr = 30000 + 20000 + 10000 = 60000
        assert _get_line(tax_return, "L10e") == 60000

    def test_disposed_asset(self, tax_return):
        """Disposed assets reduce EOY cost and accum depr."""
        _set_line(tax_return, "L10a", "200000")  # BOY gross
        _set_line(tax_return, "L10b", "80000")   # BOY accum depr

        # Continuing asset
        DepreciationAsset.objects.create(
            tax_return=tax_return,
            asset_number=1,
            description="Kept equipment",
            group_label="Machinery and Equipment",
            cost_basis=Decimal("150000"),
            date_acquired=date(2020, 1, 1),
            prior_depreciation=Decimal("60000"),
            current_depreciation=Decimal("30000"),
        )
        # Disposed asset
        DepreciationAsset.objects.create(
            tax_return=tax_return,
            asset_number=2,
            description="Sold truck",
            group_label="Vehicles",
            cost_basis=Decimal("50000"),
            date_acquired=date(2021, 3, 1),
            date_sold=date(2025, 8, 1),
            prior_depreciation=Decimal("20000"),
            current_depreciation=Decimal("5000"),
        )

        compute_schedule_l(tax_return)

        # L10d = 200000 - 50000 (disposal cost) = 150000
        assert _get_line(tax_return, "L10d") == 150000
        # L10e = 80000 + 30000 + 5000 (current) - 25000 (disposed accum: 20000+5000) = 90000
        assert _get_line(tax_return, "L10e") == 90000

    def test_amortizable_assets(self, tax_return):
        """Intangibles flow to L13d/L13e, not L10d/L10e."""
        _set_line(tax_return, "L13a", "180000")  # BOY intangibles gross
        _set_line(tax_return, "L13b", "30000")   # BOY accum amort

        DepreciationAsset.objects.create(
            tax_return=tax_return,
            asset_number=1,
            description="Goodwill",
            group_label="Intangibles/Amortization",
            is_amortization=True,
            cost_basis=Decimal("180000"),
            date_acquired=date(2022, 1, 1),
            prior_depreciation=Decimal("30000"),
            current_depreciation=Decimal("12000"),
        )

        compute_schedule_l(tax_return)

        # L13d = 180000 (no additions/dispositions)
        assert _get_line(tax_return, "L13d") == 180000
        # L13e = 30000 + 12000 = 42000
        assert _get_line(tax_return, "L13e") == 42000
        # L10d/L10e should remain at 0 (no depreciable assets)
        assert _get_line(tax_return, "L10d") == 0
        assert _get_line(tax_return, "L10e") == 0

    def test_land_excluded(self, tax_return):
        """Land assets don't affect depreciation lines."""
        _set_line(tax_return, "L10a", "0")
        _set_line(tax_return, "L10b", "0")

        DepreciationAsset.objects.create(
            tax_return=tax_return,
            asset_number=1,
            description="Lot",
            group_label="Land",
            cost_basis=Decimal("75000"),
            date_acquired=date(2025, 1, 15),
        )

        compute_schedule_l(tax_return)

        assert _get_line(tax_return, "L10d") == 0
        assert _get_line(tax_return, "L10e") == 0

    def test_mixed_assets(self, tax_return):
        """Depreciable + amortizable + land — each routes correctly."""
        _set_line(tax_return, "L10a", "50000")
        _set_line(tax_return, "L10b", "10000")
        _set_line(tax_return, "L13a", "90000")
        _set_line(tax_return, "L13b", "15000")

        # Depreciable
        DepreciationAsset.objects.create(
            tax_return=tax_return, asset_number=1,
            description="Equipment", group_label="Machinery and Equipment",
            cost_basis=Decimal("50000"), date_acquired=date(2024, 1, 1),
            prior_depreciation=Decimal("10000"), current_depreciation=Decimal("10000"),
        )
        # Amortizable
        DepreciationAsset.objects.create(
            tax_return=tax_return, asset_number=2,
            description="Covenant", group_label="Intangibles/Amortization",
            is_amortization=True,
            cost_basis=Decimal("90000"), date_acquired=date(2023, 1, 1),
            prior_depreciation=Decimal("15000"), current_depreciation=Decimal("6000"),
        )
        # Land (ignored)
        DepreciationAsset.objects.create(
            tax_return=tax_return, asset_number=3,
            description="Parking lot", group_label="Land",
            cost_basis=Decimal("30000"), date_acquired=date(2025, 6, 1),
        )

        compute_schedule_l(tax_return)

        assert _get_line(tax_return, "L10d") == 50000   # No additions this year
        assert _get_line(tax_return, "L10e") == 20000    # 10000 + 10000
        assert _get_line(tax_return, "L13d") == 90000    # No additions this year
        assert _get_line(tax_return, "L13e") == 21000    # 15000 + 6000

    def test_no_assets_noop(self, tax_return):
        """No depreciation assets — function returns without touching values."""
        _set_line(tax_return, "L10d", "999")

        compute_schedule_l(tax_return)

        # Should not have been modified
        assert _get_line(tax_return, "L10d") == 999


# ===========================================================================
# DB-Backed Tests: AMT to K15a
# ===========================================================================

@pytest.mark.django_db
class TestAMTToK15a:
    """AMT depreciation adjustment should save to K15a."""

    def test_amt_adjustment_saved(self, tax_return):
        """When AMT differs from regular, K15a gets the adjustment."""
        from unittest.mock import patch

        DepreciationAsset.objects.create(
            tax_return=tax_return,
            asset_number=1,
            description="Pre-2018 equipment",
            group_label="Machinery and Equipment",
            cost_basis=Decimal("100000"),
            date_acquired=date(2017, 3, 1),
            prior_depreciation=Decimal("60000"),
            flow_to="page1",
        )

        # Mock the engine to return known AMT vs regular difference
        mock_result = {
            "current_depreciation": Decimal("15000"),
            "bonus_amount": Decimal("0"),
            "amt_current_depreciation": Decimal("12000"),
            "state_current_depreciation": Decimal("15000"),
            "state_bonus_disallowed": Decimal("0"),
        }
        with patch(
            "apps.tts_forms.depreciation_engine.calculate_asset_depreciation",
            return_value=mock_result,
        ):
            aggregate_depreciation(tax_return)

        # K15a = current_depr - amt_current_depr = 15000 - 12000 = 3000
        assert _get_line(tax_return, "K15a") == 3000

    def test_amt_zero_when_equal(self, tax_return):
        """Post-2017 TCJA assets: amt == regular, no adjustment."""
        from unittest.mock import patch

        DepreciationAsset.objects.create(
            tax_return=tax_return,
            asset_number=1,
            description="New equipment",
            group_label="Machinery and Equipment",
            cost_basis=Decimal("50000"),
            date_acquired=date(2025, 1, 15),
            prior_depreciation=Decimal("0"),
            flow_to="page1",
        )

        # AMT equals regular — no adjustment
        mock_result = {
            "current_depreciation": Decimal("50000"),
            "bonus_amount": Decimal("50000"),
            "amt_current_depreciation": Decimal("50000"),
            "state_current_depreciation": Decimal("50000"),
            "state_bonus_disallowed": Decimal("0"),
        }
        with patch(
            "apps.tts_forms.depreciation_engine.calculate_asset_depreciation",
            return_value=mock_result,
        ):
            aggregate_depreciation(tax_return)

        # No adjustment — K15a should remain 0
        assert _get_line(tax_return, "K15a") == 0


# ===========================================================================
# DB-Backed Tests: SCHED_L_DEPR_TIE Diagnostic
# ===========================================================================

@pytest.mark.django_db
class TestSchedLDeprTieDiagnostic:
    """SCHED_L_DEPR_TIE diagnostic fires when worksheet doesn't tie."""

    def test_passes_when_tied(self, tax_return):
        """No findings when L10d matches continuing assets."""
        from apps.diagnostics.rules import sched_l_depr_tie_check

        DepreciationAsset.objects.create(
            tax_return=tax_return, asset_number=1,
            description="Equipment", group_label="Machinery and Equipment",
            cost_basis=Decimal("50000"), date_acquired=date(2023, 1, 1),
            prior_depreciation=Decimal("20000"),
            current_depreciation=Decimal("10000"),
        )
        # Set L10d/L10e to match what the worksheet expects
        # Continuing asset: cost=50000, accum=30000
        _set_line(tax_return, "L10d", "50000")
        _set_line(tax_return, "L10e", "30000")

        findings = sched_l_depr_tie_check(tax_return.tax_year)
        assert len(findings) == 0

    def test_fires_when_mismatched(self, tax_return):
        """Findings when L10d doesn't match worksheet."""
        from apps.diagnostics.rules import sched_l_depr_tie_check

        DepreciationAsset.objects.create(
            tax_return=tax_return, asset_number=1,
            description="Equipment", group_label="Machinery and Equipment",
            cost_basis=Decimal("50000"), date_acquired=date(2023, 1, 1),
            prior_depreciation=Decimal("20000"),
            current_depreciation=Decimal("10000"),
        )
        # Set L10d to wrong value
        _set_line(tax_return, "L10d", "99999")

        findings = sched_l_depr_tie_check(tax_return.tax_year)
        assert len(findings) >= 1
        assert "10a EOY" in findings[0]["message"]

    def test_skips_when_no_assets(self, tax_return):
        """No findings when no depreciation assets exist."""
        from apps.diagnostics.rules import sched_l_depr_tie_check

        findings = sched_l_depr_tie_check(tax_return.tax_year)
        assert len(findings) == 0
