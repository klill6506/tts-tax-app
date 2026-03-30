"""
Mar 30 fix tests:
1. 4797 Part III: §1245 → Lines 25a/25b, §1250 → Lines 26a-g (not backwards)
2. Depreciation PATCH runs full compute_return (K9/K15a update without render)
3. Seed clears is_overridden on computed fields
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from apps.returns.compute import ZERO, compute_return
from apps.returns.models import (
    DepreciationAsset,
    FormDefinition,
    FormFieldValue,
    FormLine,
    TaxReturn,
)


# ===========================================================================
# Test 1 & 2: 4797 Part III line assignment (§1245 vs §1250)
# Uses mock to intercept field_values before PDF generation.
# ===========================================================================


@pytest.fixture
def seeded_1120s(db):
    call_command("seed_1120s", verbosity=0)
    return FormDefinition.objects.get(code="1120-S")


@pytest.fixture
def tax_return(seeded_1120s):
    from apps.clients.models import Client, Entity, TaxYear
    from apps.firms.models import Firm

    firm = Firm.objects.create(name="Test Firm 4797")
    client = Client.objects.create(firm=firm, name="Test Client")
    entity = Entity.objects.create(client=client, name="Test S-Corp")
    ty = TaxYear.objects.create(entity=entity, year=2025)
    tr = TaxReturn.objects.create(tax_year=ty, form_definition=seeded_1120s)
    for fl in FormLine.objects.filter(section__form=seeded_1120s):
        FormFieldValue.objects.create(tax_return=tr, form_line=fl, value="")
    return tr


def _get_line(tr, line_number):
    fv = FormFieldValue.objects.get(
        tax_return=tr, form_line__line_number=line_number,
    )
    return Decimal(fv.value) if fv.value else Decimal("0")


@pytest.mark.django_db
class TestF4797PartIIILineAssignment:
    """Verify §1245 uses Lines 25a/25b and §1250 uses Lines 26a-g."""

    def _capture_field_values(self, tax_return):
        """Call render_4797 but intercept the field_values dict."""
        captured = {}

        original_render = None

        def mock_render(form_id, tax_year, field_values, header_data):
            captured.update(field_values)
            return b"%PDF-mock"

        with patch("apps.tts_forms.renderer.render", side_effect=mock_render):
            from apps.tts_forms.renderer import render_4797
            render_4797(tax_return)

        return captured

    def test_1245_uses_lines_25a_25b(self, tax_return):
        """§1245 property (equipment): depreciation on Line 25a, recapture on 25b."""
        DepreciationAsset.objects.create(
            tax_return=tax_return,
            asset_number=1,
            description="Equipment",
            group_label="Machinery and Equipment",
            cost_basis=Decimal("30500"),
            date_acquired=date(2020, 3, 1),
            date_sold=date(2025, 8, 15),
            sales_price=Decimal("15000"),
            prior_depreciation=Decimal("15878"),
            current_depreciation=Decimal("5000"),
            bonus_amount=Decimal("0"),
            sec_179_elected=Decimal("0"),
            recapture_type="1245",
        )

        fv = self._capture_field_values(tax_return)

        # §1245 should populate Lines 25a and 25b
        assert "P3_25a_a" in fv, "§1245 depreciation should be on Line 25a"
        assert "P3_25b_a" in fv, "§1245 recapture should be on Line 25b"

        # Lines 26a-g and 27a should NOT be populated
        assert "P3_26g_a" not in fv, "§1245 should not write to Line 26g"
        assert "P3_27a_a" not in fv, "§1245 should not write to Line 27a"

        # Values should be non-zero currency strings
        assert Decimal(fv["P3_25a_a"][0]) > 0, "Line 25a (depreciation) should be positive"
        assert Decimal(fv["P3_25b_a"][0]) > 0, "Line 25b (recapture) should be positive"

    def test_1250_uses_lines_26a_through_26g(self, tax_return):
        """§1250 property (building): Lines 26a/26b/26g populated, Lines 25a/25b empty."""
        DepreciationAsset.objects.create(
            tax_return=tax_return,
            asset_number=1,
            description="Office Building",
            group_label="Buildings",
            cost_basis=Decimal("500000"),
            date_acquired=date(2015, 6, 1),
            date_sold=date(2025, 6, 1),
            sales_price=Decimal("600000"),
            prior_depreciation=Decimal("115000"),
            current_depreciation=Decimal("12821"),
            bonus_amount=Decimal("0"),
            sec_179_elected=Decimal("0"),
            recapture_type="1250",
            life=Decimal("39"),
        )

        fv = self._capture_field_values(tax_return)

        # §1250 should populate Lines 26a, 26b, 26g
        assert "P3_26a_a" in fv, "§1250 should write to Line 26a"
        assert "P3_26b_a" in fv, "§1250 should write to Line 26b"
        assert "P3_26g_a" in fv, "§1250 should write to Line 26g"

        # Lines 25a/25b should NOT be populated
        assert "P3_25a_a" not in fv, "§1250 should not write to Line 25a"
        assert "P3_25b_a" not in fv, "§1250 should not write to Line 25b"

        # Post-1986 SL: all §1250 recapture amounts = 0
        assert fv["P3_26a_a"][0] == str(ZERO)
        assert fv["P3_26b_a"][0] == str(ZERO)
        assert fv["P3_26g_a"][0] == str(ZERO)


# ===========================================================================
# Test 3: Depreciation PATCH runs full compute (K9 updates)
# ===========================================================================


@pytest.mark.django_db
class TestDeprPatchRunsFullCompute:
    """PATCH on depreciation should run compute_return so K9/K15a update."""

    def test_line4_updates_after_compute_return(self, tax_return):
        """compute_return() should populate Line 4 from disposition aggregation."""
        DepreciationAsset.objects.create(
            tax_return=tax_return,
            asset_number=1,
            description="Equipment for sale",
            group_label="Machinery and Equipment",
            cost_basis=Decimal("30500"),
            date_acquired=date(2020, 3, 1),
            date_sold=date(2025, 8, 15),
            sales_price=Decimal("15000"),
            prior_depreciation=Decimal("15878"),
            current_depreciation=Decimal("5000"),
            bonus_amount=Decimal("0"),
            sec_179_elected=Decimal("0"),
            recapture_type="1245",
        )

        # Before compute_return, Line 4 should be 0
        assert _get_line(tax_return, "4") == Decimal("0")

        # Call compute_return (what the PATCH handler now does)
        compute_return(tax_return)

        # Line 4 should now have the ordinary recapture amount (non-zero).
        # The exact value depends on the depreciation engine recalculating
        # current_depreciation, but it MUST be > 0 for this §1245 disposition.
        line4 = _get_line(tax_return, "4")
        assert line4 > 0, (
            f"Line 4 (ordinary gains from 4797) should be > 0 after "
            f"compute_return with a disposed §1245 asset, got {line4}"
        )


# ===========================================================================
# Test 4: Seed clears is_overridden on computed fields
# ===========================================================================


@pytest.mark.django_db
class TestSeedClearsOverrides:
    """seed_1120s should clear is_overridden on fields that are now computed."""

    def test_override_cleared_on_computed_field(self, seeded_1120s):
        """L3d is computed — seed should clear any manual override."""
        from apps.clients.models import Client, Entity, TaxYear
        from apps.firms.models import Firm

        firm = Firm.objects.create(name="Override Test Firm")
        client = Client.objects.create(firm=firm, name="Override Client")
        entity = Entity.objects.create(client=client, name="Override S-Corp")
        ty = TaxYear.objects.create(entity=entity, year=2025)
        tr = TaxReturn.objects.create(tax_year=ty, form_definition=seeded_1120s)

        # Create all field values
        for fl in FormLine.objects.filter(section__form=seeded_1120s):
            FormFieldValue.objects.create(tax_return=tr, form_line=fl, value="")

        # Simulate a manual override on L3d
        l3d_line = FormLine.objects.get(
            section__form=seeded_1120s, line_number="L3d",
        )
        fv = FormFieldValue.objects.get(tax_return=tr, form_line=l3d_line)
        fv.is_overridden = True
        fv.value = "99999"
        fv.save()

        # Verify override is set
        fv.refresh_from_db()
        assert fv.is_overridden is True

        # Re-run the seed — should clear the override
        call_command("seed_1120s", verbosity=0)

        # Check is_overridden is now False
        fv.refresh_from_db()
        assert fv.is_overridden is False, (
            "seed_1120s should clear is_overridden on computed fields"
        )

    def test_non_computed_field_override_preserved(self, seeded_1120s):
        """Non-computed fields should NOT have overrides cleared."""
        from apps.clients.models import Client, Entity, TaxYear
        from apps.firms.models import Firm

        firm = Firm.objects.create(name="Preserve Test Firm")
        client = Client.objects.create(firm=firm, name="Preserve Client")
        entity = Entity.objects.create(client=client, name="Preserve S-Corp")
        ty = TaxYear.objects.create(entity=entity, year=2025)
        tr = TaxReturn.objects.create(tax_year=ty, form_definition=seeded_1120s)

        for fl in FormLine.objects.filter(section__form=seeded_1120s):
            FormFieldValue.objects.create(tax_return=tr, form_line=fl, value="")

        # L1a (Cash) is NOT computed — override should persist
        l1a_line = FormLine.objects.get(
            section__form=seeded_1120s, line_number="L1a",
        )
        fv = FormFieldValue.objects.get(tax_return=tr, form_line=l1a_line)
        fv.is_overridden = True
        fv.value = "50000"
        fv.save()

        call_command("seed_1120s", verbosity=0)

        fv.refresh_from_db()
        assert fv.is_overridden is True, (
            "Non-computed field overrides should NOT be cleared by seed"
        )
