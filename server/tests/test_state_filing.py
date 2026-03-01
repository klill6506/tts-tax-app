"""Tests for multi-state filing support + create_state_return endpoint."""

import pytest
from django.contrib.auth.models import User
from django.test import Client as TestClient

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.management.commands.seed_1120s import Command as Seed1120SCommand
from apps.returns.management.commands.seed_ga600s import Command as SeedGA600SCommand
from apps.returns.models import (
    FormDefinition,
    FormFieldValue,
    TaxReturn,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="State Filing Test Firm")


@pytest.fixture
def user_and_http(firm):
    user = User.objects.create_user(username="state_user", password="testpass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    http = TestClient()
    http.login(username="state_user", password="testpass123")
    return user, http


@pytest.fixture
def entity_ga(firm):
    """Entity with GA state address."""
    client = Client.objects.create(firm=firm, name="GA Client")
    return Entity.objects.create(
        client=client,
        name="GA S-Corp",
        entity_type=EntityType.SCORP,
        state="GA",
    )


@pytest.fixture
def entity_no_state(firm):
    """Entity with no state address."""
    client = Client.objects.create(firm=firm, name="No State Client")
    return Entity.objects.create(
        client=client,
        name="No State S-Corp",
        entity_type=EntityType.SCORP,
        state="",
    )


@pytest.fixture
def seeded_1120s(db):
    cmd = Seed1120SCommand()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="1120-S")


@pytest.fixture
def seeded_ga600s(db):
    cmd = SeedGA600SCommand()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="GA-600S")


@pytest.fixture
def federal_return(entity_ga, seeded_1120s, user_and_http):
    """Create a federal 1120-S return with some income values."""
    user, http = user_and_http
    ty = TaxYear.objects.create(entity=entity_ga, year=2025, filing_states=["GA"])
    resp = http.post(
        "/api/v1/tax-returns/create/",
        {"tax_year": str(ty.id)},
        content_type="application/json",
    )
    assert resp.status_code == 201
    return TaxReturn.objects.get(id=resp.json()["id"])


# ---------------------------------------------------------------------------
# TaxYear.filing_states tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFilingStates:
    def test_default_empty(self, entity_ga):
        """filing_states defaults to empty list."""
        ty = TaxYear.objects.create(entity=entity_ga, year=2025)
        assert ty.filing_states == []

    def test_explicit_states(self, entity_ga):
        """filing_states can be set explicitly."""
        ty = TaxYear.objects.create(
            entity=entity_ga, year=2025, filing_states=["GA", "AL"]
        )
        assert ty.filing_states == ["GA", "AL"]

    def test_api_create_defaults_from_entity_state(self, entity_ga, user_and_http):
        """Creating TaxYear via API defaults filing_states from entity.state."""
        _, http = user_and_http
        resp = http.post(
            "/api/v1/tax-years/",
            {"entity": str(entity_ga.id), "year": 2024},
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filing_states"] == ["GA"]

    def test_api_create_no_state(self, entity_no_state, user_and_http):
        """Creating TaxYear for entity without state → empty filing_states."""
        _, http = user_and_http
        resp = http.post(
            "/api/v1/tax-years/",
            {"entity": str(entity_no_state.id), "year": 2024},
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filing_states"] == []

    def test_api_create_explicit_states(self, entity_ga, user_and_http):
        """Can explicitly set filing_states via API."""
        _, http = user_and_http
        resp = http.post(
            "/api/v1/tax-years/",
            {
                "entity": str(entity_ga.id),
                "year": 2024,
                "filing_states": ["GA", "SC"],
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filing_states"] == ["GA", "SC"]

    def test_serializer_includes_filing_states(self, entity_ga, user_and_http):
        """TaxYear serializer includes filing_states in response."""
        _, http = user_and_http
        ty = TaxYear.objects.create(
            entity=entity_ga, year=2025, filing_states=["GA"]
        )
        resp = http.get(f"/api/v1/tax-years/{ty.id}/")
        assert resp.status_code == 200
        assert "filing_states" in resp.json()
        assert resp.json()["filing_states"] == ["GA"]


# ---------------------------------------------------------------------------
# create_state_return endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateStateReturn:
    def test_create_ga_state_return(
        self, federal_return, seeded_ga600s, user_and_http
    ):
        """POST create-state-return creates a GA-600S linked to federal."""
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{federal_return.id}/create-state-return/",
            {"state": "GA"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["form_code"] == "GA-600S"
        assert data["federal_return_id"] == str(federal_return.id)

    def test_state_return_has_field_values(
        self, federal_return, seeded_ga600s, user_and_http
    ):
        """State return gets all GA-600S form lines pre-populated."""
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{federal_return.id}/create-state-return/",
            {"state": "GA"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.json()
        # GA-600S has 85 lines
        assert len(data["field_values"]) == 85

    def test_ga_ratios_default_to_one(
        self, federal_return, seeded_ga600s, user_and_http
    ):
        """S5_4 (GA ratio) and S3_5 (net worth ratio) default to 1.000000."""
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{federal_return.id}/create-state-return/",
            {"state": "GA"},
            content_type="application/json",
        )
        data = resp.json()
        fv_map = {fv["line_number"]: fv["value"] for fv in data["field_values"]}
        assert fv_map["S5_4"] == "1.000000"
        assert fv_map["S3_5"] == "1.000000"

    def test_duplicate_state_return_409(
        self, federal_return, seeded_ga600s, user_and_http
    ):
        """Creating a duplicate state return returns 409."""
        _, http = user_and_http
        resp1 = http.post(
            f"/api/v1/tax-returns/{federal_return.id}/create-state-return/",
            {"state": "GA"},
            content_type="application/json",
        )
        assert resp1.status_code == 201
        resp2 = http.post(
            f"/api/v1/tax-returns/{federal_return.id}/create-state-return/",
            {"state": "GA"},
            content_type="application/json",
        )
        assert resp2.status_code == 409

    def test_unsupported_state(self, federal_return, user_and_http):
        """Unsupported state returns 400."""
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{federal_return.id}/create-state-return/",
            {"state": "NY"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_invalid_state_code(self, federal_return, user_and_http):
        """Invalid state code returns 400."""
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{federal_return.id}/create-state-return/",
            {"state": "X"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_cannot_create_from_state_return(
        self, federal_return, seeded_ga600s, user_and_http
    ):
        """Cannot create state return from another state return."""
        _, http = user_and_http
        # Create state return first
        resp1 = http.post(
            f"/api/v1/tax-returns/{federal_return.id}/create-state-return/",
            {"state": "GA"},
            content_type="application/json",
        )
        state_return_id = resp1.json()["id"]
        # Try creating state return from state return
        resp2 = http.post(
            f"/api/v1/tax-returns/{state_return_id}/create-state-return/",
            {"state": "GA"},
            content_type="application/json",
        )
        assert resp2.status_code == 400

    def test_state_returns_in_federal_response(
        self, federal_return, seeded_ga600s, user_and_http
    ):
        """Federal return response includes state_returns array."""
        _, http = user_and_http
        # Create state return
        http.post(
            f"/api/v1/tax-returns/{federal_return.id}/create-state-return/",
            {"state": "GA"},
            content_type="application/json",
        )
        # Fetch federal return
        resp = http.get(f"/api/v1/tax-returns/{federal_return.id}/")
        data = resp.json()
        assert "state_returns" in data
        assert len(data["state_returns"]) == 1
        assert data["state_returns"][0]["form_code"] == "GA-600S"

    def test_federal_still_createable_with_state_return(
        self, entity_ga, seeded_1120s, seeded_ga600s, user_and_http
    ):
        """Having a state return doesn't block creating new federal returns
        for other tax years."""
        _, http = user_and_http
        # Create first tax year + federal + state
        ty1 = TaxYear.objects.create(entity=entity_ga, year=2024, filing_states=["GA"])
        resp = http.post(
            "/api/v1/tax-returns/create/",
            {"tax_year": str(ty1.id)},
            content_type="application/json",
        )
        assert resp.status_code == 201
        fed_id = resp.json()["id"]
        http.post(
            f"/api/v1/tax-returns/{fed_id}/create-state-return/",
            {"state": "GA"},
            content_type="application/json",
        )
        # Create second tax year + federal
        ty2 = TaxYear.objects.create(entity=entity_ga, year=2023, filing_states=["GA"])
        resp2 = http.post(
            "/api/v1/tax-returns/create/",
            {"tax_year": str(ty2.id)},
            content_type="application/json",
        )
        assert resp2.status_code == 201


# ---------------------------------------------------------------------------
# GA federal pull-through tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGAFederalPull:
    def test_ordinary_income_pulls_through(
        self, federal_return, seeded_ga600s, user_and_http
    ):
        """Federal Line 21 (ordinary income) pulls to GA S6_1."""
        _, http = user_and_http
        # Set federal Line 21 to 100000 (ordinary income — in deductions section)
        line21_fv = FormFieldValue.objects.filter(
            tax_return=federal_return,
            form_line__line_number="21",
            form_line__section__code="page1_deductions",
        ).first()
        if line21_fv:
            line21_fv.value = "100000.00"
            line21_fv.save()

        # Create state return
        resp = http.post(
            f"/api/v1/tax-returns/{federal_return.id}/create-state-return/",
            {"state": "GA"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.json()
        fv_map = {fv["line_number"]: fv["value"] for fv in data["field_values"]}
        assert fv_map.get("S6_1") == "100000.00"

    def test_schedule_k_pulls_through(
        self, federal_return, seeded_ga600s, user_and_http
    ):
        """Federal Schedule K values pull to GA Schedule 6."""
        _, http = user_and_http
        # Set K4 (interest income) on federal return
        k4_fv = FormFieldValue.objects.filter(
            tax_return=federal_return,
            form_line__line_number="K4",
            form_line__section__code="sched_k",
        ).first()
        if k4_fv:
            k4_fv.value = "5000.00"
            k4_fv.save()

        resp = http.post(
            f"/api/v1/tax-returns/{federal_return.id}/create-state-return/",
            {"state": "GA"},
            content_type="application/json",
        )
        data = resp.json()
        fv_map = {fv["line_number"]: fv["value"] for fv in data["field_values"]}
        assert fv_map.get("S6_4a") == "5000.00"
