"""
Supporting Forms — Tests from Rule Studio specs.

Tests compute flows for 1125-A, 1125-E, 8825, and GA-600S.

Specs:
  - form_1125a_spec.json (3 rules, 8 lines)
  - form_1125e_spec.json (3 rules, 2 lines)
  - form_8825_spec.json  (4 rules, 17 lines)
  - ga600s_spec.json     (6 rules, 8 lines)
"""

from decimal import Decimal

import pytest

from apps.returns.compute import (
    FORMULAS_1120S,
    FORMULAS_GA600S,
    _ga_net_worth_tax,
    ZERO,
)


def _run_formulas(formulas, inputs: dict[str, Decimal]) -> dict[str, Decimal]:
    """Run a formula list against a values dict and return final values."""
    values = {k: Decimal(str(v)) for k, v in inputs.items()}
    for line_number, formula_fn in formulas:
        values[line_number] = formula_fn(values).quantize(Decimal("1"))
    return values


def _run_1120s(inputs):
    return _run_formulas(FORMULAS_1120S, inputs)


def _run_ga600s(inputs):
    return _run_formulas(FORMULAS_GA600S, inputs)


# ===========================================================================
# Form 1125-A (COGS) Spec Tests — R001, R002, R003
# ===========================================================================
class TestCOGSBasicCalculation:
    """Spec: Basic COGS — 50K begin, 200K purchases, 30K labor, 5K 263A, 2K other."""

    def setup_method(self):
        self.values = _run_1120s({
            "1a": 500000, "1b": 0,
            "A1": 50000,    # Beginning inventory
            "A2": 200000,   # Purchases
            "A3": 30000,    # Cost of labor
            "A4": 5000,     # Section 263A costs
            "A5": 2000,     # Other costs
            "A7": 55000,    # Ending inventory
            "7": 50000, "14": 10000,
        })

    def test_r001_total_costs(self):
        """R001: A6 = A1 + A2 + A3 + A4 + A5 = 287,000."""
        assert self.values["A6"] == 287000

    def test_r002_cogs(self):
        """R002: A8 = A6 - A7 = 287,000 - 55,000 = 232,000."""
        assert self.values["A8"] == 232000

    def test_r003_flows_to_page1_line2(self):
        """R003: Page 1 Line 2 = COGS (A8)."""
        assert self.values["2"] == 232000

    def test_gross_profit(self):
        """Line 3 = 1c - 2 = 500,000 - 232,000 = 268,000."""
        assert self.values["3"] == 268000


class TestCOGSServiceCompany:
    """Spec: Service company — zero COGS."""

    def setup_method(self):
        self.values = _run_1120s({
            "1a": 300000, "1b": 0,
            # No COGS inputs
            "7": 80000, "14": 5000,
        })

    def test_zero_cogs(self):
        """A8 = 0 when no COGS data."""
        assert self.values["A8"] == 0

    def test_line2_zero(self):
        assert self.values["2"] == 0

    def test_gross_profit_equals_net_receipts(self):
        assert self.values["3"] == 300000


# ===========================================================================
# Form 1125-E (Officer Compensation) Spec Tests — R001, R002
# ===========================================================================
class TestOfficerCompensationFlow:
    """Spec: Officer comp flows to Page 1 Line 7.

    Note: aggregate_officer_compensation() sets Line 7 via _set_field_value.
    Here we test that Line 7 is correctly included in total deductions.
    """

    def setup_method(self):
        self.values = _run_1120s({
            "1a": 400000, "1b": 0,
            "7": 80000,    # Officer compensation (set by aggregate_officer_compensation)
            "8": 30000,    # Salaries and wages
            "14": 10000,   # Depreciation
        })

    def test_officer_comp_in_deductions(self):
        """Line 7 flows into Line 20 (total deductions)."""
        assert self.values["20"] == 120000  # 80000 + 30000 + 10000

    def test_ordinary_income(self):
        """Line 21 = 6 - 20."""
        assert self.values["21"] == 280000  # 400000 - 120000


# ===========================================================================
# Form 8825 (Rental) Spec Tests — R001-R004
# ===========================================================================
class TestRentalIncomeFlowToK2:
    """Spec R003: K2 = sum(all net_rent) from Form 8825.

    Note: aggregate_rental_income() sets K2 via _set_field_value.
    Here we test K2 flows into K18 reconciliation.
    """

    def setup_method(self):
        self.values = _run_1120s({
            "1a": 200000, "1b": 0,
            "7": 50000, "14": 8000,
            "K2": 7500,     # Set by aggregate_rental_income (net rental income)
        })

    def test_k2_in_k18(self):
        """K2 is included in K18 reconciliation."""
        k1 = self.values["K1"]
        expected_k18 = k1 + 7500
        assert self.values["K18"] == expected_k18


class TestRentalLossFlowToK2:
    """Spec: Rental loss flows through K2."""

    def setup_method(self):
        self.values = _run_1120s({
            "1a": 200000, "1b": 0,
            "7": 50000, "14": 8000,
            "K2": -12000,   # Net rental loss
        })

    def test_k2_loss_in_k18(self):
        """K2 rental loss reduces K18."""
        k1 = self.values["K1"]
        expected_k18 = k1 + (-12000)
        assert self.values["K18"] == expected_k18


# ===========================================================================
# GA-600S Spec Tests — R001-R006
# ===========================================================================
class TestGA600SSingleState:
    """Spec: Single-state GA S-Corp, no bonus difference."""

    def setup_method(self):
        self.values = _run_ga600s({
            "S6_1": 95000,     # Federal taxable income
            "S5_4": 1,         # 100% apportionment
            "GA_PTET": 0,      # No PTET election
            "S3_1": 500000,    # Net worth component 1
        })

    def test_r001_ga_taxable_income(self):
        """S6_11 = S6_7 + additions - subtractions."""
        assert self.values["S6_11"] == 95000

    def test_ga_net_income(self):
        """S5_7 = S5_1 * apportionment."""
        assert self.values["S5_7"] == 95000

    def test_s1_taxable(self):
        """Schedule 1 taxable income = apportioned net income."""
        assert self.values["S1_1"] == 95000

    def test_no_income_tax_without_ptet(self):
        """S1_7 = 0 when PTET not elected."""
        assert self.values["S1_7"] == 0


class TestGA600SWithBonusAddback:
    """Spec: S-Corp with $100K federal bonus depreciation addback."""

    def setup_method(self):
        self.values = _run_ga600s({
            "S6_1": 50000,      # Federal taxable income
            "S7_1": 100000,     # Bonus depreciation addback (GA nonconformity)
            "S8_1": 14286,      # GA depreciation (7yr SL year 1: 100K/7)
            "S5_4": 1,          # 100% apportionment
            "GA_PTET": 0,
        })

    def test_r002_additions(self):
        """S7_8 includes bonus addback."""
        assert self.values["S7_8"] == 100000

    def test_subtractions(self):
        """S8_5 includes GA depreciation."""
        assert self.values["S8_5"] == 14286

    def test_ga_taxable_income(self):
        """S6_11 = 50000 + 100000 - 14286 = 135,714."""
        assert self.values["S6_11"] == 135714


class TestGA600SPTET:
    """Spec R003: PTET at GA income tax rate.

    Note: Spec says 5.49% (TY 2024 rate). Code uses 5.39% (TY 2025 rate).
    GA lowered the rate from 5.49% → 5.39% for 2025. Code is correct.
    """

    def setup_method(self):
        self.values = _run_ga600s({
            "S6_1": 200000,
            "S5_4": 1,
            "GA_PTET": 1,  # PTET elected
        })

    def test_ptet_tax(self):
        """S2_4 = $200,000 × 5.39% = $10,780."""
        assert self.values["S2_4"] == 10780

    def test_income_tax_with_ptet(self):
        """S1_7 = income × 5.39% when PTET elected."""
        assert self.values["S1_7"] == 10780


class TestGA600SMultiState:
    """Spec: Multi-state with 60% GA apportionment."""

    def setup_method(self):
        self.values = _run_ga600s({
            "S6_1": 200000,
            "S5_4": Decimal("0.60"),  # 60% apportionment
            "GA_PTET": 0,
        })

    def test_ga_apportioned_income(self):
        """S5_5 = $200,000 × 60% = $120,000."""
        assert self.values["S5_5"] == 120000


class TestGA600SNetWorthTax:
    """Spec R004: Net worth tax bracket lookup."""

    def test_bracket_100k(self):
        """Net worth ≤ $100K = $0."""
        assert _ga_net_worth_tax(Decimal("100000")) == 0

    def test_bracket_150k(self):
        """Net worth $100,001-$150,000 = $125."""
        assert _ga_net_worth_tax(Decimal("150000")) == 125

    def test_bracket_500k(self):
        """Net worth $300,001-$500,000 = $250."""
        assert _ga_net_worth_tax(Decimal("500000")) == 250

    def test_bracket_1m(self):
        """Net worth $750,001-$1,000,000 = $500."""
        assert _ga_net_worth_tax(Decimal("1000000")) == 500

    def test_bracket_22m(self):
        """Net worth $20,000,001-$22,000,000 = $4,500."""
        assert _ga_net_worth_tax(Decimal("22000000")) == 4500

    def test_over_22m(self):
        """Net worth > $22,000,000 = $5,000 (max)."""
        assert _ga_net_worth_tax(Decimal("25000000")) == 5000

    def test_zero(self):
        """Net worth ≤ 0 = $0."""
        assert _ga_net_worth_tax(Decimal("0")) == 0
        assert _ga_net_worth_tax(Decimal("-10000")) == 0
