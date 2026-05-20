"""Tests for the expanded 1099-INT InterestIncome model (Commit 2)."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.compute import aggregate_1040_income
from apps.returns.models import (
    FormDefinition,
    FormFieldValue,
    InterestIncome,
    TaxReturn,
)


# ---------------------------------------------------------------------------
# Fixtures — mirror test_dependents.py pattern exactly
# ---------------------------------------------------------------------------


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Firm Interest")


@pytest.fixture
def member_user(firm):
    user = User.objects.create_user(username="int_preparer", password="x")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    return user


@pytest.fixture
def client_api(member_user):
    c = APIClient()
    c.force_login(member_user)
    return c


@pytest.fixture
def form_1040(db):
    return FormDefinition.objects.create(
        code="1040_int", name="Form 1040 Interest", tax_year_applicable=2025,
    )


@pytest.fixture
def tax_return_2025(firm, form_1040):
    cl = Client.objects.create(firm=firm, name="Smith, Jane")
    ent = Entity.objects.create(
        client=cl, name="Jane Smith", entity_type=EntityType.INDIVIDUAL,
    )
    ty = TaxYear.objects.create(entity=ent, year=2025)
    return TaxReturn.objects.create(
        tax_year=ty,
        form_definition=form_1040,
    )


@pytest.fixture
def setup_1040(firm, member_user, form_1040, tax_return_2025):
    """Combined fixture that mirrors the setup_1040 dict contract in the spec."""
    return {
        "user": member_user,
        "firm": firm,
        "tax_return": tax_return_2025,
    }


# ---------------------------------------------------------------------------
# Serializer / API tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExpandedInterestIncomeSerializer:
    def test_create_with_all_boxes(self, client_api, setup_1040):
        tr = setup_1040["tax_return"]
        payload = {
            "payer_name": "Wells Fargo Bank",
            "payer_ein": "94-1234567",
            "payer_street": "123 Test Blvd",
            "payer_city": "Test City",
            "payer_state": "CA",
            "payer_zip": "00000",
            "interest_income": "1500.00",
            "early_withdrawal_penalty": "25.00",
            "treasury_interest": "300.00",
            "federal_tax_withheld": "150.00",
            "tax_exempt_interest": "100.00",
            "state_code": "GA",
            "state_id_number": "12345",
            "state_tax_withheld": "75.00",
        }
        resp = client_api.post(
            f"/api/v1/tax-returns/{tr.id}/interest-incomes/",
            payload,
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["payer_name"] == "Wells Fargo Bank"
        assert body["payer_ein"] == "94-1234567"
        assert body["interest_income"] == "1500.00"
        assert body["tax_exempt_interest"] == "100.00"
        assert body["treasury_interest"] == "300.00"
        assert body["state_tax_withheld"] == "75.00"

    def test_minimal_fields_default_zero(self, client_api, setup_1040):
        tr = setup_1040["tax_return"]
        resp = client_api.post(
            f"/api/v1/tax-returns/{tr.id}/interest-incomes/",
            {"payer_name": "Local Credit Union"},
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["interest_income"] == "0.00"
        assert body["tax_exempt_interest"] == "0.00"
        # Optional (nullable) boxes should be null when not provided
        assert body["early_withdrawal_penalty"] is None
        assert body["federal_tax_withheld"] is None
        assert body["state_tax_withheld"] is None

    def test_nullable_boxes_accept_values(self, client_api, setup_1040):
        tr = setup_1040["tax_return"]
        resp = client_api.post(
            f"/api/v1/tax-returns/{tr.id}/interest-incomes/",
            {
                "payer_name": "Bond Fund",
                "bond_premium": "12.50",
                "market_discount": "3.00",
                "pab_interest": "200.00",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["bond_premium"] == "12.50"
        assert body["market_discount"] == "3.00"
        assert body["pab_interest"] == "200.00"

    def test_payer_address_snapshot_fields_present(self, client_api, setup_1040):
        tr = setup_1040["tax_return"]
        resp = client_api.post(
            f"/api/v1/tax-returns/{tr.id}/interest-incomes/",
            {
                "payer_name": "US Treasury",
                "payer_street": "1500 Pennsylvania Ave",
                "payer_city": "Washington",
                "payer_state": "DC",
                "payer_zip": "20220",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["payer_street"] == "1500 Pennsylvania Ave"
        assert body["payer_city"] == "Washington"
        assert body["payer_state"] == "DC"
        assert body["payer_zip"] == "20220"

    def test_old_fields_amount_and_is_tax_exempt_absent(self, client_api, setup_1040):
        """Confirm the old shape is gone from the API response."""
        tr = setup_1040["tax_return"]
        resp = client_api.post(
            f"/api/v1/tax-returns/{tr.id}/interest-incomes/",
            {"payer_name": "Any Bank"},
            format="json",
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "amount" not in body
        assert "is_tax_exempt" not in body

    def test_patch_updates_single_box(self, client_api, setup_1040):
        tr = setup_1040["tax_return"]
        ii = InterestIncome.objects.create(
            tax_return=tr, payer_name="Patch Bank", interest_income=Decimal("500"),
        )
        resp = client_api.patch(
            f"/api/v1/tax-returns/{tr.id}/interest-incomes/{ii.id}/",
            {"federal_tax_withheld": "50.00"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["federal_tax_withheld"] == "50.00"

    def test_delete_removes_record(self, client_api, setup_1040):
        tr = setup_1040["tax_return"]
        ii = InterestIncome.objects.create(tax_return=tr, payer_name="Delete Me")
        resp = client_api.delete(
            f"/api/v1/tax-returns/{tr.id}/interest-incomes/{ii.id}/"
        )
        assert resp.status_code == 204
        assert InterestIncome.objects.filter(id=ii.id).count() == 0


# ---------------------------------------------------------------------------
# aggregate_1040_income — Line 2a / 2b split
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAggregateInterestIncomeSplit:
    def _seed_form_lines(self, tax_return):
        """Ensure FormLine + FormFieldValue rows for 2a and 2b exist.

        _set_field_value() does a get() on existing FormFieldValue rows — it
        never creates them. Production returns are pre-seeded by seed_1040;
        in tests we build the rows manually so the function can write to them.
        """
        from apps.returns.models import FormFieldValue, FormLine, FormSection
        fd = tax_return.form_definition
        # FormSection FK is `form`, unique_together is (form, code)
        section, _ = FormSection.objects.get_or_create(
            form=fd,
            code="page1_income",
            defaults={"title": "Income", "sort_order": 1},
        )
        for i, line_num in enumerate(("2a", "2b")):
            fl, _ = FormLine.objects.get_or_create(
                section=section,
                line_number=line_num,
                defaults={
                    "label": f"Line {line_num}",
                    "is_computed": False,
                    "sort_order": i,
                },
            )
            FormFieldValue.objects.get_or_create(
                tax_return=tax_return,
                form_line=fl,
                defaults={"value": "0.00"},
            )

    def test_lines_2a_and_2b_separately(self, tax_return_2025):
        tr = tax_return_2025
        self._seed_form_lines(tr)

        InterestIncome.objects.create(
            tax_return=tr, payer_name="A",
            interest_income=Decimal("100"), tax_exempt_interest=Decimal("0"),
        )
        InterestIncome.objects.create(
            tax_return=tr, payer_name="B",
            interest_income=Decimal("0"), tax_exempt_interest=Decimal("50"),
        )
        InterestIncome.objects.create(
            tax_return=tr, payer_name="C — both",
            interest_income=Decimal("200"), tax_exempt_interest=Decimal("75"),
        )
        aggregate_1040_income(tr)

        line_2a = FormFieldValue.objects.get(
            tax_return=tr, form_line__line_number="2a",
        ).value
        line_2b = FormFieldValue.objects.get(
            tax_return=tr, form_line__line_number="2b",
        ).value
        assert Decimal(line_2a) == Decimal("125.00")   # 50 + 75
        assert Decimal(line_2b) == Decimal("300.00")   # 100 + 200

    def test_all_taxable_no_exempt(self, tax_return_2025):
        tr = tax_return_2025
        self._seed_form_lines(tr)
        InterestIncome.objects.create(
            tax_return=tr, payer_name="Bank",
            interest_income=Decimal("999"), tax_exempt_interest=Decimal("0"),
        )
        aggregate_1040_income(tr)
        assert Decimal(FormFieldValue.objects.get(
            tax_return=tr, form_line__line_number="2b").value) == Decimal("999.00")
        assert Decimal(FormFieldValue.objects.get(
            tax_return=tr, form_line__line_number="2a").value) == Decimal("0.00")

    def test_no_interest_income_zeros_both_lines(self, tax_return_2025):
        tr = tax_return_2025
        self._seed_form_lines(tr)
        aggregate_1040_income(tr)
        assert Decimal(FormFieldValue.objects.get(
            tax_return=tr, form_line__line_number="2a").value) == Decimal("0.00")
        assert Decimal(FormFieldValue.objects.get(
            tax_return=tr, form_line__line_number="2b").value) == Decimal("0.00")

    def test_box_3_treasury_interest_flows_to_line_2b(self, setup_1040):
        """Treasury interest (Box 3) is taxable — must flow to Line 2b alongside Box 1."""
        tr = setup_1040["tax_return"]
        self._seed_form_lines(tr)
        InterestIncome.objects.create(
            tax_return=tr, payer_name="Treasury Direct",
            interest_income=Decimal("0"),
            treasury_interest=Decimal("500"),
            tax_exempt_interest=Decimal("0"),
        )
        aggregate_1040_income(tr)
        line_2b = FormFieldValue.objects.get(
            tax_return=tr, form_line__line_number="2b",
        ).value
        assert Decimal(line_2b) == Decimal("500.00")
