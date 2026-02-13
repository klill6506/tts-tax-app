import pytest
from django.contrib.auth.models import User
from django.test import Client as TestClient

from apps.clients.models import Client, Entity, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.management.commands.seed_1120s import Command as SeedCommand
from apps.returns.models import (
    FormDefinition,
    FormFieldValue,
    FormLine,
    FormSection,
    TaxReturn,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Returns Test Firm")


@pytest.fixture
def user_and_http(firm):
    user = User.objects.create_user(username="preparer", password="testpass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    http = TestClient()
    http.login(username="preparer", password="testpass123")
    return user, http


@pytest.fixture
def tax_year(firm):
    client = Client.objects.create(firm=firm, name="Returns Client")
    entity = Entity.objects.create(client=client, name="Returns S-Corp")
    return TaxYear.objects.create(entity=entity, year=2025)


@pytest.fixture
def seeded(db):
    """Seed 1120-S form definition."""
    cmd = SeedCommand()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="1120-S")


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSeed:
    def test_seed_creates_form(self, seeded):
        assert seeded.code == "1120-S"
        assert seeded.name == "U.S. Income Tax Return for an S Corporation"

    def test_seed_creates_sections(self, seeded):
        sections = FormSection.objects.filter(form=seeded)
        assert sections.count() == 8

    def test_seed_creates_lines(self, seeded):
        lines = FormLine.objects.filter(section__form=seeded)
        assert lines.count() == 113

    def test_seed_is_idempotent(self, seeded):
        # Run again
        cmd = SeedCommand()
        cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
        cmd.handle()
        cmd.stdout.close()
        assert FormLine.objects.filter(section__form=seeded).count() == 113

    def test_mapping_keys_populated(self, seeded):
        lines_with_keys = FormLine.objects.filter(
            section__form=seeded, mapping_key__gt=""
        )
        # Most lines have mapping keys (except computed ones)
        assert lines_with_keys.count() > 50


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFormDefinitionEndpoints:
    def test_list_form_definitions(self, user_and_http, seeded):
        _, http = user_and_http
        resp = http.get("/api/v1/form-definitions/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["code"] == "1120-S"

    def test_retrieve_form_definition_with_sections(self, user_and_http, seeded):
        _, http = user_and_http
        resp = http.get(f"/api/v1/form-definitions/{seeded.id}/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sections"]) == 8
        # First section should have lines
        assert len(data["sections"][0]["lines"]) > 0

    def test_requires_auth(self, seeded):
        http = TestClient()
        resp = http.get("/api/v1/form-definitions/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestTaxReturnEndpoints:
    def test_create_return(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        resp = http.post(
            "/api/v1/tax-returns/create/",
            data={"tax_year": str(tax_year.id)},
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["form_code"] == "1120-S"
        assert data["status"] == "draft"
        # All 105 lines should have empty field values
        assert len(data["field_values"]) == 113

    def test_create_duplicate_returns_409(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        http.post(
            "/api/v1/tax-returns/create/",
            data={"tax_year": str(tax_year.id)},
            content_type="application/json",
        )
        resp = http.post(
            "/api/v1/tax-returns/create/",
            data={"tax_year": str(tax_year.id)},
            content_type="application/json",
        )
        assert resp.status_code == 409

    def test_list_returns(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        http.post(
            "/api/v1/tax-returns/create/",
            data={"tax_year": str(tax_year.id)},
            content_type="application/json",
        )
        resp = http.get("/api/v1/tax-returns/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_retrieve_return(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        create_resp = http.post(
            "/api/v1/tax-returns/create/",
            data={"tax_year": str(tax_year.id)},
            content_type="application/json",
        )
        return_id = create_resp.json()["id"]
        resp = http.get(f"/api/v1/tax-returns/{return_id}/")
        assert resp.status_code == 200
        assert resp.json()["form_code"] == "1120-S"

    def test_update_fields(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        create_resp = http.post(
            "/api/v1/tax-returns/create/",
            data={"tax_year": str(tax_year.id)},
            content_type="application/json",
        )
        return_id = create_resp.json()["id"]

        # Get a form_line ID from the field values
        field = create_resp.json()["field_values"][0]
        form_line_id = field["form_line"]

        resp = http.patch(
            f"/api/v1/tax-returns/{return_id}/fields/",
            data={"fields": [{"form_line": form_line_id, "value": "810269.97"}]},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == 1

        # Verify the value was saved
        fv = FormFieldValue.objects.get(
            tax_return_id=return_id, form_line_id=form_line_id
        )
        assert fv.value == "810269.97"
        assert fv.is_overridden is True

    def test_wrong_tax_year_returns_404(self, user_and_http, seeded):
        _, http = user_and_http
        import uuid

        resp = http.post(
            "/api/v1/tax-returns/create/",
            data={"tax_year": str(uuid.uuid4())},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_firm_isolation(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        http.post(
            "/api/v1/tax-returns/create/",
            data={"tax_year": str(tax_year.id)},
            content_type="application/json",
        )
        # Another firm's user can't see it
        other_firm = Firm.objects.create(name="Other Firm")
        other_user = User.objects.create_user(username="other", password="testpass123")
        FirmMembership.objects.create(
            user=other_user, firm=other_firm, role=Role.PREPARER
        )
        other_http = TestClient()
        other_http.login(username="other", password="testpass123")
        resp = other_http.get("/api/v1/tax-returns/")
        assert len(resp.json()) == 0
