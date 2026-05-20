"""Tests for the Dependent model on 1040 returns."""

from datetime import date

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.models import Dependent, FormDefinition, TaxReturn


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Firm Dependents")


@pytest.fixture
def member_user(firm):
    user = User.objects.create_user(username="dep_preparer", password="x")
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
        code="1040", name="Form 1040", tax_year_applicable=2025,
    )


@pytest.fixture
def tax_return_2025(firm, form_1040):
    cl = Client.objects.create(firm=firm, name="Doe, John")
    ent = Entity.objects.create(
        client=cl, name="John Doe", entity_type=EntityType.INDIVIDUAL,
    )
    ty = TaxYear.objects.create(entity=ent, year=2025)
    return TaxReturn.objects.create(
        tax_year=ty,
        form_definition=form_1040,
    )


@pytest.mark.django_db
class TestDependentModel:
    def test_compute_ctc_under_17(self, tax_return_2025):
        dep = Dependent.objects.create(
            tax_return=tax_return_2025,
            first_name="Sally",
            date_of_birth=date(2015, 6, 1),
        )
        assert dep.compute_qualifies_ctc(2025) is True
        assert dep.compute_qualifies_odc(2025) is False

    def test_compute_ctc_age_17_does_not_qualify(self, tax_return_2025):
        dep = Dependent.objects.create(
            tax_return=tax_return_2025,
            date_of_birth=date(2008, 6, 1),
        )
        assert dep.compute_qualifies_ctc(2025) is False
        assert dep.compute_qualifies_odc(2025) is True

    def test_compute_no_dob_returns_false(self, tax_return_2025):
        dep = Dependent.objects.create(tax_return=tax_return_2025)
        assert dep.compute_qualifies_ctc(2025) is False
        assert dep.compute_qualifies_odc(2025) is True

    def test_ctc_override_true_wins(self, tax_return_2025):
        dep = Dependent.objects.create(
            tax_return=tax_return_2025,
            date_of_birth=date(2000, 1, 1),
            ctc_override=True,
        )
        assert dep.compute_qualifies_ctc(2025) is True

    def test_ctc_override_false_wins(self, tax_return_2025):
        dep = Dependent.objects.create(
            tax_return=tax_return_2025,
            date_of_birth=date(2020, 1, 1),
            ctc_override=False,
        )
        assert dep.compute_qualifies_ctc(2025) is False


@pytest.mark.django_db
class TestDependentCRUD:
    def test_create_dependent(self, client_api, tax_return_2025):
        resp = client_api.post(
            f"/api/v1/tax-returns/{tax_return_2025.id}/dependents/",
            {
                "first_name": "Alex",
                "last_name": "Doe",
                "ssn": "123-45-6789",
                "relationship": "Son",
                "date_of_birth": "2015-06-01",
            },
            format="json",
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["first_name"] == "Alex"
        assert body["qualifies_ctc"] is True
        assert body["qualifies_odc"] is False

    def test_list_dependents_orders_by_order_then_created(
        self, client_api, tax_return_2025
    ):
        Dependent.objects.create(tax_return=tax_return_2025, first_name="A", order=2)
        Dependent.objects.create(tax_return=tax_return_2025, first_name="B", order=1)
        resp = client_api.get(
            f"/api/v1/tax-returns/{tax_return_2025.id}/dependents/"
        )
        assert resp.status_code == 200
        names = [d["first_name"] for d in resp.json()]
        assert names == ["B", "A"]

    def test_patch_dependent(self, client_api, tax_return_2025):
        dep = Dependent.objects.create(tax_return=tax_return_2025, first_name="A")
        resp = client_api.patch(
            f"/api/v1/tax-returns/{tax_return_2025.id}/dependents/{dep.id}/",
            {"last_name": "Updated"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["last_name"] == "Updated"

    def test_delete_dependent(self, client_api, tax_return_2025):
        dep = Dependent.objects.create(tax_return=tax_return_2025, first_name="A")
        resp = client_api.delete(
            f"/api/v1/tax-returns/{tax_return_2025.id}/dependents/{dep.id}/"
        )
        assert resp.status_code == 204
        assert Dependent.objects.filter(id=dep.id).count() == 0

    def test_firm_scoping(self, client_api, db):
        """User cannot access dependents on a return belonging to another firm."""
        other_firm = Firm.objects.create(name="Other Firm")
        cl = Client.objects.create(firm=other_firm, name="Other")
        ent = Entity.objects.create(
            client=cl, name="Other Entity", entity_type=EntityType.INDIVIDUAL,
        )
        ty = TaxYear.objects.create(entity=ent, year=2025)
        form_def = FormDefinition.objects.create(
            code="1040_other", name="Form 1040 Other", tax_year_applicable=2025,
        )
        other_tr = TaxReturn.objects.create(
            tax_year=ty,
            form_definition=form_def,
        )
        resp = client_api.get(
            f"/api/v1/tax-returns/{other_tr.id}/dependents/"
        )
        assert resp.status_code in (403, 404)
