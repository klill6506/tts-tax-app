"""
Tests for Form 7203 computation engine.

Tests cover:
    - Part I: Stock basis calculation (income, distributions, non-deductibles)
    - Part II: Debt basis per-loan tracking
    - Part III: Loss limitation with pro-rata allocation
    - Edge cases: zero basis, no losses, all losses suspended
"""

from decimal import Decimal

import pytest

from apps.returns.management.commands.seed_1120s import Command as SeedCommand
from apps.returns.models import FormDefinition
from apps.tts_forms.compute_7203 import (
    ZERO,
    _prorate,
    _prorate_negative_as_positive,
    _prorate_positive,
    compute_7203,
)

TWO_PLACES = Decimal("0.01")


@pytest.fixture
def seeded(db):
    """Seed 1120-S form definition so FormLines exist."""
    cmd = SeedCommand()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="1120-S")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestProrate:
    def test_prorate_basic(self):
        assert _prorate(Decimal("100000"), Decimal("0.50")) == Decimal("50000.00")

    def test_prorate_zero(self):
        assert _prorate(ZERO, Decimal("0.50")) == ZERO

    def test_prorate_rounding(self):
        result = _prorate(Decimal("100"), Decimal("0.3333"))
        assert result == Decimal("33.33")

    def test_prorate_positive_with_positive(self):
        assert _prorate_positive(Decimal("100000"), Decimal("0.50")) == Decimal("50000.00")

    def test_prorate_positive_with_negative(self):
        assert _prorate_positive(Decimal("-50000"), Decimal("0.50")) == ZERO

    def test_prorate_positive_with_zero(self):
        assert _prorate_positive(ZERO, Decimal("0.50")) == ZERO

    def test_prorate_negative_as_positive_with_loss(self):
        assert _prorate_negative_as_positive(Decimal("-60000"), Decimal("0.50")) == Decimal("30000.00")

    def test_prorate_negative_as_positive_with_income(self):
        assert _prorate_negative_as_positive(Decimal("60000"), Decimal("0.50")) == ZERO


# ---------------------------------------------------------------------------
# Part I: Shareholder Stock Basis
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCompute7203PartI:
    """Tests for Part I stock basis computation."""

    @pytest.fixture
    def firm_and_return(self, seeded):
        """Create a firm, entity, tax year, form definition, and tax return."""
        from apps.clients.models import Client, Entity, TaxYear
        from apps.firms.models import Firm
        from apps.returns.models import TaxReturn

        firm = Firm.objects.create(name="Test Firm")
        client = Client.objects.create(firm=firm, name="Test Client")
        entity = Entity.objects.create(
            client=client, name="Test S-Corp", entity_type="scorp",
            ein="12-3456789",
        )
        ty = TaxYear.objects.create(entity=entity, year=2025)
        tr = TaxReturn.objects.create(
            tax_year=ty, form_definition=seeded, status="draft",
        )
        return firm, tr

    @pytest.fixture
    def shareholder(self, firm_and_return):
        """Create a shareholder with 50% ownership."""
        from apps.returns.models import Shareholder

        _, tr = firm_and_return
        return Shareholder.objects.create(
            tax_return=tr,
            name="Alice Smith",
            ssn="111-22-3333",
            ownership_percentage=Decimal("50.0000"),
            stock_basis_boy=Decimal("50000"),
            capital_contributions=Decimal("10000"),
            distributions=Decimal("20000"),
        )

    def _set_k_value(self, tax_return, line_number, value):
        """Set a Schedule K form field value."""
        from apps.returns.models import FormFieldValue, FormLine

        fl = FormLine.objects.filter(
            section__form=tax_return.form_definition,
            line_number=line_number,
        ).first()
        if fl:
            FormFieldValue.objects.update_or_create(
                tax_return=tax_return,
                form_line=fl,
                defaults={"value": str(value)},
            )

    def test_simple_stock_basis_no_k_data(self, firm_and_return, shareholder):
        """Basis with no K-1 data: BOY + contributions - distributions."""
        _, tr = firm_and_return
        result = compute_7203(tr, shareholder)

        assert result["1"] == Decimal("50000")    # BOY
        assert result["2"] == Decimal("10000")    # Contributions
        assert result["4"] == ZERO                 # No income
        assert result["5"] == Decimal("60000")    # 50k + 10k + 0
        assert result["6"] == Decimal("20000")    # Distributions
        assert result["7"] == Decimal("40000")    # 60k - 20k
        assert result["15"] == Decimal("40000")   # No losses

    def test_income_increases_basis(self, firm_and_return, shareholder):
        """K-1 ordinary income at 50% ownership increases basis."""
        _, tr = firm_and_return
        self._set_k_value(tr, "K1", "100000")  # 100k ordinary income

        result = compute_7203(tr, shareholder)

        assert result["3a"] == Decimal("50000.00")  # 100k * 50%
        assert result["4"] == Decimal("50000.00")
        assert result["5"] == Decimal("110000.00")  # 50k + 10k + 50k

    def test_distributions_reduce_basis(self, firm_and_return, shareholder):
        """Distributions reduce stock basis but not below zero."""
        _, tr = firm_and_return
        # Override distributions to exceed basis
        shareholder.distributions = Decimal("75000")
        shareholder.save()

        result = compute_7203(tr, shareholder)

        assert result["5"] == Decimal("60000")    # 50k + 10k
        assert result["6"] == Decimal("75000")
        assert result["7"] == ZERO                 # max(0, 60k - 75k)

    def test_nondeductible_expenses_from_k16c(self, firm_and_return, shareholder):
        """Line 8a: K16c * ownership %."""
        _, tr = firm_and_return
        self._set_k_value(tr, "K16c", "10000")  # 10k nondeductible

        result = compute_7203(tr, shareholder)

        assert result["8a"] == Decimal("5000.00")  # 10k * 50%
        assert result["9"] == Decimal("5000.00")
        # Line 10 = 7 - 9 = 40k - 5k
        assert result["10"] == Decimal("35000.00")

    def test_tax_exempt_income(self, firm_and_return, shareholder):
        """Line 3k: K16a + K16b combined."""
        _, tr = firm_and_return
        self._set_k_value(tr, "K16a", "5000")
        self._set_k_value(tr, "K16b", "3000")

        result = compute_7203(tr, shareholder)

        assert result["3k"] == Decimal("4000.00")  # (5k + 3k) * 50%

    def test_losses_appear_in_part_iii_not_part_i(self, firm_and_return, shareholder):
        """K-1 losses go to Part III, not to Part I income lines."""
        _, tr = firm_and_return
        self._set_k_value(tr, "K1", "-60000")  # 60k ordinary loss

        result = compute_7203(tr, shareholder)

        # Income line 3a should be zero (loss goes to Part III)
        assert result["3a"] == ZERO
        # Part III line 35a should have the loss
        assert result["35a"] == Decimal("30000.00")  # 60k * 50%

    def test_ending_basis_cannot_be_negative(self, firm_and_return, shareholder):
        """Line 15 floors at zero."""
        _, tr = firm_and_return
        shareholder.stock_basis_boy = Decimal("0")
        shareholder.capital_contributions = Decimal("0")
        shareholder.distributions = Decimal("0")
        shareholder.save()

        result = compute_7203(tr, shareholder)

        assert result["15"] >= ZERO


# ---------------------------------------------------------------------------
# Part II: Shareholder Debt Basis
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCompute7203PartII:
    """Tests for Part II debt basis computation."""

    @pytest.fixture
    def shareholder_with_loan(self, seeded):
        """Create shareholder with one loan."""
        from apps.clients.models import Client, Entity, TaxYear
        from apps.firms.models import Firm
        from apps.returns.models import (
            Shareholder,
            ShareholderLoan,
            TaxReturn,
        )

        firm = Firm.objects.create(name="Test Firm II")
        client = Client.objects.create(firm=firm, name="Client II")
        entity = Entity.objects.create(
            client=client, name="Corp II", entity_type="scorp",
            ein="98-7654321",
        )
        ty = TaxYear.objects.create(entity=entity, year=2025)
        tr = TaxReturn.objects.create(
            tax_year=ty, form_definition=seeded, status="draft",
        )
        sh = Shareholder.objects.create(
            tax_return=tr,
            name="Bob Jones",
            ownership_percentage=Decimal("100.0000"),
            stock_basis_boy=Decimal("100000"),
        )
        loan = ShareholderLoan.objects.create(
            shareholder=sh,
            description="Operating line of credit",
            loan_balance_boy=Decimal("50000"),
            additional_loans=Decimal("10000"),
            loan_repayments=Decimal("15000"),
            debt_basis_boy=Decimal("50000"),
            new_loans_increasing_basis=Decimal("10000"),
        )
        return tr, sh, loan

    def test_single_loan_balances(self, shareholder_with_loan):
        """Lines 16-20: loan balance computation."""
        tr, sh, loan = shareholder_with_loan
        result = compute_7203(tr, sh)

        assert result["16a"] == Decimal("50000")     # BOY balance
        assert result["17a"] == Decimal("10000")     # Additional
        assert result["18a"] == Decimal("60000")     # 50k + 10k
        assert result["19a"] == Decimal("15000")     # Repayments
        assert result["20a"] == Decimal("45000")     # 60k - 15k

    def test_debt_basis_adjustments(self, shareholder_with_loan):
        """Lines 21-25: debt basis adjustment computation."""
        tr, sh, loan = shareholder_with_loan
        result = compute_7203(tr, sh)

        assert result["21a"] == Decimal("50000")     # Debt basis BOY
        assert result["22a"] == Decimal("10000")     # New loans increasing basis
        assert result["24a"] == Decimal("60000")     # 50k + 10k + 0
        # Line 25: ratio = 60000/60000 = 1.0
        assert result["25a"] == Decimal("1")

    def test_total_column_sums_loans(self, shareholder_with_loan):
        """Column (d) should sum individual loan columns."""
        tr, sh, loan = shareholder_with_loan
        result = compute_7203(tr, sh)

        # With one loan, total = same as loan (a)
        assert result["16d"] == result["16a"]
        assert result["20d"] == result["20a"]

    def test_gain_on_repayment(self, shareholder_with_loan):
        """Section C: gain = repayment - nontaxable portion."""
        tr, sh, loan = shareholder_with_loan
        result = compute_7203(tr, sh)

        assert result["32a"] == Decimal("15000")     # Repayment
        # With ratio = 1.0, nontaxable = 15000
        assert result["33a"] == Decimal("15000.00")
        assert result["34a"] == ZERO                  # No gain


# ---------------------------------------------------------------------------
# Part III: Loss Limitations
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCompute7203PartIII:
    """Tests for Part III loss limitation and pro-rata allocation."""

    @pytest.fixture
    def sh_with_limited_basis(self, seeded):
        """Shareholder with limited basis and losses."""
        from apps.clients.models import Client, Entity, TaxYear
        from apps.firms.models import Firm
        from apps.returns.models import (
            FormFieldValue,
            FormLine,
            Shareholder,
            TaxReturn,
        )

        firm = Firm.objects.create(name="Firm III")
        client = Client.objects.create(firm=firm, name="Client III")
        entity = Entity.objects.create(
            client=client, name="Corp III", entity_type="scorp",
            ein="11-1111111",
        )
        ty = TaxYear.objects.create(entity=entity, year=2025)
        tr = TaxReturn.objects.create(
            tax_year=ty, form_definition=seeded, status="draft",
        )
        sh = Shareholder.objects.create(
            tax_return=tr,
            name="Charlie Brown",
            ownership_percentage=Decimal("100.0000"),
            stock_basis_boy=Decimal("30000"),
        )

        # Set K1 = -60000 (ordinary loss)
        fl_k1 = FormLine.objects.filter(
            section__form=seeded, line_number="K1"
        ).first()
        if fl_k1:
            FormFieldValue.objects.create(
                tax_return=tr, form_line=fl_k1, value="-60000",
            )

        return tr, sh

    def test_losses_within_basis_all_allowed(self, seeded):
        """When losses <= stock basis, all losses are allowed."""
        from apps.clients.models import Client, Entity, TaxYear
        from apps.firms.models import Firm
        from apps.returns.models import (
            FormFieldValue,
            FormLine,
            Shareholder,
            TaxReturn,
        )

        firm = Firm.objects.create(name="Firm III-OK")
        client = Client.objects.create(firm=firm, name="Client III-OK")
        entity = Entity.objects.create(
            client=client, name="Corp III-OK", entity_type="scorp",
            ein="22-2222222",
        )
        ty = TaxYear.objects.create(entity=entity, year=2025)
        tr = TaxReturn.objects.create(
            tax_year=ty, form_definition=seeded, status="draft",
        )
        sh = Shareholder.objects.create(
            tax_return=tr,
            name="Dana White",
            ownership_percentage=Decimal("100.0000"),
            stock_basis_boy=Decimal("100000"),
        )

        # Set K1 = -40000 (loss within basis)
        fl = FormLine.objects.filter(
            section__form=seeded, line_number="K1"
        ).first()
        if fl:
            FormFieldValue.objects.create(
                tax_return=tr, form_line=fl, value="-40000",
            )

        result = compute_7203(tr, sh)

        # Loss is 40k, basis is 100k — all allowed from stock
        assert result["35a"] == Decimal("40000.00")
        assert result["35c"] == Decimal("40000.00")
        assert result["35d"] == ZERO
        assert result["35e"] == ZERO
        # Line 11 = total allowed from stock
        assert result["11"] == Decimal("40000.00")

    def test_losses_exceed_basis_pro_rata(self, sh_with_limited_basis):
        """When losses > stock basis, allocate pro-rata and suspend excess."""
        tr, sh = sh_with_limited_basis
        result = compute_7203(tr, sh)

        # Loss is 60k at 100% ownership, basis is 30k
        assert result["35a"] == Decimal("60000.00")
        # Stock basis available = 30k (no distributions, no nondeductibles)
        assert result["10"] == Decimal("30000.00")
        # Allowed from stock = 30k (only one loss category, gets it all)
        assert result["35c"] == Decimal("30000.00")
        # No debt basis
        assert result["35d"] == ZERO
        # Suspended = 60k - 30k = 30k
        assert result["35e"] == Decimal("30000.00")

    def test_prior_suspended_losses_combined(self, sh_with_limited_basis):
        """Prior year suspended losses add to current year."""
        tr, sh = sh_with_limited_basis
        sh.suspended_ordinary_loss = Decimal("10000")
        sh.save()

        result = compute_7203(tr, sh)

        # Column (a) = 60k current, column (b) = 10k prior
        assert result["35a"] == Decimal("60000.00")
        assert result["35b"] == Decimal("10000")
        # Total = 70k, basis = 30k
        assert result["35c"] == Decimal("30000.00")
        # Suspended = 70k - 30k = 40k
        assert result["35e"] == Decimal("40000.00")

    def test_zero_basis_all_suspended(self, seeded):
        """Zero basis shareholder: all losses suspended."""
        from apps.clients.models import Client, Entity, TaxYear
        from apps.firms.models import Firm
        from apps.returns.models import (
            FormFieldValue,
            FormLine,
            Shareholder,
            TaxReturn,
        )

        firm = Firm.objects.create(name="Firm III-Z")
        client = Client.objects.create(firm=firm, name="Client III-Z")
        entity = Entity.objects.create(
            client=client, name="Corp III-Z", entity_type="scorp",
            ein="33-3333333",
        )
        ty = TaxYear.objects.create(entity=entity, year=2025)
        tr = TaxReturn.objects.create(
            tax_year=ty, form_definition=seeded, status="draft",
        )
        sh = Shareholder.objects.create(
            tax_return=tr,
            name="Zero Basis",
            ownership_percentage=Decimal("100.0000"),
            stock_basis_boy=Decimal("0"),
        )

        fl = FormLine.objects.filter(
            section__form=seeded, line_number="K1"
        ).first()
        if fl:
            FormFieldValue.objects.create(
                tax_return=tr, form_line=fl, value="-25000",
            )

        result = compute_7203(tr, sh)

        assert result["35a"] == Decimal("25000.00")
        assert result["35c"] == ZERO
        assert result["35e"] == Decimal("25000.00")
        assert result["11"] == ZERO
        assert result["15"] == ZERO
