"""Tests for the GET /api/v1/employers/lookup/ autofill endpoint.

Auth pattern follows Session C's lesson learned: APIClient.force_login()
is required (not force_authenticate) so FirmMiddleware can read
request.user from the session and populate request.firm before
IsFirmMember runs.
"""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.employers.models import Employer, EmployerStateAccount
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.models import FormDefinition, TaxReturn, W2Income


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Firm Employers API")


@pytest.fixture
def member_user(firm):
    user = User.objects.create_user(username="emp_preparer", password="x")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    return user


@pytest.fixture
def authed_api(member_user):
    api = APIClient()
    api.force_login(member_user)
    return api


@pytest.fixture
def employer_acme(db):
    return Employer.objects.create(
        ein="12-3456789",
        name="ACME CORP",
        street="123 MAIN ST",
        city="DALLAS",
        state="TX",
        zip="75001",
        source="taxwise_import",
        verified=False,
    )


# ---------------------------------------------------------------------------
# Lookup endpoint — happy path
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLookupSuccess:
    def test_valid_ein_returns_employer(self, authed_api, employer_acme):
        resp = authed_api.get("/api/v1/employers/lookup/", {"ein": "12-3456789"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ein"] == "12-3456789"
        assert body["name"] == "ACME CORP"
        assert body["state"] == "TX"
        assert body["zip"] == "75001"
        assert body["verified"] is False
        assert body["source"] == "taxwise_import"
        assert body["state_accounts"] == []

    def test_unhyphenated_ein_normalized(self, authed_api, employer_acme):
        # Frontend may pass either "12-3456789" or "123456789".
        resp = authed_api.get("/api/v1/employers/lookup/", {"ein": "123456789"})
        assert resp.status_code == 200
        assert resp.json()["ein"] == "12-3456789"

    def test_state_accounts_returned(self, authed_api, employer_acme):
        EmployerStateAccount.objects.create(
            employer=employer_acme, state="GA",
            state_id_number="GA-W-12345", verified=True,
        )
        EmployerStateAccount.objects.create(
            employer=employer_acme, state="SC",
            state_id_number="SC-W-67890", verified=False,
        )
        resp = authed_api.get("/api/v1/employers/lookup/", {"ein": "12-3456789"})
        assert resp.status_code == 200
        accts = resp.json()["state_accounts"]
        assert len(accts) == 2
        states = {a["state"] for a in accts}
        assert states == {"GA", "SC"}
        ga = next(a for a in accts if a["state"] == "GA")
        assert ga["state_id_number"] == "GA-W-12345"
        assert ga["verified"] is True

    def test_verified_flag_flows_through(self, authed_api, db):
        Employer.objects.create(
            ein="55-5555555", name="VERIFIED CO", state="GA", zip="30303",
            verified=True, source="user_entered",
        )
        resp = authed_api.get("/api/v1/employers/lookup/", {"ein": "55-5555555"})
        assert resp.status_code == 200
        assert resp.json()["verified"] is True
        assert resp.json()["source"] == "user_entered"


# ---------------------------------------------------------------------------
# Lookup endpoint — error paths
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLookupErrors:
    def test_unknown_ein_returns_404(self, authed_api):
        resp = authed_api.get("/api/v1/employers/lookup/", {"ein": "99-9999999"})
        assert resp.status_code == 404
        assert "not found" in resp.json()["error"].lower()

    def test_malformed_ein_returns_400(self, authed_api):
        resp = authed_api.get("/api/v1/employers/lookup/", {"ein": "abc"})
        assert resp.status_code == 400
        assert "invalid" in resp.json()["error"].lower()

    def test_too_short_ein_returns_400(self, authed_api):
        resp = authed_api.get("/api/v1/employers/lookup/", {"ein": "12345"})
        assert resp.status_code == 400

    def test_missing_ein_returns_400(self, authed_api):
        resp = authed_api.get("/api/v1/employers/lookup/")
        assert resp.status_code == 400

    def test_empty_ein_returns_400(self, authed_api):
        resp = authed_api.get("/api/v1/employers/lookup/", {"ein": ""})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLookupPermissions:
    def test_unauthenticated_denied(self, db, employer_acme):
        resp = APIClient().get("/api/v1/employers/lookup/", {"ein": "12-3456789"})
        assert resp.status_code in (401, 403)

    def test_authed_no_firm_membership_denied(self, db, employer_acme):
        loner = User.objects.create_user(username="emp_loner", password="x")
        api = APIClient()
        api.force_login(loner)
        resp = api.get("/api/v1/employers/lookup/", {"ein": "12-3456789"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Integration: simulate the full W-2 autofill flow
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAutofillFlow:
    """End-to-end simulation of the W-2 entry UI's autofill behavior:
    1. Frontend looks up EIN  → 200 with employer + state_accounts
    2. Frontend PATCHes the W-2 row with the autofilled snapshot fields
    3. Backend learning loop sees an EIN that already exists; no duplicate
    """

    @pytest.fixture
    def tax_return(self, firm):
        form_1040 = FormDefinition.objects.create(
            code="1040", name="Form 1040", tax_year_applicable=2025,
        )
        client = Client.objects.create(firm=firm, name="Indiv")
        entity = Entity.objects.create(
            client=client, name="Indiv", entity_type=EntityType.INDIVIDUAL,
        )
        ty = TaxYear.objects.create(entity=entity, year=2025)
        return TaxReturn.objects.create(
            tax_year=ty, form_definition=form_1040,
            tax_year_start=date(2025, 1, 1),
            tax_year_end=date(2025, 12, 31),
        )

    def test_full_autofill_flow_with_existing_employer(self, authed_api, employer_acme, tax_return):
        # Pre-populate the employer with a state account so the frontend's
        # Box-15 cache has something to autofill.
        EmployerStateAccount.objects.create(
            employer=employer_acme, state="TX",
            state_id_number="TX-W-99999", source="taxwise_import", verified=True,
        )

        # Step 1: frontend hits the lookup endpoint
        lookup = authed_api.get("/api/v1/employers/lookup/", {"ein": "12-3456789"})
        assert lookup.status_code == 200
        emp = lookup.json()
        assert emp["name"] == "ACME CORP"
        assert len(emp["state_accounts"]) == 1
        cached_state_account = emp["state_accounts"][0]
        assert cached_state_account["state"] == "TX"

        # Step 2: frontend creates a W-2 row, then PATCHes it with the
        # autofilled snapshot fields (mimicking what the W-2 component does).
        create = authed_api.post(
            f"/api/v1/tax-returns/{tax_return.id}/w2-incomes/",
            data={"employer_name": "New Employer", "wages": "0.00",
                  "federal_tax_withheld": "0.00"},
            format="json",
        )
        assert create.status_code == 201
        w2_id = create.json()["id"]

        # PATCH 1: autofill name + address from lookup response
        patch1 = authed_api.patch(
            f"/api/v1/tax-returns/{tax_return.id}/w2-incomes/{w2_id}/",
            data={
                "employer_ein": emp["ein"],
                "employer_name": emp["name"],
                "employer_street": emp["street"],
                "employer_city": emp["city"],
                "employer_state": emp["state"],
                "employer_zip": emp["zip"],
            },
            format="json",
        )
        assert patch1.status_code == 200

        # PATCH 2: user types Box 15 state, frontend autofills state_id_number
        # from cached state_accounts (no extra API call needed).
        patch2 = authed_api.patch(
            f"/api/v1/tax-returns/{tax_return.id}/w2-incomes/{w2_id}/",
            data={
                "state_box15": cached_state_account["state"],
                "state_id_number": cached_state_account["state_id_number"],
            },
            format="json",
        )
        assert patch2.status_code == 200

        # Step 3: verify final state
        w2 = W2Income.objects.get(id=w2_id)
        assert w2.employer_ein == "12-3456789"
        assert w2.employer_name == "ACME CORP"
        assert w2.employer_state == "TX"
        assert w2.state_box15 == "TX"
        assert w2.state_id_number == "TX-W-99999"

        # Learning loop saw the existing employer — no duplicate created
        assert Employer.objects.filter(ein="12-3456789").count() == 1
        # And the existing state_account was preserved (verified=true)
        assert EmployerStateAccount.objects.filter(
            employer=employer_acme, state="TX"
        ).count() == 1

    def test_autofill_flow_with_unknown_ein_creates_new_employer(self, authed_api, tax_return):
        """404 on lookup → user types manually → save creates new employer."""
        # Step 1: lookup returns 404
        lookup = authed_api.get("/api/v1/employers/lookup/", {"ein": "99-9999999"})
        assert lookup.status_code == 404

        # Step 2: user types name + address manually; create + PATCH a W-2 row
        create = authed_api.post(
            f"/api/v1/tax-returns/{tax_return.id}/w2-incomes/",
            data={
                "employer_name": "FRESH EMPLOYER",
                "employer_ein": "99-9999999",
                "employer_street": "1 NEW WAY",
                "employer_city": "AUSTIN",
                "employer_state": "TX",
                "employer_zip": "78701",
                "wages": "30000.00",
                "federal_tax_withheld": "3000.00",
            },
            format="json",
        )
        assert create.status_code == 201

        # Step 3: learning loop created the new Employer
        e = Employer.objects.get(ein="99-9999999")
        assert e.name == "FRESH EMPLOYER"
        assert e.source == "user_entered"
        assert e.verified is False
        assert e.street == "1 NEW WAY"
