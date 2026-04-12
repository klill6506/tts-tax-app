"""
Tests for the 1040 Individual Income Tax Return skeleton.

Covers:
- Tax bracket calculator (multiple filing statuses)
- Compute pipeline (W-2 + interest → all line values)
- Edge cases (zero income, standard deduction > income)
"""

import pytest
from decimal import Decimal

from apps.returns.compute import compute_tax_from_brackets


# ---------------------------------------------------------------------------
# Bracket calculator tests
# ---------------------------------------------------------------------------


class TestBracketCalculator:
    """Test compute_tax_from_brackets() against hand-calculated values."""

    def test_single_50000(self):
        """Single filer, $50,000 taxable income.

        10% on $11,925 = $1,192.50
        12% on ($48,475 - $11,925) = $4,386.00
        22% on ($50,000 - $48,475) = $335.50
        Total = $5,914.00
        """
        tax = compute_tax_from_brackets(Decimal("50000"), "single", 2025)
        assert tax == Decimal("5914.00")

    def test_mfj_150000(self):
        """MFJ filer, $150,000 taxable income.

        10% on $23,850 = $2,385.00
        12% on ($96,950 - $23,850) = $8,772.00
        22% on ($150,000 - $96,950) = $11,671.00
        Total = $22,828.00
        """
        tax = compute_tax_from_brackets(Decimal("150000"), "mfj", 2025)
        assert tax == Decimal("22828.00")

    def test_hoh_75000(self):
        """HOH filer, $75,000 taxable income.

        10% on $17,000 = $1,700.00
        12% on ($64,850 - $17,000) = $5,742.00
        22% on ($75,000 - $64,850) = $2,233.00
        Total = $9,675.00
        """
        tax = compute_tax_from_brackets(Decimal("75000"), "hoh", 2025)
        assert tax == Decimal("9675.00")

    def test_mfs_200000(self):
        """MFS filer, $200,000 taxable income.

        10% on $11,925 = $1,192.50
        12% on ($48,475 - $11,925) = $4,386.00
        22% on ($103,350 - $48,475) = $12,072.50
        24% on ($197,300 - $103,350) = $22,548.00
        32% on ($200,000 - $197,300) = $864.00
        Total = $41,063.00
        """
        tax = compute_tax_from_brackets(Decimal("200000"), "mfs", 2025)
        assert tax == Decimal("41063.00")

    def test_qss_uses_mfj_brackets(self):
        """QSS uses MFJ brackets — same result."""
        mfj = compute_tax_from_brackets(Decimal("100000"), "mfj", 2025)
        qss = compute_tax_from_brackets(Decimal("100000"), "qss", 2025)
        assert mfj == qss

    def test_zero_income(self):
        """Zero taxable income → zero tax."""
        tax = compute_tax_from_brackets(Decimal("0"), "single", 2025)
        assert tax == Decimal("0")

    def test_negative_income(self):
        """Negative taxable income → zero tax."""
        tax = compute_tax_from_brackets(Decimal("-5000"), "single", 2025)
        assert tax == Decimal("0")

    def test_first_bracket_only(self):
        """Income entirely in 10% bracket (single)."""
        tax = compute_tax_from_brackets(Decimal("10000"), "single", 2025)
        assert tax == Decimal("1000.00")

    def test_high_income_37_bracket(self):
        """Single filer in 37% bracket, $700,000."""
        # 10%: 11,925 * 0.10 = 1,192.50
        # 12%: (48,475-11,925) * 0.12 = 4,386.00
        # 22%: (103,350-48,475) * 0.22 = 12,072.50
        # 24%: (197,300-103,350) * 0.24 = 22,548.00
        # 32%: (250,525-197,300) * 0.32 = 17,032.00
        # 35%: (626,350-250,525) * 0.35 = 131,538.75
        # 37%: (700,000-626,350) * 0.37 = 27,250.50
        # Total = 216,020.25
        tax = compute_tax_from_brackets(Decimal("700000"), "single", 2025)
        assert tax == Decimal("216020.25")


# ---------------------------------------------------------------------------
# Compute pipeline tests (require database)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCompute1040Pipeline:
    """Integration tests for the full 1040 compute pipeline."""

    def _create_1040_return(self):
        """Create a minimal 1040 return with seeded form definition."""
        from apps.clients.models import Client, Entity, EntityType
        from apps.firms.models import Firm
        from apps.clients.models import TaxYear
        from apps.returns.models import FormDefinition, TaxReturn

        # Ensure seed data exists
        from django.core.management import call_command
        call_command("seed_1040", "--year", "2025", verbosity=0)

        firm = Firm.objects.first()
        if not firm:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.first() or User.objects.create_user(
                username="test", password="test"
            )
            firm = Firm.objects.create(name="Test Firm")

        client = Client.objects.create(firm=firm, name="Test Individual")
        entity = Entity.objects.create(
            client=client,
            name="John Doe",
            entity_type=EntityType.INDIVIDUAL,
        )
        tax_year = TaxYear.objects.create(entity=entity, year=2025)
        form_def = FormDefinition.objects.get(code="1040", tax_year_applicable=2025)
        tax_return = TaxReturn.objects.create(
            tax_year=tax_year,
            form_definition=form_def,
        )
        return tax_return

    def test_two_w2s_and_interest(self):
        """Create a return with 2 W-2s and 1 interest, verify all lines."""
        from apps.returns.models import W2Income, InterestIncome, Taxpayer, FormFieldValue
        from apps.returns.compute import compute_return, aggregate_1040_income

        tr = self._create_1040_return()

        # Create taxpayer (single)
        Taxpayer.objects.create(
            tax_return=tr,
            filing_status="single",
            first_name="John",
            last_name="Doe",
            ssn="123-45-6789",
        )

        # Create 2 W-2s
        W2Income.objects.create(
            tax_return=tr,
            employer_name="Acme Corp",
            wages=Decimal("40000.00"),
            federal_tax_withheld=Decimal("5000.00"),
        )
        W2Income.objects.create(
            tax_return=tr,
            employer_name="Side Gig LLC",
            wages=Decimal("10000.00"),
            federal_tax_withheld=Decimal("1000.00"),
        )

        # Create 1 interest income
        InterestIncome.objects.create(
            tax_return=tr,
            payer_name="Big Bank",
            amount=Decimal("500.00"),
            is_tax_exempt=False,
        )

        # Run compute
        aggregate_1040_income(tr)
        compute_return(tr)

        def _fv(line):
            try:
                fv = FormFieldValue.objects.get(
                    tax_return=tr, form_line__line_number=line
                )
                return Decimal(fv.value) if fv.value else Decimal("0")
            except FormFieldValue.DoesNotExist:
                return None

        # Line 1a = 40000 + 10000 = 50000
        assert _fv("1a") == Decimal("50000.00")
        # Line 1z = 1a = 50000
        assert _fv("1z") == Decimal("50000.00")
        # Line 2b = 500 (taxable interest)
        assert _fv("2b") == Decimal("500.00")
        # Line 2a = 0 (no tax-exempt interest)
        assert _fv("2a") == Decimal("0.00")
        # Line 9 = 50000 + 500 = 50500
        assert _fv("9") == Decimal("50500.00")
        # Line 11 = AGI = 50500
        assert _fv("11") == Decimal("50500.00")
        # Line 12 = Standard deduction (single) = 15700
        assert _fv("12") == Decimal("15700.00")
        # Line 15 = 50500 - 15700 = 34800
        assert _fv("15") == Decimal("34800.00")
        # Line 16 = tax on 34800 (single)
        # 10% on 11925 = 1192.50
        # 12% on (34800-11925) = 2745.00
        # Total = 3937.50
        assert _fv("16") == Decimal("3937.50")
        # Line 25a = 5000 + 1000 = 6000
        assert _fv("25a") == Decimal("6000.00")
        # Line 33 = 6000
        assert _fv("33") == Decimal("6000.00")
        # Line 34 = overpayment = 6000 - 3937.50 = 2062.50
        assert _fv("34") == Decimal("2062.50")
        # Line 37 = 0 (overpaid)
        assert _fv("37") == Decimal("0.00")

    def test_zero_income_return(self):
        """Zero income return — no negative values anywhere."""
        from apps.returns.models import Taxpayer, FormFieldValue
        from apps.returns.compute import compute_return, aggregate_1040_income

        tr = self._create_1040_return()
        Taxpayer.objects.create(
            tax_return=tr,
            filing_status="single",
            first_name="Jane",
            last_name="Doe",
        )

        aggregate_1040_income(tr)
        compute_return(tr)

        def _fv(line):
            try:
                fv = FormFieldValue.objects.get(
                    tax_return=tr, form_line__line_number=line
                )
                return Decimal(fv.value) if fv.value else Decimal("0")
            except FormFieldValue.DoesNotExist:
                return None

        # All income/tax lines should be 0
        assert _fv("1a") == Decimal("0.00")
        assert _fv("9") == Decimal("0.00")
        assert _fv("15") == Decimal("0.00")  # max(0, AGI - std ded)
        assert _fv("16") == Decimal("0.00")
        assert _fv("34") == Decimal("0.00")  # max(0, payments - tax) = 0
        assert _fv("37") == Decimal("0.00")  # max(0, tax - payments) = 0

    def test_mfj_standard_deduction_exceeds_income(self):
        """MFJ std ded ($31,400) exceeds income ($20,000) — taxable income = 0."""
        from apps.returns.models import W2Income, Taxpayer, FormFieldValue
        from apps.returns.compute import compute_return, aggregate_1040_income

        tr = self._create_1040_return()
        Taxpayer.objects.create(
            tax_return=tr,
            filing_status="mfj",
            first_name="John",
            last_name="Doe",
        )
        W2Income.objects.create(
            tax_return=tr,
            employer_name="Small Co",
            wages=Decimal("20000.00"),
            federal_tax_withheld=Decimal("2000.00"),
        )

        aggregate_1040_income(tr)
        compute_return(tr)

        def _fv(line):
            try:
                fv = FormFieldValue.objects.get(
                    tax_return=tr, form_line__line_number=line
                )
                return Decimal(fv.value) if fv.value else Decimal("0")
            except FormFieldValue.DoesNotExist:
                return None

        assert _fv("11") == Decimal("20000.00")  # AGI
        assert _fv("12") == Decimal("31400.00")   # MFJ std ded
        assert _fv("15") == Decimal("0.00")        # Taxable = max(0, 20000-31400)
        assert _fv("16") == Decimal("0.00")        # Tax = 0
        assert _fv("34") == Decimal("2000.00")    # Refund = withholding - 0

    def test_standard_deduction_override(self):
        """Override standard deduction uses the custom value."""
        from apps.returns.models import W2Income, Taxpayer, FormFieldValue
        from apps.returns.compute import compute_return, aggregate_1040_income

        tr = self._create_1040_return()
        Taxpayer.objects.create(
            tax_return=tr,
            filing_status="single",
            first_name="Jane",
            last_name="Doe",
            standard_deduction_override=Decimal("20000.00"),
        )
        W2Income.objects.create(
            tax_return=tr,
            employer_name="Big Co",
            wages=Decimal("50000.00"),
            federal_tax_withheld=Decimal("5000.00"),
        )

        aggregate_1040_income(tr)
        compute_return(tr)

        def _fv(line):
            fv = FormFieldValue.objects.get(
                tax_return=tr, form_line__line_number=line
            )
            return Decimal(fv.value) if fv.value else Decimal("0")

        assert _fv("12") == Decimal("20000.00")  # Override value
        assert _fv("15") == Decimal("30000.00")  # 50000 - 20000
