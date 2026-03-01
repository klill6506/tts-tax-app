"""Tests for GA Form 600S — seed, compute formulas, net worth tax table."""

import pytest
from decimal import Decimal

from apps.returns.compute import (
    FORMULAS_GA600S,
    _ga_net_worth_tax,
    GA_NET_WORTH_TAX_TABLE,
    GA_NET_WORTH_TAX_MAX,
    _d,
    _sum,
    ZERO,
)
from apps.returns.management.commands.seed_ga600s import Command as SeedGA600SCommand
from apps.returns.models import FormDefinition, FormLine, FormSection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded(db):
    """Seed GA 600S form definition."""
    cmd = SeedGA600SCommand()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="GA-600S")


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSeedGA600S:
    def test_seed_creates_form(self, seeded):
        assert seeded.code == "GA-600S"
        assert seeded.name == "Georgia S Corporation Tax Return"

    def test_seed_creates_sections(self, seeded):
        sections = FormSection.objects.filter(form=seeded)
        assert sections.count() == 7

    def test_seed_creates_lines(self, seeded):
        lines = FormLine.objects.filter(section__form=seeded)
        assert lines.count() == 85

    def test_seed_is_idempotent(self, seeded):
        cmd = SeedGA600SCommand()
        cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
        cmd.handle()
        cmd.stdout.close()
        assert FormLine.objects.filter(section__form=seeded).count() == 85

    def test_schedule_4_has_three_columns(self, seeded):
        """Schedule 4 rows have a/b/c sub-lines for 3-column layout."""
        sched4_lines = FormLine.objects.filter(
            section__form=seeded, section__code="sched_4"
        )
        # 11 rows × 3 columns = 33 lines
        assert sched4_lines.count() == 33


# ---------------------------------------------------------------------------
# Net worth tax table tests
# ---------------------------------------------------------------------------


class TestGANetWorthTax:
    """Test the tiered bracket net worth tax lookup."""

    def test_zero_net_worth(self):
        assert _ga_net_worth_tax(Decimal("0")) == ZERO

    def test_under_100k(self):
        assert _ga_net_worth_tax(Decimal("50000")) == ZERO
        assert _ga_net_worth_tax(Decimal("99999")) == ZERO
        assert _ga_net_worth_tax(Decimal("100000")) == ZERO

    def test_first_bracket(self):
        assert _ga_net_worth_tax(Decimal("100001")) == Decimal("125")
        assert _ga_net_worth_tax(Decimal("150000")) == Decimal("125")

    def test_mid_brackets(self):
        assert _ga_net_worth_tax(Decimal("200001")) == Decimal("200")
        assert _ga_net_worth_tax(Decimal("500000")) == Decimal("250")
        assert _ga_net_worth_tax(Decimal("750001")) == Decimal("500")
        assert _ga_net_worth_tax(Decimal("1000000")) == Decimal("500")
        assert _ga_net_worth_tax(Decimal("1000001")) == Decimal("750")

    def test_high_brackets(self):
        assert _ga_net_worth_tax(Decimal("20000001")) == Decimal("4500")
        assert _ga_net_worth_tax(Decimal("22000000")) == Decimal("4500")

    def test_over_max(self):
        assert _ga_net_worth_tax(Decimal("22000001")) == Decimal("5000")
        assert _ga_net_worth_tax(Decimal("100000000")) == Decimal("5000")

    def test_negative_net_worth(self):
        assert _ga_net_worth_tax(Decimal("-500000")) == ZERO


# ---------------------------------------------------------------------------
# Compute formula tests (unit-level, no DB needed)
# ---------------------------------------------------------------------------


class TestGA600SFormulas:
    """Test key GA 600S computation formulas in isolation."""

    def _run_formulas(self, initial_values: dict[str, Decimal]) -> dict[str, Decimal]:
        """Run all GA 600S formulas on given initial values."""
        values = {k: v for k, v in initial_values.items()}
        for line_number, formula_fn in FORMULAS_GA600S:
            values[line_number] = formula_fn(values).quantize(Decimal("0.01"))
        return values

    def test_basic_income_tax_flow(self):
        """Fed income → Schedule 6 → Schedule 5 → Schedule 1 → tax."""
        vals = self._run_formulas({
            "S6_1": Decimal("100000"),   # ordinary income
            "S5_4": Decimal("1.000000"),  # 100% GA ratio
        })
        # Schedule 6: total fed income = 100K, no additions/subtractions
        assert vals["S6_7"] == Decimal("100000.00")
        assert vals["S6_11"] == Decimal("100000.00")
        # Schedule 5: all GA
        assert vals["S5_7"] == Decimal("100000.00")
        # Schedule 1: taxable income × 5.39%
        assert vals["S1_6"] == Decimal("100000.00")
        assert vals["S1_7"] == Decimal("5390.00")

    def test_additions_and_subtractions(self):
        """Schedule 7 additions and Schedule 8 subtractions flow through."""
        vals = self._run_formulas({
            "S6_1": Decimal("200000"),
            "S7_1": Decimal("5000"),   # out-of-state bond interest
            "S8_1": Decimal("3000"),   # US obligations interest
            "S5_4": Decimal("1.000000"),
        })
        assert vals["S7_8"] == Decimal("5000.00")
        assert vals["S8_5"] == Decimal("3000.00")
        assert vals["S6_8"] == Decimal("5000.00")
        assert vals["S6_10"] == Decimal("3000.00")
        assert vals["S6_11"] == Decimal("202000.00")  # 200K + 5K - 3K

    def test_apportionment(self):
        """Schedule 5 apportionment ratio reduces GA taxable income."""
        vals = self._run_formulas({
            "S6_1": Decimal("500000"),
            "S5_4": Decimal("0.400000"),  # 40% GA ratio
        })
        assert vals["S5_3"] == Decimal("500000.00")
        assert vals["S5_5"] == Decimal("200000.00")
        assert vals["S5_7"] == Decimal("200000.00")
        assert vals["S1_7"] == Decimal("10780.00")  # 200K × 5.39%

    def test_net_worth_tax(self):
        """Schedule 3 net worth tax flows to Schedule 4."""
        vals = self._run_formulas({
            "S6_1": Decimal("0"),
            "S5_4": Decimal("1.000000"),
            "S3_1": Decimal("100000"),  # capital stock
            "S3_2": Decimal("50000"),   # paid-in surplus
            "S3_3": Decimal("350000"),  # retained earnings
            "S3_5": Decimal("1.000000"),  # 100% GA
        })
        assert vals["S3_4"] == Decimal("500000.00")
        assert vals["S3_6"] == Decimal("500000.00")
        assert vals["S3_7"] == Decimal("250.00")  # $500K bracket → $250
        assert vals["S4_1b"] == Decimal("250.00")

    def test_tax_due_with_payments(self):
        """Schedule 4 computes balance due or overpayment."""
        vals = self._run_formulas({
            "S6_1": Decimal("100000"),
            "S5_4": Decimal("1.000000"),
            "S3_1": Decimal("0"),
            "S3_5": Decimal("1.000000"),
            "S4_2a": Decimal("4000"),  # estimated payment (income)
        })
        # Income tax = 5390, payment = 4000
        assert vals["S4_1a"] == Decimal("5390.00")
        assert vals["S4_5a"] == Decimal("1390.00")  # balance due
        assert vals["S4_6a"] == ZERO  # no overpayment

    def test_overpayment(self):
        """Excess payments create overpayment."""
        vals = self._run_formulas({
            "S6_1": Decimal("100000"),
            "S5_4": Decimal("1.000000"),
            "S3_1": Decimal("0"),
            "S3_5": Decimal("1.000000"),
            "S4_2a": Decimal("6000"),  # overpaid
        })
        assert vals["S4_5a"] == ZERO  # no balance due
        assert vals["S4_6a"] == Decimal("610.00")  # 6000 - 5390
        assert vals["S4_11a"] == Decimal("610.00")  # credited to next year

    def test_loss_no_negative_tax(self):
        """Negative taxable income produces zero tax, not negative."""
        vals = self._run_formulas({
            "S6_1": Decimal("-50000"),
            "S5_4": Decimal("1.000000"),
        })
        assert vals["S1_6"] == Decimal("-50000.00")
        assert vals["S1_7"] == ZERO  # no negative tax
