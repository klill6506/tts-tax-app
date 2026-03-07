"""Tests for Schedule F — Farm Income (seed and computation)."""

import pytest
from decimal import Decimal

from apps.returns.compute import FORMULAS_1120S, _d, _sum, ZERO
from apps.returns.management.commands.seed_1120s import Command as SeedCommand
from apps.returns.models import (
    FormDefinition,
    FormFieldValue,
    FormLine,
    FormSection,
    TaxReturn,
)
from apps.firms.models import Firm
from apps.clients.models import Client, Entity, TaxYear


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded(db):
    """Seed 1120-S form definition (includes Schedule F)."""
    cmd = SeedCommand()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="1120-S")


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestScheduleFSeed:
    def test_schedule_f_section_exists(self, seeded):
        section = FormSection.objects.get(form=seeded, code="sched_f")
        assert section.title == "Schedule F — Profit or Loss From Farming"

    def test_schedule_f_has_38_lines(self, seeded):
        lines = FormLine.objects.filter(
            section__form=seeded, section__code="sched_f"
        )
        assert lines.count() == 38

    def test_schedule_f_computed_lines(self, seeded):
        computed = FormLine.objects.filter(
            section__form=seeded,
            section__code="sched_f",
            is_computed=True,
        ).values_list("line_number", flat=True)
        assert set(computed) == {"F1c", "F9", "F33", "F34"}

    def test_schedule_f_income_lines(self, seeded):
        """Farm income lines (F1a through F9) exist."""
        income_lines = FormLine.objects.filter(
            section__form=seeded,
            section__code="sched_f",
            line_number__in=[
                "F1a", "F1b", "F1c", "F2", "F3", "F4",
                "F5", "F6", "F7", "F8", "F9",
            ],
        )
        assert income_lines.count() == 11

    def test_schedule_f_expense_lines(self, seeded):
        """Farm expense lines (F10 through F32) exist."""
        expense_lines = FormLine.objects.filter(
            section__form=seeded,
            section__code="sched_f",
            line_number__startswith="F",
        ).exclude(
            line_number__in=[
                "F1a", "F1b", "F1c", "F2", "F3", "F4",
                "F5", "F6", "F7", "F8", "F9", "F33", "F34",
            ],
        )
        assert expense_lines.count() == 25


# ---------------------------------------------------------------------------
# Computation formula tests (no DB needed)
# ---------------------------------------------------------------------------


class TestScheduleFFormulas:
    """Test Schedule F formulas in isolation — pure calculation, no DB."""

    def _run_formulas(
        self, initial_values: dict[str, Decimal]
    ) -> dict[str, Decimal]:
        """Run all 1120-S formulas on given initial values."""
        values = {k: v for k, v in initial_values.items()}
        for line_number, formula_fn in FORMULAS_1120S:
            values[line_number] = formula_fn(values).quantize(Decimal("0.01"))
        return values

    # -- Farm Income (Part I) --

    def test_f1c_net_sales(self):
        """F1c = F1a - F1b (net livestock/resale)."""
        vals = self._run_formulas({
            "F1a": Decimal("50000"),
            "F1b": Decimal("20000"),
        })
        assert vals["F1c"] == Decimal("30000.00")

    def test_f1c_loss(self):
        """F1c can be negative if cost exceeds sales."""
        vals = self._run_formulas({
            "F1a": Decimal("10000"),
            "F1b": Decimal("15000"),
        })
        assert vals["F1c"] == Decimal("-5000.00")

    def test_f9_gross_income(self):
        """F9 = sum of F1c + F2 through F8."""
        vals = self._run_formulas({
            "F1a": Decimal("10000"),
            "F1b": Decimal("3000"),
            "F2": Decimal("25000"),
            "F3": Decimal("1000"),
            "F4": Decimal("2000"),
            "F5": Decimal("500"),
            "F6": Decimal("3000"),
            "F7": Decimal("4000"),
            "F8": Decimal("1500"),
        })
        # F1c = 7000, then 7000 + 25000 + 1000 + 2000 + 500 + 3000 + 4000 + 1500 = 44000
        assert vals["F9"] == Decimal("44000.00")

    def test_f9_with_only_produce_sales(self):
        """F9 works with just line 2 (most common farm income)."""
        vals = self._run_formulas({
            "F2": Decimal("80000"),
        })
        assert vals["F9"] == Decimal("80000.00")

    # -- Farm Expenses (Part II) --

    def test_f33_total_expenses(self):
        """F33 = sum of all expense lines F10 through F32."""
        vals = self._run_formulas({
            "F10": Decimal("5000"),   # Car/truck
            "F11": Decimal("2000"),   # Chemicals
            "F14": Decimal("8000"),   # Depreciation
            "F16": Decimal("12000"),  # Feed
            "F17": Decimal("3000"),   # Fertilizer
            "F19": Decimal("4000"),   # Gasoline
            "F22": Decimal("6000"),   # Labor
            "F25": Decimal("2500"),   # Repairs
            "F29": Decimal("1500"),   # Taxes
        })
        assert vals["F33"] == Decimal("44000.00")

    def test_f33_all_expense_lines(self):
        """F33 sums all 25 expense lines when populated."""
        vals = self._run_formulas({
            "F10": Decimal("100"),
            "F11": Decimal("100"),
            "F12": Decimal("100"),
            "F13": Decimal("100"),
            "F14": Decimal("100"),
            "F15": Decimal("100"),
            "F16": Decimal("100"),
            "F17": Decimal("100"),
            "F18": Decimal("100"),
            "F19": Decimal("100"),
            "F20": Decimal("100"),
            "F21a": Decimal("100"),
            "F21b": Decimal("100"),
            "F22": Decimal("100"),
            "F23": Decimal("100"),
            "F24a": Decimal("100"),
            "F24b": Decimal("100"),
            "F25": Decimal("100"),
            "F26": Decimal("100"),
            "F27": Decimal("100"),
            "F28": Decimal("100"),
            "F29": Decimal("100"),
            "F30": Decimal("100"),
            "F31": Decimal("100"),
            "F32": Decimal("100"),
        })
        assert vals["F33"] == Decimal("2500.00")  # 25 × 100

    # -- Net Farm Profit/Loss --

    def test_f34_net_profit(self):
        """F34 = F9 - F33 (positive = profit)."""
        vals = self._run_formulas({
            "F2": Decimal("100000"),
            "F16": Decimal("20000"),
            "F22": Decimal("15000"),
        })
        assert vals["F9"] == Decimal("100000.00")
        assert vals["F33"] == Decimal("35000.00")
        assert vals["F34"] == Decimal("65000.00")

    def test_f34_net_loss(self):
        """F34 = F9 - F33 (negative = loss)."""
        vals = self._run_formulas({
            "F2": Decimal("20000"),
            "F16": Decimal("25000"),
            "F22": Decimal("10000"),
        })
        assert vals["F9"] == Decimal("20000.00")
        assert vals["F33"] == Decimal("35000.00")
        assert vals["F34"] == Decimal("-15000.00")

    def test_f34_zero(self):
        """F34 = 0 when no farm data."""
        vals = self._run_formulas({})
        assert vals["F34"] == ZERO

    # -- K-Line Flow --

    def test_f34_flows_to_k10(self):
        """Net farm profit flows to Schedule K line 10."""
        vals = self._run_formulas({
            "F2": Decimal("80000"),
            "F16": Decimal("30000"),
        })
        assert vals["F34"] == Decimal("50000.00")
        assert vals["K10"] == Decimal("50000.00")

    def test_farm_loss_flows_to_k10(self):
        """Net farm loss (negative) flows to K10."""
        vals = self._run_formulas({
            "F2": Decimal("10000"),
            "F16": Decimal("25000"),
        })
        assert vals["F34"] == Decimal("-15000.00")
        assert vals["K10"] == Decimal("-15000.00")

    def test_k18_includes_farm_income(self):
        """K18 reconciliation total includes farm income via K10."""
        vals = self._run_formulas({
            "F2": Decimal("50000"),
            "F16": Decimal("20000"),
        })
        # F34 = 30000, K10 = 30000
        # K18 = K1(0) + K2(0) + ... + K10(30000) + ... = 30000
        assert vals["K10"] == Decimal("30000.00")
        assert vals["K18"] == Decimal("30000.00")

    def test_k18_combines_ordinary_and_farm(self):
        """K18 includes both ordinary business income (K1) and farm (K10)."""
        vals = self._run_formulas({
            # Ordinary income flow: 1a=100000, deductions=0 → Line 21=100000 → K1
            "1a": Decimal("100000"),
            # Farm income: F2=50000, F16=20000 → F34=30000 → K10
            "F2": Decimal("50000"),
            "F16": Decimal("20000"),
        })
        assert vals["K1"] == Decimal("100000.00")
        assert vals["K10"] == Decimal("30000.00")
        assert vals["K18"] == Decimal("130000.00")


# ---------------------------------------------------------------------------
# DB integration tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestScheduleFCompute:
    """End-to-end: seed → create return → set values → compute → verify."""

    def test_compute_return_with_farm_data(self, seeded):
        from apps.returns.compute import compute_return

        firm = Firm.objects.create(name="Test Farm Firm")
        client = Client.objects.create(firm=firm, name="Farm Client")
        entity = Entity.objects.create(client=client, name="Farm S-Corp")
        tax_year = TaxYear.objects.create(entity=entity, year=2025)
        tr = TaxReturn.objects.create(
            form_definition=seeded,
            tax_year=tax_year,
        )

        lines = {
            fl.line_number: fl
            for fl in FormLine.objects.filter(section__form=seeded)
        }

        # Set farm income
        FormFieldValue.objects.create(
            tax_return=tr, form_line=lines["F2"], value="75000"
        )
        # Set farm expenses
        FormFieldValue.objects.create(
            tax_return=tr, form_line=lines["F16"], value="20000"
        )
        FormFieldValue.objects.create(
            tax_return=tr, form_line=lines["F22"], value="10000"
        )

        # Create empty rows for computed fields
        for ln in ["F1c", "F9", "F33", "F34", "K10", "K18",
                    "A6", "A8", "1c", "2", "3", "6", "19", "20", "21",
                    "22c", "23d", "25", "26", "K1"]:
            if ln in lines and not FormFieldValue.objects.filter(
                tax_return=tr, form_line=lines[ln]
            ).exists():
                FormFieldValue.objects.create(
                    tax_return=tr, form_line=lines[ln], value=""
                )

        compute_return(tr)

        def _val(ln):
            return FormFieldValue.objects.get(
                tax_return=tr, form_line=lines[ln]
            ).value

        assert _val("F9") == "75000.00"
        assert _val("F33") == "30000.00"
        assert _val("F34") == "45000.00"
        assert _val("K10") == "45000.00"

    def test_k10_override_preserved(self, seeded):
        """Manual K10 override is not overwritten by farm formula."""
        from apps.returns.compute import compute_return

        firm = Firm.objects.create(name="Test Override Firm")
        client = Client.objects.create(firm=firm, name="Override Client")
        entity = Entity.objects.create(client=client, name="Override S-Corp")
        tax_year = TaxYear.objects.create(entity=entity, year=2025)
        tr = TaxReturn.objects.create(
            form_definition=seeded,
            tax_year=tax_year,
        )

        lines = {
            fl.line_number: fl
            for fl in FormLine.objects.filter(section__form=seeded)
        }

        # Set farm income
        FormFieldValue.objects.create(
            tax_return=tr, form_line=lines["F2"], value="50000"
        )

        # Create computed fields
        for ln in ["F1c", "F9", "F33", "F34",
                    "A6", "A8", "1c", "2", "3", "6", "19", "20", "21",
                    "22c", "23d", "25", "26", "K1", "K18"]:
            if ln in lines and not FormFieldValue.objects.filter(
                tax_return=tr, form_line=lines[ln]
            ).exists():
                FormFieldValue.objects.create(
                    tax_return=tr, form_line=lines[ln], value=""
                )

        # Manually override K10
        fv_k10 = FormFieldValue.objects.create(
            tax_return=tr,
            form_line=lines["K10"],
            value="99999",
            is_overridden=True,
        )

        compute_return(tr)

        fv_k10.refresh_from_db()
        assert fv_k10.value == "99999"  # preserved, not overwritten
