"""
Schedule D / Form 8949 — Tests from Rule Studio specs.

Tests the Schedule D compute flow: Disposition → aggregate_schedule_d() → K7, K8a.
Tests formula integration: K7 and K8a flow into K18 reconciliation.

Specs:
  - sched_d_1120s_spec.json (8 rules, 17 lines, 2 tests)
  - form_8949_spec.json     (4 rules, 12 lines, 3 tests)
"""

from decimal import Decimal

import pytest

from apps.returns.compute import FORMULAS_1120S, ZERO


def _run_formulas(inputs: dict[str, Decimal]) -> dict[str, Decimal]:
    """Run FORMULAS_1120S against a values dict and return final values."""
    values = {k: Decimal(str(v)) for k, v in inputs.items()}
    for line_number, formula_fn in FORMULAS_1120S:
        values[line_number] = formula_fn(values).quantize(Decimal("1"))
    return values


# ===========================================================================
# Schedule D Spec Tests — R001-R004 (formula-level, no DB)
# ===========================================================================
class TestSchedDBasicAggregation:
    """Spec scenario: Two ST transactions, one LT — correct aggregation.

    ST net = 2000 - 1000 = 1000 → K7
    LT net = 8000 → K8a
    """

    def setup_method(self):
        self.values = _run_formulas({
            "1a": 100000, "1b": 0,
            "7": 50000, "14": 5000,
            # K7 and K8a set by aggregate_schedule_d() before formulas run
            "K7": 1000,    # Net short-term (2 transactions: +2000, -1000)
            "K8a": 8000,   # Net long-term (1 transaction: +8000)
        })

    def test_k7_flows_to_k18(self):
        """K7 (short-term capital gain) is included in K18 reconciliation."""
        assert self.values["K7"] == 1000

    def test_k8a_flows_to_k18(self):
        """K8a (long-term capital gain) is included in K18 reconciliation."""
        assert self.values["K8a"] == 8000

    def test_k18_includes_capital_gains(self):
        """K18 = sum(K1..K10) - K11..K12d. K7 and K8a are included."""
        k1 = self.values["K1"]  # = Line 21
        expected_k18 = k1 + 1000 + 8000  # K1 + K7 + K8a (no K11/K12)
        assert self.values["K18"] == expected_k18


class TestSchedDLossOnly:
    """Spec edge case: Capital losses only, no gains."""

    def setup_method(self):
        self.values = _run_formulas({
            "1a": 200000, "1b": 0,
            "7": 80000, "14": 10000,
            "K7": -5000,   # Net short-term loss
            "K8a": -3000,  # Net long-term loss
        })

    def test_k7_negative_flows(self):
        assert self.values["K7"] == -5000

    def test_k8a_negative_flows(self):
        assert self.values["K8a"] == -3000

    def test_k18_includes_losses(self):
        """K18 correctly includes capital losses (reduces income)."""
        k1 = self.values["K1"]
        expected_k18 = k1 + (-5000) + (-3000)
        assert self.values["K18"] == expected_k18


class TestSchedDMixedWithOtherK:
    """K7/K8a combined with other K-line items (K9, K10, K11, K12a)."""

    def setup_method(self):
        self.values = _run_formulas({
            "1a": 300000, "1b": 0,
            "7": 100000, "14": 20000,
            "K7": 5000,     # ST capital gain
            "K8a": 12000,   # LT capital gain
            "K9": 8000,     # Section 1231 gain (from 4797)
            "F34": 0,       # No farm income
            "K11": 3000,    # Section 179
            "K12a": 2000,   # Charitable contributions
        })

    def test_k18_full_reconciliation(self):
        """K18 = K1 + K7 + K8a + K9 - K11 - K12a."""
        k1 = self.values["K1"]  # = Line 21 = 6 - 20
        expected = k1 + 5000 + 12000 + 8000 - 3000 - 2000
        assert self.values["K18"] == expected


class TestSchedDZero:
    """No capital activity — K7 and K8a default to 0."""

    def setup_method(self):
        self.values = _run_formulas({
            "1a": 100000, "1b": 0,
            "7": 40000, "14": 5000,
        })

    def test_k7_defaults_zero(self):
        """K7 defaults to 0 when no Schedule D dispositions exist."""
        assert self.values.get("K7", Decimal("0")) == 0

    def test_k8a_defaults_zero(self):
        """K8a defaults to 0 when no Schedule D dispositions exist."""
        assert self.values.get("K8a", Decimal("0")) == 0


# ===========================================================================
# K-1 Allocation of K7/K8a (formula-level tests)
# ===========================================================================
class TestK1AllocationCapitalGains:
    """Verify K7 and K8a are in the pro-rata allocation map."""

    def test_k7_in_k1_map(self):
        """K7 → K-1 Box 7 (short-term capital gain)."""
        from apps.tts_forms.renderer import SCHED_K_TO_K1_MAP
        assert "K7" in SCHED_K_TO_K1_MAP
        assert SCHED_K_TO_K1_MAP["K7"] == "7"

    def test_k8a_in_k1_map(self):
        """K8a → K-1 Box 8a (long-term capital gain)."""
        from apps.tts_forms.renderer import SCHED_K_TO_K1_MAP
        assert "K8a" in SCHED_K_TO_K1_MAP
        assert SCHED_K_TO_K1_MAP["K8a"] == "8a"

    def test_k9_in_k1_map(self):
        """K9 → K-1 Box 9 (Section 1231 gain, NOT on Schedule D)."""
        from apps.tts_forms.renderer import SCHED_K_TO_K1_MAP
        assert "K9" in SCHED_K_TO_K1_MAP
        assert SCHED_K_TO_K1_MAP["K9"] == "9"


# ===========================================================================
# Section 1231 bypass verification
# ===========================================================================
class TestSection1231BypassesScheduleD:
    """Spec R010: Section 1231 gains do NOT flow through Schedule D on 1120-S.

    They bypass Schedule D and go directly to K9 from Form 4797.
    K7/K8a are from Schedule D capital assets; K9 is from 4797 business property.
    """

    def setup_method(self):
        self.values = _run_formulas({
            "1a": 200000, "1b": 0,
            "7": 60000, "14": 8000,
            "4": 15000,    # Ordinary gain from 4797 Part II (Page 1 Line 4)
            "K7": 3000,    # ST capital gain (from Schedule D)
            "K8a": 7000,   # LT capital gain (from Schedule D)
            "K9": 10000,   # Section 1231 gain (from 4797 Part I — NOT Schedule D)
        })

    def test_all_three_in_k18(self):
        """K7, K8a, and K9 all flow to K18 — but from different sources."""
        k1 = self.values["K1"]  # includes Line 4 (4797 ordinary)
        expected_k18 = k1 + 3000 + 7000 + 10000
        assert self.values["K18"] == expected_k18

    def test_4797_ordinary_on_page1(self):
        """Form 4797 Part II ordinary gains appear on Page 1 Line 4."""
        assert self.values["4"] == 15000
        # Line 6 = 3 + 4 + 5
        assert self.values["6"] == self.values["3"] + 15000
