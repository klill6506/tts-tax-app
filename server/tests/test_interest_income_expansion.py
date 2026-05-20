"""
Tests for the expanded InterestIncome model (1099-INT Boxes 2, 3, 4) and the
compute wiring in aggregate_1040_income().

Currently exercised:
- Box 3 (treasury_interest) is included in Line 2b alongside Box 1 amount.
- Box 8 (is_tax_exempt) routing to Line 2a is unaffected.

Box 2 (early_withdrawal_penalty → Schedule 1, Line 18) and Box 4
(federal_tax_withheld → Form 1040 Line 25b) are captured on the model but
not yet wired to form lines — the 1040 seed lacks Schedule 1 and Line 25b.
Those flows will get their own tests when the seed is expanded.
"""

from decimal import Decimal

import pytest


def _create_1040_return():
    """Create a minimal 1040 return with seeded form definition."""
    from django.core.management import call_command

    from apps.clients.models import Client, Entity, EntityType, TaxYear
    from apps.firms.models import Firm
    from apps.returns.models import FormDefinition, TaxReturn

    call_command("seed_1040", "--year", "2025", verbosity=0)

    firm = Firm.objects.first() or Firm.objects.create(name="Test Firm")
    client = Client.objects.create(firm=firm, name="Test Individual")
    entity = Entity.objects.create(
        client=client,
        name="Jane Doe",
        entity_type=EntityType.INDIVIDUAL,
    )
    tax_year = TaxYear.objects.create(entity=entity, year=2025)
    form_def = FormDefinition.objects.get(code="1040", tax_year_applicable=2025)
    return TaxReturn.objects.create(tax_year=tax_year, form_definition=form_def)


def _line_value(tax_return, line_number):
    from apps.returns.models import FormFieldValue

    try:
        fv = FormFieldValue.objects.get(
            tax_return=tax_return, form_line__line_number=line_number,
        )
    except FormFieldValue.DoesNotExist:
        return None
    return Decimal(fv.value) if fv.value else Decimal("0")


@pytest.mark.django_db
class TestBox3TreasuryInterestFlow:
    """Box 3 (treasury_interest) must be added to Line 2b alongside Box 1."""

    def test_treasury_interest_only_flows_to_2b(self):
        """A 1099-INT with only Box 3 populated still lands on Line 2b."""
        from apps.returns.compute import aggregate_1040_income, compute_return
        from apps.returns.models import InterestIncome, Taxpayer

        tr = _create_1040_return()
        Taxpayer.objects.create(
            tax_return=tr, filing_status="single",
            first_name="Treasury", last_name="Only",
        )
        InterestIncome.objects.create(
            tax_return=tr,
            payer_name="US Treasury",
            amount=Decimal("0.00"),
            treasury_interest=Decimal("750.00"),
            is_tax_exempt=False,
        )

        aggregate_1040_income(tr)
        compute_return(tr)

        assert _line_value(tr, "2b") == Decimal("750.00")
        assert _line_value(tr, "2a") == Decimal("0.00")

    def test_box1_plus_box3_sum_on_2b(self):
        """Box 1 amount + Box 3 treasury_interest both land on Line 2b."""
        from apps.returns.compute import aggregate_1040_income, compute_return
        from apps.returns.models import InterestIncome, Taxpayer

        tr = _create_1040_return()
        Taxpayer.objects.create(
            tax_return=tr, filing_status="single",
            first_name="Mixed", last_name="Interest",
        )
        InterestIncome.objects.create(
            tax_return=tr,
            payer_name="Big Bank",
            amount=Decimal("400.00"),
            treasury_interest=Decimal("250.00"),
            is_tax_exempt=False,
        )

        aggregate_1040_income(tr)
        compute_return(tr)

        # 400 (Box 1) + 250 (Box 3) = 650
        assert _line_value(tr, "2b") == Decimal("650.00")

    def test_multiple_payers_box1_and_box3_aggregate(self):
        """Box 1 + Box 3 across multiple payers all sum into Line 2b."""
        from apps.returns.compute import aggregate_1040_income, compute_return
        from apps.returns.models import InterestIncome, Taxpayer

        tr = _create_1040_return()
        Taxpayer.objects.create(
            tax_return=tr, filing_status="single",
            first_name="Multi", last_name="Payer",
        )
        InterestIncome.objects.create(
            tax_return=tr,
            payer_name="Bank A",
            amount=Decimal("100.00"),
            treasury_interest=Decimal("0.00"),
        )
        InterestIncome.objects.create(
            tax_return=tr,
            payer_name="Brokerage B",
            amount=Decimal("50.00"),
            treasury_interest=Decimal("200.00"),
        )
        InterestIncome.objects.create(
            tax_return=tr,
            payer_name="US Treasury Direct",
            amount=Decimal("0.00"),
            treasury_interest=Decimal("325.00"),
        )

        aggregate_1040_income(tr)
        compute_return(tr)

        # (100 + 0) + (50 + 200) + (0 + 325) = 675
        assert _line_value(tr, "2b") == Decimal("675.00")

    def test_tax_exempt_excludes_treasury_interest_from_2b(self):
        """A row flagged tax-exempt is excluded from Line 2b entirely
        (its Box 3 value is not silently added to taxable interest)."""
        from apps.returns.compute import aggregate_1040_income, compute_return
        from apps.returns.models import InterestIncome, Taxpayer

        tr = _create_1040_return()
        Taxpayer.objects.create(
            tax_return=tr, filing_status="single",
            first_name="Exempt", last_name="Row",
        )
        # Tax-exempt row with Box 1 = 800 → Line 2a
        InterestIncome.objects.create(
            tax_return=tr,
            payer_name="Muni Fund",
            amount=Decimal("800.00"),
            treasury_interest=Decimal("0.00"),
            is_tax_exempt=True,
        )
        # Taxable row with Box 1 = 100 + Box 3 = 50 → Line 2b
        InterestIncome.objects.create(
            tax_return=tr,
            payer_name="Bank",
            amount=Decimal("100.00"),
            treasury_interest=Decimal("50.00"),
            is_tax_exempt=False,
        )

        aggregate_1040_income(tr)
        compute_return(tr)

        assert _line_value(tr, "2a") == Decimal("800.00")
        assert _line_value(tr, "2b") == Decimal("150.00")
