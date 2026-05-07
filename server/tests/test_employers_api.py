"""Tests for the GET /api/v1/employers/lookup/ autofill endpoint.

Auth pattern follows Session C's lesson learned: APIClient.force_login()
is required (not force_authenticate) so FirmMiddleware can read
request.user from the session and populate request.firm before
IsFirmMember runs.
"""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.employers.models import Employer, EmployerStateAccount
from apps.firms.models import Firm, FirmMembership, Role


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
