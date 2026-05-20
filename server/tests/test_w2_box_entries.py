"""Tests for W-2 Box 12 and Box 14 nested entry endpoints."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.models import (
    FormDefinition,
    TaxReturn,
    W2Box12Entry,
    W2Box14Entry,
    W2Income,
)


# ---------------------------------------------------------------------------
# Fixtures — mirror the pattern from test_dependents.py
# ---------------------------------------------------------------------------

@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Firm Box Entries")


@pytest.fixture
def member_user(firm):
    user = User.objects.create_user(username="box_preparer", password="x")
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
        code="1040_box", name="Form 1040 Box Entries", tax_year_applicable=2025,
    )


@pytest.fixture
def tax_return_2025(firm, form_1040):
    cl = Client.objects.create(firm=firm, name="Box, Tester")
    ent = Entity.objects.create(
        client=cl, name="Tester Box", entity_type=EntityType.INDIVIDUAL,
    )
    ty = TaxYear.objects.create(entity=ent, year=2025)
    return TaxReturn.objects.create(
        tax_year=ty,
        form_definition=form_1040,
    )


@pytest.fixture
def w2(tax_return_2025):
    return W2Income.objects.create(
        tax_return=tax_return_2025,
        employer_name="Acme Co",
        wages=50000,
    )


# ---------------------------------------------------------------------------
# Box 12 tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBox12Entries:
    def test_create(self, client_api, tax_return_2025, w2):
        resp = client_api.post(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/{w2.id}/box-12-entries/",
            {"code": "D", "amount": "5000.00"},
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        assert resp.json()["code"] == "D"
        assert resp.json()["amount"] == "5000.00"

    def test_invalid_code_rejected(self, client_api, tax_return_2025, w2):
        resp = client_api.post(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/{w2.id}/box-12-entries/",
            {"code": "ZZ", "amount": "100"},
            format="json",
        )
        assert resp.status_code == 400
        assert "code" in resp.json()

    def test_list(self, client_api, tax_return_2025, w2):
        W2Box12Entry.objects.create(w2_income=w2, code="D", amount=1000)
        W2Box12Entry.objects.create(w2_income=w2, code="W", amount=500)
        resp = client_api.get(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/{w2.id}/box-12-entries/"
        )
        assert resp.status_code == 200
        codes = {e["code"] for e in resp.json()}
        assert codes == {"D", "W"}

    def test_patch(self, client_api, tax_return_2025, w2):
        entry = W2Box12Entry.objects.create(w2_income=w2, code="D", amount=1000)
        resp = client_api.patch(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/{w2.id}/box-12-entries/{entry.id}/",
            {"amount": "2500.00"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["amount"] == "2500.00"

    def test_delete(self, client_api, tax_return_2025, w2):
        entry = W2Box12Entry.objects.create(w2_income=w2, code="D", amount=1000)
        resp = client_api.delete(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/{w2.id}/box-12-entries/{entry.id}/"
        )
        assert resp.status_code == 204
        assert W2Box12Entry.objects.filter(id=entry.id).count() == 0

    def test_over_4_entries_allowed(self, client_api, tax_return_2025, w2):
        """No hard cap on entry count — soft warning lives in UI only."""
        for code in ["D", "W", "DD", "AA", "BB"]:
            resp = client_api.post(
                f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/{w2.id}/box-12-entries/",
                {"code": code, "amount": "100"},
                format="json",
            )
            assert resp.status_code == 201
        assert W2Box12Entry.objects.filter(w2_income=w2).count() == 5

    def test_w2_income_detail_includes_box_12_entries(self, client_api, tax_return_2025, w2):
        """W2IncomeSerializer includes box_12_entries when fetching the full return."""
        W2Box12Entry.objects.create(w2_income=w2, code="D", amount=5000)
        resp = client_api.get(f"/api/v1/tax-returns/{tax_return_2025.id}/")
        assert resp.status_code == 200
        w2_data = resp.json()["w2_incomes"][0]
        assert "box_12_entries" in w2_data
        assert w2_data["box_12_entries"][0]["code"] == "D"


# ---------------------------------------------------------------------------
# Box 14 tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBox14Entries:
    def test_create(self, client_api, tax_return_2025, w2):
        resp = client_api.post(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/{w2.id}/box-14-entries/",
            {"description": "UNION DUES", "amount": "240.00"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["description"] == "UNION DUES"

    def test_free_text_description(self, client_api, tax_return_2025, w2):
        resp = client_api.post(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/{w2.id}/box-14-entries/",
            {"description": "Anything goes here", "amount": "1"},
            format="json",
        )
        assert resp.status_code == 201

    def test_patch(self, client_api, tax_return_2025, w2):
        entry = W2Box14Entry.objects.create(w2_income=w2, description="OLD", amount=100)
        resp = client_api.patch(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/{w2.id}/box-14-entries/{entry.id}/",
            {"description": "NEW", "amount": "200.00"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "NEW"
        assert resp.json()["amount"] == "200.00"

    def test_delete(self, client_api, tax_return_2025, w2):
        entry = W2Box14Entry.objects.create(w2_income=w2, description="RR RETIREMENT", amount=500)
        resp = client_api.delete(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/{w2.id}/box-14-entries/{entry.id}/"
        )
        assert resp.status_code == 204
        assert W2Box14Entry.objects.filter(id=entry.id).count() == 0

    def test_w2_income_detail_includes_box_14_entries(self, client_api, tax_return_2025, w2):
        """W2IncomeSerializer includes box_14_entries when fetching the full return."""
        W2Box14Entry.objects.create(w2_income=w2, description="UNION DUES", amount=240)
        resp = client_api.get(f"/api/v1/tax-returns/{tax_return_2025.id}/")
        assert resp.status_code == 200
        w2_data = resp.json()["w2_incomes"][0]
        assert "box_14_entries" in w2_data
        assert w2_data["box_14_entries"][0]["description"] == "UNION DUES"
