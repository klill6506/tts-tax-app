"""
Tests for the 1065 K-1 allocation engine.

Tests cover:
- Default pro-rata allocation by profit/loss %
- Special allocation overrides by category
- Guaranteed payments (per-partner, not allocated)
- Self-employment earnings by partner type
- Distributions (per-partner, not allocated)
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from apps.returns.k1_allocator import (
    allocate_k1,
    compute_self_employment,
    get_allocation_pct,
)
from apps.returns.models import AllocationCategory


ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# get_allocation_pct tests
# ---------------------------------------------------------------------------


class TestGetAllocationPct:
    def test_default_profit_pct_for_income(self):
        """Income items use profit_pct when no special allocation."""
        partner = MagicMock()
        partner.profit_pct = Decimal("50.0000")
        partner.loss_pct = Decimal("30.0000")

        pct = get_allocation_pct(partner, "ordinary", Decimal("1000"), {})
        assert pct == Decimal("0.5000")

    def test_default_loss_pct_for_losses(self):
        """Loss items use loss_pct when no special allocation."""
        partner = MagicMock()
        partner.profit_pct = Decimal("50.0000")
        partner.loss_pct = Decimal("30.0000")

        pct = get_allocation_pct(partner, "ordinary", Decimal("-500"), {})
        assert pct == Decimal("0.3000")

    def test_special_allocation_overrides_default(self):
        """PartnerAllocation override takes priority over default %."""
        partner = MagicMock()
        partner.profit_pct = Decimal("50.0000")
        partner.loss_pct = Decimal("30.0000")

        alloc_map = {"ordinary": Decimal("75.0000")}
        pct = get_allocation_pct(partner, "ordinary", Decimal("1000"), alloc_map)
        assert pct == Decimal("0.750000")

    def test_no_category_uses_profit_pct(self):
        """Lines without a category mapping use profit_pct."""
        partner = MagicMock()
        partner.profit_pct = Decimal("40.0000")
        partner.loss_pct = Decimal("40.0000")

        pct = get_allocation_pct(partner, None, Decimal("100"), {})
        assert pct == Decimal("0.4000")


# ---------------------------------------------------------------------------
# compute_self_employment tests
# ---------------------------------------------------------------------------


class TestComputeSelfEmployment:
    def test_general_partner_se(self):
        """General partner: ordinary income + total GP."""
        partner = MagicMock()
        partner.partner_type = "general"
        partner.gp_services = Decimal("20000")
        partner.gp_capital = Decimal("5000")

        k1_data = {"1": Decimal("50000")}
        se = compute_self_employment(partner, k1_data)

        # 50000 (ordinary) + 20000 (svc) + 5000 (cap) = 75000
        assert se["14a"] == Decimal("75000")

    def test_limited_partner_se(self):
        """Limited partner: only GP for services."""
        partner = MagicMock()
        partner.partner_type = "limited"
        partner.gp_services = Decimal("15000")
        partner.gp_capital = Decimal("10000")

        k1_data = {"1": Decimal("50000")}
        se = compute_self_employment(partner, k1_data)

        # Limited: only GP for services = 15000
        assert se["14a"] == Decimal("15000")

    def test_llc_member_treated_as_general(self):
        """LLC member: treated as general partner for SE."""
        partner = MagicMock()
        partner.partner_type = "llc_member"
        partner.gp_services = Decimal("10000")
        partner.gp_capital = Decimal("0")

        k1_data = {"1": Decimal("30000")}
        se = compute_self_employment(partner, k1_data)

        # LLC member = general: 30000 + 10000 = 40000
        assert se["14a"] == Decimal("40000")

    def test_no_gp_no_income(self):
        """Partner with no GP and no ordinary income has zero SE."""
        partner = MagicMock()
        partner.partner_type = "general"
        partner.gp_services = Decimal("0")
        partner.gp_capital = Decimal("0")

        k1_data = {}
        se = compute_self_employment(partner, k1_data)
        assert se["14a"] == ZERO

    def test_loss_reduces_se_for_general(self):
        """General partner with ordinary loss: loss + GP."""
        partner = MagicMock()
        partner.partner_type = "general"
        partner.gp_services = Decimal("30000")
        partner.gp_capital = Decimal("0")

        k1_data = {"1": Decimal("-10000")}
        se = compute_self_employment(partner, k1_data)

        # -10000 + 30000 = 20000
        assert se["14a"] == Decimal("20000")


# ---------------------------------------------------------------------------
# allocate_k1 tests (integration — uses mock QuerySet)
# ---------------------------------------------------------------------------


class TestAllocateK1:
    @patch("apps.returns.k1_allocator.PartnerAllocation")
    def test_basic_pro_rata(self, MockAllocation):
        """Basic pro-rata allocation by profit %."""
        MockAllocation.objects.filter.return_value.values_list.return_value = []

        partner = MagicMock()
        partner.profit_pct = Decimal("50.0000")
        partner.loss_pct = Decimal("50.0000")
        partner.gp_services = Decimal("0")
        partner.gp_capital = Decimal("0")
        partner.distributions = Decimal("0")
        partner.partner_type = "general"

        k_values = {
            "K1": "100000",
            "K5": "2000",
            "K6a": "1000",
        }

        tax_return = MagicMock()
        result = allocate_k1(tax_return, partner, k_values)

        assert result["1"] == Decimal("50000")
        assert result["5"] == Decimal("1000")
        assert result["6a"] == Decimal("500")

    @patch("apps.returns.k1_allocator.PartnerAllocation")
    def test_special_allocation_override(self, MockAllocation):
        """Special allocation overrides default for that category."""
        # Interest income allocated 75% to this partner
        MockAllocation.objects.filter.return_value.values_list.return_value = [
            ("interest", Decimal("75.0000")),
        ]

        partner = MagicMock()
        partner.profit_pct = Decimal("50.0000")
        partner.loss_pct = Decimal("50.0000")
        partner.gp_services = Decimal("0")
        partner.gp_capital = Decimal("0")
        partner.distributions = Decimal("0")
        partner.partner_type = "general"

        k_values = {
            "K1": "100000",  # ordinary → 50% default
            "K5": "10000",   # interest → 75% special
        }

        tax_return = MagicMock()
        result = allocate_k1(tax_return, partner, k_values)

        assert result["1"] == Decimal("50000")   # 50% default
        assert result["5"] == Decimal("7500")     # 75% special

    @patch("apps.returns.k1_allocator.PartnerAllocation")
    def test_guaranteed_payments_per_partner(self, MockAllocation):
        """GP are per-partner amounts, not pro-rata."""
        MockAllocation.objects.filter.return_value.values_list.return_value = []

        partner = MagicMock()
        partner.profit_pct = Decimal("50.0000")
        partner.loss_pct = Decimal("50.0000")
        partner.gp_services = Decimal("25000")
        partner.gp_capital = Decimal("5000")
        partner.distributions = Decimal("0")
        partner.partner_type = "general"

        k_values = {"K1": "100000"}
        tax_return = MagicMock()
        result = allocate_k1(tax_return, partner, k_values)

        assert result["4a"] == Decimal("25000")
        assert result["4b"] == Decimal("5000")
        assert result["4c"] == Decimal("30000")

    @patch("apps.returns.k1_allocator.PartnerAllocation")
    def test_distributions_per_partner(self, MockAllocation):
        """Distributions are per-partner, not pro-rata."""
        MockAllocation.objects.filter.return_value.values_list.return_value = []

        partner = MagicMock()
        partner.profit_pct = Decimal("50.0000")
        partner.loss_pct = Decimal("50.0000")
        partner.gp_services = Decimal("0")
        partner.gp_capital = Decimal("0")
        partner.distributions = Decimal("15000")
        partner.partner_type = "general"

        k_values = {}
        tax_return = MagicMock()
        result = allocate_k1(tax_return, partner, k_values)

        assert result["19a"] == Decimal("15000")

    @patch("apps.returns.k1_allocator.PartnerAllocation")
    def test_loss_uses_loss_pct(self, MockAllocation):
        """Losses use loss_pct, not profit_pct."""
        MockAllocation.objects.filter.return_value.values_list.return_value = []

        partner = MagicMock()
        partner.profit_pct = Decimal("60.0000")
        partner.loss_pct = Decimal("40.0000")
        partner.gp_services = Decimal("0")
        partner.gp_capital = Decimal("0")
        partner.distributions = Decimal("0")
        partner.partner_type = "general"

        k_values = {"K1": "-50000"}  # ordinary loss
        tax_return = MagicMock()
        result = allocate_k1(tax_return, partner, k_values)

        # Loss: -50000 × 40% = -20000
        assert result["1"] == Decimal("-20000")

    @patch("apps.returns.k1_allocator.PartnerAllocation")
    def test_se_included_for_general_partner(self, MockAllocation):
        """SE earnings computed and included in K-1 data."""
        MockAllocation.objects.filter.return_value.values_list.return_value = []

        partner = MagicMock()
        partner.profit_pct = Decimal("100.0000")
        partner.loss_pct = Decimal("100.0000")
        partner.gp_services = Decimal("20000")
        partner.gp_capital = Decimal("0")
        partner.distributions = Decimal("0")
        partner.partner_type = "general"

        k_values = {"K1": "80000"}
        tax_return = MagicMock()
        result = allocate_k1(tax_return, partner, k_values)

        # SE = ordinary (80000) + GP total (20000) = 100000
        assert result["14a"] == Decimal("100000")

    @patch("apps.returns.k1_allocator.PartnerAllocation")
    def test_zero_values_excluded(self, MockAllocation):
        """Zero-value lines are not included in results."""
        MockAllocation.objects.filter.return_value.values_list.return_value = []

        partner = MagicMock()
        partner.profit_pct = Decimal("50.0000")
        partner.loss_pct = Decimal("50.0000")
        partner.gp_services = Decimal("0")
        partner.gp_capital = Decimal("0")
        partner.distributions = Decimal("0")
        partner.partner_type = "general"

        k_values = {"K1": "0", "K5": "0"}
        tax_return = MagicMock()
        result = allocate_k1(tax_return, partner, k_values)

        assert "1" not in result
        assert "5" not in result
        assert "4a" not in result
        assert "19a" not in result
