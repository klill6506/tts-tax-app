"""Tests for Disposition model and API endpoints."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client as TestClient

from apps.clients.models import Client, Entity, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.management.commands.seed_1120s import Command as SeedCommand
from apps.returns.models import Disposition, FormDefinition, TaxReturn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Disp Test Firm")


@pytest.fixture
def user_and_http(firm):
    user = User.objects.create_user(username="disp_prep", password="testpass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    http = TestClient()
    http.login(username="disp_prep", password="testpass123")
    return user, http


@pytest.fixture
def seeded(db):
    cmd = SeedCommand()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="1120-S")


@pytest.fixture
def tax_return(firm, seeded):
    client = Client.objects.create(firm=firm, name="Disp Client")
    entity = Entity.objects.create(client=client, name="Disp Corp")
    ty = TaxYear.objects.create(entity=entity, year=2025)
    return TaxReturn.objects.create(tax_year=ty, form_definition=seeded)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestDispositionModel:
    def test_gain_loss_positive(self, tax_return):
        d = Disposition.objects.create(
            tax_return=tax_return,
            description="Office Building",
            sales_price=Decimal("100000"),
            cost_basis=Decimal("60000"),
            expenses_of_sale=Decimal("5000"),
        )
        assert d.gain_loss == Decimal("35000")

    def test_gain_loss_negative(self, tax_return):
        d = Disposition.objects.create(
            tax_return=tax_return,
            description="Equipment",
            sales_price=Decimal("10000"),
            cost_basis=Decimal("25000"),
            expenses_of_sale=Decimal("1000"),
        )
        assert d.gain_loss == Decimal("-16000")

    def test_gain_loss_zero(self, tax_return):
        d = Disposition.objects.create(
            tax_return=tax_return,
            description="Vehicle",
            sales_price=Decimal("20000"),
            cost_basis=Decimal("18000"),
            expenses_of_sale=Decimal("2000"),
        )
        assert d.gain_loss == Decimal("0")

    def test_multiple_dispositions(self, tax_return):
        Disposition.objects.create(
            tax_return=tax_return,
            description="Asset 1",
            sales_price=Decimal("50000"),
            cost_basis=Decimal("30000"),
        )
        Disposition.objects.create(
            tax_return=tax_return,
            description="Asset 2",
            sales_price=Decimal("20000"),
            cost_basis=Decimal("25000"),
        )
        assert tax_return.dispositions.count() == 2

    def test_various_dates(self, tax_return):
        d = Disposition.objects.create(
            tax_return=tax_return,
            description="Stock Portfolio",
            date_acquired_various=True,
            date_sold_various=True,
            sales_price=Decimal("50000"),
            cost_basis=Decimal("40000"),
        )
        assert d.date_acquired is None
        assert d.date_acquired_various is True
        assert d.date_sold is None
        assert d.date_sold_various is True

    def test_default_term_is_long(self, tax_return):
        d = Disposition.objects.create(
            tax_return=tax_return,
            description="Land",
            sales_price=Decimal("100000"),
            cost_basis=Decimal("80000"),
        )
        assert d.term == "long"


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


class TestDispositionAPI:
    def test_create_disposition(self, user_and_http, tax_return):
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{tax_return.id}/dispositions/",
            data={
                "description": "Warehouse",
                "sales_price": "200000.00",
                "cost_basis": "150000.00",
                "expenses_of_sale": "10000.00",
                "term": "long",
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["description"] == "Warehouse"
        assert data["gain_loss"] == "40000.00"

    def test_list_dispositions(self, user_and_http, tax_return):
        _, http = user_and_http
        Disposition.objects.create(
            tax_return=tax_return,
            description="Asset A",
            sales_price=Decimal("10000"),
            cost_basis=Decimal("5000"),
        )
        Disposition.objects.create(
            tax_return=tax_return,
            description="Asset B",
            sales_price=Decimal("20000"),
            cost_basis=Decimal("15000"),
        )
        resp = http.get(f"/api/v1/tax-returns/{tax_return.id}/dispositions/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_update_disposition(self, user_and_http, tax_return):
        _, http = user_and_http
        d = Disposition.objects.create(
            tax_return=tax_return,
            description="Old Name",
            sales_price=Decimal("10000"),
            cost_basis=Decimal("5000"),
        )
        resp = http.patch(
            f"/api/v1/tax-returns/{tax_return.id}/dispositions/{d.id}/",
            data={"description": "New Name", "sales_price": "15000.00"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "New Name"
        assert resp.json()["gain_loss"] == "10000.00"

    def test_delete_disposition(self, user_and_http, tax_return):
        _, http = user_and_http
        d = Disposition.objects.create(
            tax_return=tax_return,
            description="To Delete",
            sales_price=Decimal("10000"),
            cost_basis=Decimal("5000"),
        )
        resp = http.delete(
            f"/api/v1/tax-returns/{tax_return.id}/dispositions/{d.id}/"
        )
        assert resp.status_code == 204
        assert Disposition.objects.filter(id=d.id).count() == 0

    def test_dispositions_in_return_data(self, user_and_http, tax_return):
        _, http = user_and_http
        Disposition.objects.create(
            tax_return=tax_return,
            description="Included Asset",
            sales_price=Decimal("50000"),
            cost_basis=Decimal("30000"),
        )
        resp = http.get(f"/api/v1/tax-returns/{tax_return.id}/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["dispositions"]) == 1
        assert data["dispositions"][0]["description"] == "Included Asset"
