"""Tests for the expanded W-2 flat field surface (Commit 3)."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.models import FormDefinition, TaxReturn, W2Income


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Firm W2 Expansion")


@pytest.fixture
def member_user(firm):
    user = User.objects.create_user(username="w2exp_preparer", password="x")
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
        code="1040_w2exp", name="Form 1040 W2 Expansion Test", tax_year_applicable=2025,
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


@pytest.mark.django_db
class TestW2FlatExpansion:
    def test_create_with_new_fields(self, client_api, tax_return_2025):
        resp = client_api.post(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/",
            {
                "employer_name": "Acme Co",
                "wages": "50000.00",
                "social_security_tips": "100.00",
                "allocated_tips": "50.00",
                "dependent_care_benefits": "5000.00",
                "nonqualified_plans": "1000.00",
                "statutory_employee": True,
                "retirement_plan": True,
                "third_party_sick_pay": False,
                "local_wages": "50000.00",
                "local_income_tax": "500.00",
                "locality_name": "Athens-Clarke",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["social_security_tips"] == "100.00"
        assert body["allocated_tips"] == "50.00"
        assert body["dependent_care_benefits"] == "5000.00"
        assert body["nonqualified_plans"] == "1000.00"
        assert body["statutory_employee"] is True
        assert body["retirement_plan"] is True
        assert body["third_party_sick_pay"] is False
        assert body["local_wages"] == "50000.00"
        assert body["local_income_tax"] == "500.00"
        assert body["locality_name"] == "Athens-Clarke"

    def test_defaults(self, client_api, tax_return_2025):
        resp = client_api.post(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/",
            {"employer_name": "Minimal Co"},
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["social_security_tips"] is None
        assert body["allocated_tips"] is None
        assert body["dependent_care_benefits"] is None
        assert body["nonqualified_plans"] is None
        assert body["statutory_employee"] is False
        assert body["retirement_plan"] is False
        assert body["third_party_sick_pay"] is False
        assert body["local_wages"] is None
        assert body["local_income_tax"] is None
        assert body["locality_name"] == ""

    def test_box_13_booleans_persist_independently(self, client_api, tax_return_2025):
        """Box 13 has three independent checkboxes — toggle each separately."""
        resp = client_api.post(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/",
            {
                "employer_name": "BoxThirteen Co",
                "statutory_employee": True,
                "retirement_plan": False,
                "third_party_sick_pay": True,
            },
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["statutory_employee"] is True
        assert body["retirement_plan"] is False
        assert body["third_party_sick_pay"] is True

        # Verify patch doesn't cross-contaminate the three flags
        w2_id = body["id"]
        patch_resp = client_api.patch(
            f"/api/v1/tax-returns/{tax_return_2025.id}/w2-incomes/{w2_id}/",
            {"retirement_plan": True},
            format="json",
        )
        assert patch_resp.status_code == 200
        patched = patch_resp.json()
        assert patched["statutory_employee"] is True      # unchanged
        assert patched["retirement_plan"] is True          # updated
        assert patched["third_party_sick_pay"] is True    # unchanged
