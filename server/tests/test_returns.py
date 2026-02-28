import json
import uuid
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client as TestClient

from apps.clients.models import Client, Entity, EntityType, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.compute import compute_return
from apps.returns.management.commands.seed_1065 import Command as Seed1065Command
from apps.returns.management.commands.seed_1120 import Command as Seed1120Command
from apps.returns.management.commands.seed_1120s import Command as SeedCommand
from apps.returns.models import (
    FormDefinition,
    FormFieldValue,
    FormLine,
    FormSection,
    Officer,
    OtherDeduction,
    Shareholder,
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
        assert sections.count() == 9

    def test_seed_creates_lines(self, seeded):
        lines = FormLine.objects.filter(section__form=seeded)
        assert lines.count() == 133

    def test_seed_is_idempotent(self, seeded):
        # Run again
        cmd = SeedCommand()
        cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
        cmd.handle()
        cmd.stdout.close()
        assert FormLine.objects.filter(section__form=seeded).count() == 130

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
        assert len(data["sections"]) == 9
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
        # All form lines should have field values (113 non-B + 17 Schedule B = 130)
        assert len(data["field_values"]) == 130

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

    def test_list_returns_includes_entity_type(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        _create_return(http, tax_year.id)
        resp = http.get("/api/v1/tax-returns/")
        assert resp.status_code == 200
        data = resp.json()[0]
        assert data["entity_type"] == "scorp"
        assert "client_id" in data
        assert "entity_id" in data

    def test_list_returns_filter_by_status(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        _create_return(http, tax_year.id)
        resp = http.get("/api/v1/tax-returns/?status=draft")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        resp = http.get("/api/v1/tax-returns/?status=filed")
        assert len(resp.json()) == 0

    def test_list_returns_filter_by_year(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        _create_return(http, tax_year.id)
        resp = http.get("/api/v1/tax-returns/?year=2025")
        assert len(resp.json()) == 1
        resp = http.get("/api/v1/tax-returns/?year=2024")
        assert len(resp.json()) == 0

    def test_list_returns_filter_by_form_code(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        _create_return(http, tax_year.id)
        resp = http.get("/api/v1/tax-returns/?form_code=1120-S")
        assert len(resp.json()) == 1
        resp = http.get("/api/v1/tax-returns/?form_code=1065")
        assert len(resp.json()) == 0

    def test_list_returns_search(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        _create_return(http, tax_year.id)
        resp = http.get("/api/v1/tax-returns/?search=Returns")
        assert len(resp.json()) == 1
        resp = http.get("/api/v1/tax-returns/?search=nonexistent")
        assert len(resp.json()) == 0

    def test_delete_return(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        resp = _create_return(http, tax_year.id)
        rid = resp.json()["id"]
        del_resp = http.delete(f"/api/v1/tax-returns/{rid}/")
        assert del_resp.status_code == 204
        assert TaxReturn.objects.filter(id=rid).count() == 0

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


# ---------------------------------------------------------------------------
# Additional fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded_1065(db):
    """Seed 1065 form definition."""
    cmd = Seed1065Command()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="1065")


@pytest.fixture
def seeded_1120(db):
    """Seed 1120 form definition."""
    cmd = Seed1120Command()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="1120")


@pytest.fixture
def partnership_tax_year(firm):
    """Tax year for a partnership entity (maps to 1065)."""
    client = Client.objects.create(firm=firm, name="Partnership Client")
    entity = Entity.objects.create(
        client=client, name="Test Partnership", entity_type=EntityType.PARTNERSHIP,
    )
    return TaxYear.objects.create(entity=entity, year=2025)


@pytest.fixture
def ccorp_tax_year(firm):
    """Tax year for a C-Corp entity (maps to 1120)."""
    client = Client.objects.create(firm=firm, name="C-Corp Client")
    entity = Entity.objects.create(
        client=client, name="Test C-Corp", entity_type=EntityType.CCORP,
    )
    return TaxYear.objects.create(entity=entity, year=2025)


@pytest.fixture
def trust_tax_year(firm):
    """Tax year for a trust entity (not yet supported)."""
    client = Client.objects.create(firm=firm, name="Trust Client")
    entity = Entity.objects.create(
        client=client, name="Test Trust", entity_type=EntityType.TRUST,
    )
    return TaxYear.objects.create(entity=entity, year=2025)


def _create_return(http, tax_year_id):
    """Helper to create a return via API."""
    return http.post(
        "/api/v1/tax-returns/create/",
        data={"tax_year": str(tax_year_id)},
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# Form selection by entity type
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFormSelection:
    def test_scorp_gets_1120s(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        resp = _create_return(http, tax_year.id)
        assert resp.status_code == 201
        assert resp.json()["form_code"] == "1120-S"

    def test_partnership_gets_1065(self, user_and_http, seeded_1065, partnership_tax_year):
        _, http = user_and_http
        resp = _create_return(http, partnership_tax_year.id)
        assert resp.status_code == 201
        assert resp.json()["form_code"] == "1065"
        assert len(resp.json()["field_values"]) == 97

    def test_ccorp_gets_1120(self, user_and_http, seeded_1120, ccorp_tax_year):
        _, http = user_and_http
        resp = _create_return(http, ccorp_tax_year.id)
        assert resp.status_code == 201
        assert resp.json()["form_code"] == "1120"
        assert len(resp.json()["field_values"]) == 172

    def test_trust_returns_400(self, user_and_http, seeded, trust_tax_year):
        _, http = user_and_http
        resp = _create_return(http, trust_tax_year.id)
        assert resp.status_code == 400
        assert "not yet supported" in resp.json()["error"]


# ---------------------------------------------------------------------------
# Other Deductions CRUD + rollup
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOtherDeductions:
    def _setup_return(self, http, seeded, tax_year):
        resp = _create_return(http, tax_year.id)
        return resp.json()["id"]

    def test_standard_deductions_prepopulated(self, user_and_http, seeded, tax_year):
        """New returns come pre-populated with standard deduction categories."""
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.get(f"/api/v1/tax-returns/{rid}/other-deductions/")
        assert resp.status_code == 200
        data = resp.json()
        # Should have 27 standard deduction presets
        assert len(data) == 27
        # All should have zero amounts and source=standard
        for d in data:
            assert d["amount"] == "0.00"
            assert d["source"] == "standard"
        # Check a few specific categories are present
        descriptions = {d["description"] for d in data}
        assert "Accounting" in descriptions
        assert "Supplies" in descriptions
        assert "Travel" in descriptions
        assert "Utilities" in descriptions

    def test_schedule_b_defaults(self, user_and_http, seeded, tax_year):
        """New returns have Schedule B questions defaulted to No (Lacerte approach)."""
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.get(f"/api/v1/tax-returns/{rid}/")
        assert resp.status_code == 200
        data = resp.json()
        # Find all Schedule B fields
        b_fields = [
            fv for fv in data["field_values"]
            if fv["section_code"] == "sched_b"
        ]
        assert len(b_fields) == 17  # B3-B16 + B4a/b, B5a/b, B14a/b
        # All boolean fields should default to "false"
        bool_fields = [f for f in b_fields if f["field_type"] == "boolean"]
        for fv in bool_fields:
            assert fv["value"] == "false", f"{fv['line_number']} should default to false"
        # B8 (currency) should default to "0.00"
        b8 = next((f for f in b_fields if f["line_number"] == "B8"), None)
        assert b8 is not None
        assert b8["value"] == "0.00"

    def test_create_deduction(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.post(
            f"/api/v1/tax-returns/{rid}/other-deductions/",
            data={"description": "Office Expense", "amount": "1500.00", "category": "Office Expense"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["description"] == "Office Expense"
        assert resp.json()["amount"] == "1500.00"

    def test_create_deduction_rollup(self, user_and_http, seeded, tax_year):
        """Creating deductions should auto-rollup to Line 19."""
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        # Add two deductions
        http.post(
            f"/api/v1/tax-returns/{rid}/other-deductions/",
            data={"description": "Supplies", "amount": "250.00"},
            content_type="application/json",
        )
        http.post(
            f"/api/v1/tax-returns/{rid}/other-deductions/",
            data={"description": "Travel", "amount": "750.00"},
            content_type="application/json",
        )
        # Check that Line 19 has 1000.00
        fv = FormFieldValue.objects.get(
            tax_return_id=rid,
            form_line__mapping_key="1120S_L19",
        )
        assert fv.value == "1000.00"

    def test_update_deduction(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        create_resp = http.post(
            f"/api/v1/tax-returns/{rid}/other-deductions/",
            data={"description": "Supplies", "amount": "100.00"},
            content_type="application/json",
        )
        ded_id = create_resp.json()["id"]
        resp = http.patch(
            f"/api/v1/tax-returns/{rid}/other-deductions/{ded_id}/",
            data={"amount": "200.00"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["amount"] == "200.00"
        # Rollup should reflect new amount
        fv = FormFieldValue.objects.get(
            tax_return_id=rid, form_line__mapping_key="1120S_L19",
        )
        assert fv.value == "200.00"

    def test_delete_deduction(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp1 = http.post(
            f"/api/v1/tax-returns/{rid}/other-deductions/",
            data={"description": "Supplies", "amount": "300.00"},
            content_type="application/json",
        )
        ded_id = resp1.json()["id"]
        resp = http.delete(f"/api/v1/tax-returns/{rid}/other-deductions/{ded_id}/")
        assert resp.status_code == 204
        # Rollup should be 0
        fv = FormFieldValue.objects.get(
            tax_return_id=rid, form_line__mapping_key="1120S_L19",
        )
        assert fv.value == "0.00"

    def test_deduction_categories_endpoint(self, user_and_http, seeded):
        _, http = user_and_http
        resp = http.get("/api/v1/tax-returns/deduction-categories/")
        assert resp.status_code == 200
        data = resp.json()
        assert "Amortization" in data
        assert "Other Deductions" in data
        assert len(data) == 34


# ---------------------------------------------------------------------------
# Officers CRUD
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOfficers:
    def _setup_return(self, http, seeded, tax_year):
        resp = _create_return(http, tax_year.id)
        return resp.json()["id"]

    def test_list_empty_officers(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.get(f"/api/v1/tax-returns/{rid}/officers/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_officer(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.post(
            f"/api/v1/tax-returns/{rid}/officers/",
            data={
                "name": "John Smith",
                "title": "President",
                "ssn": "123-45-6789",
                "percent_ownership": "100.00",
                "compensation": "150000.00",
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "John Smith"
        assert resp.json()["title"] == "President"

    def test_update_officer(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        create_resp = http.post(
            f"/api/v1/tax-returns/{rid}/officers/",
            data={"name": "Jane Doe", "title": "VP"},
            content_type="application/json",
        )
        oid = create_resp.json()["id"]
        resp = http.patch(
            f"/api/v1/tax-returns/{rid}/officers/{oid}/",
            data={"title": "CEO"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "CEO"

    def test_delete_officer(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        create_resp = http.post(
            f"/api/v1/tax-returns/{rid}/officers/",
            data={"name": "To Delete"},
            content_type="application/json",
        )
        oid = create_resp.json()["id"]
        resp = http.delete(f"/api/v1/tax-returns/{rid}/officers/{oid}/")
        assert resp.status_code == 204
        assert Officer.objects.filter(id=oid).count() == 0


# ---------------------------------------------------------------------------
# Shareholders CRUD
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestShareholders:
    def _setup_return(self, http, seeded, tax_year):
        resp = _create_return(http, tax_year.id)
        return resp.json()["id"]

    def test_list_empty_shareholders(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.get(f"/api/v1/tax-returns/{rid}/shareholders/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_shareholder(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.post(
            f"/api/v1/tax-returns/{rid}/shareholders/",
            data={
                "name": "Alice Johnson",
                "ssn": "111-22-3333",
                "ownership_percentage": "50.0000",
                "beginning_shares": 100,
                "ending_shares": 100,
                "city": "Dallas",
                "state": "TX",
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Alice Johnson"
        assert resp.json()["ownership_percentage"] == "50.0000"

    def test_update_shareholder(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        create_resp = http.post(
            f"/api/v1/tax-returns/{rid}/shareholders/",
            data={"name": "Bob", "ownership_percentage": "25.0000"},
            content_type="application/json",
        )
        sh_id = create_resp.json()["id"]
        resp = http.patch(
            f"/api/v1/tax-returns/{rid}/shareholders/{sh_id}/",
            data={"ownership_percentage": "75.0000"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["ownership_percentage"] == "75.0000"

    def test_delete_shareholder(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        create_resp = http.post(
            f"/api/v1/tax-returns/{rid}/shareholders/",
            data={"name": "To Delete"},
            content_type="application/json",
        )
        sh_id = create_resp.json()["id"]
        resp = http.delete(f"/api/v1/tax-returns/{rid}/shareholders/{sh_id}/")
        assert resp.status_code == 204

    def test_shareholders_in_return_data(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        http.post(
            f"/api/v1/tax-returns/{rid}/shareholders/",
            data={"name": "Included SH", "ownership_percentage": "100.0000"},
            content_type="application/json",
        )
        resp = http.get(f"/api/v1/tax-returns/{rid}/")
        data = resp.json()
        assert len(data["shareholders"]) == 1
        assert data["shareholders"][0]["name"] == "Included SH"


# ---------------------------------------------------------------------------
# Rental Properties CRUD (Form 8825)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRentalProperties:
    def _setup_return(self, http, seeded, tax_year):
        resp = _create_return(http, tax_year.id)
        return resp.json()["id"]

    def test_list_empty_properties(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.get(f"/api/v1/tax-returns/{rid}/rental-properties/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_rental_property(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.post(
            f"/api/v1/tax-returns/{rid}/rental-properties/",
            data={
                "description": "123 Main St",
                "property_type": "4",
                "rents_received": "24000.00",
                "insurance": "1200.00",
                "taxes": "3000.00",
                "depreciation": "5000.00",
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["description"] == "123 Main St"
        assert data["total_expenses"] == "9200.00"
        assert data["net_rent"] == "14800.00"

    def test_rental_rollup_to_k2(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        http.post(
            f"/api/v1/tax-returns/{rid}/rental-properties/",
            data={"description": "Prop A", "rents_received": "10000.00", "taxes": "2000.00"},
            content_type="application/json",
        )
        http.post(
            f"/api/v1/tax-returns/{rid}/rental-properties/",
            data={"description": "Prop B", "rents_received": "6000.00", "insurance": "1000.00"},
            content_type="application/json",
        )
        # K2 should have net rent: (10000-2000) + (6000-1000) = 13000
        fv = FormFieldValue.objects.get(
            tax_return_id=rid,
            form_line__mapping_key="1120S_K2",
        )
        assert fv.value == "13000.00"

    def test_delete_rental_property(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        create_resp = http.post(
            f"/api/v1/tax-returns/{rid}/rental-properties/",
            data={"description": "To Delete", "rents_received": "5000.00"},
            content_type="application/json",
        )
        rp_id = create_resp.json()["id"]
        resp = http.delete(f"/api/v1/tax-returns/{rid}/rental-properties/{rp_id}/")
        assert resp.status_code == 204
        # K2 should be zero
        fv = FormFieldValue.objects.get(
            tax_return_id=rid,
            form_line__mapping_key="1120S_K2",
        )
        assert fv.value == "0.00"


# ---------------------------------------------------------------------------
# Update return info (header fields)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUpdateInfo:
    def test_update_accounting_method(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        resp = _create_return(http, tax_year.id)
        rid = resp.json()["id"]
        resp = http.patch(
            f"/api/v1/tax-returns/{rid}/info/",
            data={"accounting_method": "accrual"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["accounting_method"] == "accrual"

    def test_update_tax_year_dates(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        resp = _create_return(http, tax_year.id)
        rid = resp.json()["id"]
        resp = http.patch(
            f"/api/v1/tax-returns/{rid}/info/",
            data={"tax_year_start": "2025-01-01", "tax_year_end": "2025-12-31"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["tax_year_start"] == "2025-01-01"
        assert resp.json()["tax_year_end"] == "2025-12-31"


# ---------------------------------------------------------------------------
# Entity profile fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEntityProfile:
    def test_entity_profile_fields_in_serializer(self, user_and_http, firm):
        _, http = user_and_http
        client = Client.objects.create(firm=firm, name="Profile Client")
        entity = Entity.objects.create(
            client=client,
            name="Profile Entity",
            legal_name="Profile Corp LLC",
            ein="12-3456789",
            address_line1="123 Main St",
            city="Anytown",
            state="TX",
            zip_code="75001",
            business_activity="Consulting",
            naics_code="541611",
        )
        resp = http.get(f"/api/v1/entities/{entity.id}/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["legal_name"] == "Profile Corp LLC"
        assert data["ein"] == "12-3456789"
        assert data["city"] == "Anytown"
        assert data["naics_code"] == "541611"


# ---------------------------------------------------------------------------
# Compute engine override guardrail
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestComputeOverride:
    def test_override_preserves_manual_value(self, seeded, tax_year):
        """Manually overridden computed fields should not be recalculated."""
        tr = TaxReturn.objects.create(
            tax_year=tax_year,
            form_definition=seeded,
        )
        # Create field values for lines 1a, 1b, 1c
        lines = {
            fl.line_number: fl
            for fl in FormLine.objects.filter(section__form=seeded)
        }

        # Set 1a = 1000, 1b = 200
        FormFieldValue.objects.create(tax_return=tr, form_line=lines["1a"], value="1000")
        FormFieldValue.objects.create(tax_return=tr, form_line=lines["1b"], value="200")

        # Create 1c with a manual override of 999
        fv_1c = FormFieldValue.objects.create(
            tax_return=tr, form_line=lines["1c"], value="999", is_overridden=True,
        )
        # Create remaining computed lines with empty values so compute doesn't crash
        for ln in ["2", "3", "6", "20", "21", "22c", "23d", "25", "26",
                    "A6", "A8", "L14a", "L14d", "L27a", "L27d",
                    "M1_4", "M1_7", "M1_8", "M2_2", "M2_4", "M2_6", "M2_8"]:
            if ln in lines and not FormFieldValue.objects.filter(
                tax_return=tr, form_line=lines[ln]
            ).exists():
                FormFieldValue.objects.create(
                    tax_return=tr, form_line=lines[ln], value="",
                )

        compute_return(tr)

        fv_1c.refresh_from_db()
        assert fv_1c.value == "999"  # preserved, not recalculated to 800
        assert fv_1c.is_overridden is True

    def test_non_overridden_fields_are_computed(self, seeded, tax_year):
        """Non-overridden computed fields should be recalculated normally."""
        tr = TaxReturn.objects.create(
            tax_year=tax_year,
            form_definition=seeded,
        )
        lines = {
            fl.line_number: fl
            for fl in FormLine.objects.filter(section__form=seeded)
        }

        FormFieldValue.objects.create(tax_return=tr, form_line=lines["1a"], value="5000")
        FormFieldValue.objects.create(tax_return=tr, form_line=lines["1b"], value="1000")
        fv_1c = FormFieldValue.objects.create(
            tax_return=tr, form_line=lines["1c"], value="", is_overridden=False,
        )
        # Create remaining computed lines
        for ln in ["2", "3", "6", "20", "21", "22c", "23d", "25", "26",
                    "A6", "A8", "L14a", "L14d", "L27a", "L27d",
                    "M1_4", "M1_7", "M1_8", "M2_2", "M2_4", "M2_6", "M2_8"]:
            if ln in lines and not FormFieldValue.objects.filter(
                tax_return=tr, form_line=lines[ln]
            ).exists():
                FormFieldValue.objects.create(
                    tax_return=tr, form_line=lines[ln], value="",
                )

        compute_return(tr)

        fv_1c.refresh_from_db()
        assert fv_1c.value == "4000.00"  # 5000 - 1000


# ---------------------------------------------------------------------------
# 1065 & 1120 seed tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSeed1065:
    def test_seed_creates_form(self, seeded_1065):
        assert seeded_1065.code == "1065"

    def test_seed_creates_sections(self, seeded_1065):
        assert FormSection.objects.filter(form=seeded_1065).count() == 6

    def test_seed_creates_lines(self, seeded_1065):
        assert FormLine.objects.filter(section__form=seeded_1065).count() == 97

    def test_seed_has_normal_balance(self, seeded_1065):
        """1065 lines should have normal_balance set."""
        credit_lines = FormLine.objects.filter(
            section__form=seeded_1065, normal_balance="credit",
        )
        assert credit_lines.count() > 0  # revenue/liability lines should be credit


@pytest.mark.django_db
class TestSeed1120:
    def test_seed_creates_form(self, seeded_1120):
        assert seeded_1120.code == "1120"

    def test_seed_creates_sections(self, seeded_1120):
        assert FormSection.objects.filter(form=seeded_1120).count() == 9

    def test_seed_creates_lines(self, seeded_1120):
        assert FormLine.objects.filter(section__form=seeded_1120).count() == 172

    def test_seed_has_normal_balance(self, seeded_1120):
        """1120 lines should have normal_balance set."""
        credit_lines = FormLine.objects.filter(
            section__form=seeded_1120, normal_balance="credit",
        )
        assert credit_lines.count() > 0


# ---------------------------------------------------------------------------
# 1065 & 1120 compute formulas
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCompute1065:
    def test_gross_profit(self, seeded_1065, partnership_tax_year):
        """1065: 1c = 1a - 1b, 3 = 1c - 2."""
        tr = TaxReturn.objects.create(
            tax_year=partnership_tax_year,
            form_definition=seeded_1065,
        )
        lines = {
            fl.line_number: fl
            for fl in FormLine.objects.filter(section__form=seeded_1065)
        }
        for ln_num, val in [("1a", "10000"), ("1b", "3000"), ("2", "2000")]:
            FormFieldValue.objects.create(
                tax_return=tr, form_line=lines[ln_num], value=val,
            )
        # Create empty values for all computed lines
        for ln_num, fl in lines.items():
            if not FormFieldValue.objects.filter(tax_return=tr, form_line=fl).exists():
                FormFieldValue.objects.create(tax_return=tr, form_line=fl, value="")

        compute_return(tr)

        fv_1c = FormFieldValue.objects.get(tax_return=tr, form_line=lines["1c"])
        assert fv_1c.value == "7000.00"

        fv_3 = FormFieldValue.objects.get(tax_return=tr, form_line=lines["3"])
        assert fv_3.value == "5000.00"


@pytest.mark.django_db
class TestCompute1120:
    def test_gross_profit_and_tax(self, seeded_1120, ccorp_tax_year):
        """1120: 1c = 1a - 1b, 3 = 1c - 2, 11 = sum(3..10)."""
        tr = TaxReturn.objects.create(
            tax_year=ccorp_tax_year,
            form_definition=seeded_1120,
        )
        lines = {
            fl.line_number: fl
            for fl in FormLine.objects.filter(section__form=seeded_1120)
        }
        for ln_num, val in [("1a", "100000"), ("1b", "10000"), ("2", "5000")]:
            FormFieldValue.objects.create(
                tax_return=tr, form_line=lines[ln_num], value=val,
            )
        # Create empty values for all lines
        for ln_num, fl in lines.items():
            if not FormFieldValue.objects.filter(tax_return=tr, form_line=fl).exists():
                FormFieldValue.objects.create(tax_return=tr, form_line=fl, value="")

        compute_return(tr)

        fv_1c = FormFieldValue.objects.get(tax_return=tr, form_line=lines["1c"])
        assert fv_1c.value == "90000.00"

        fv_3 = FormFieldValue.objects.get(tax_return=tr, form_line=lines["3"])
        assert fv_3.value == "85000.00"

        # Line 11 = sum of 3 through 10, with only 3 populated
        fv_11 = FormFieldValue.objects.get(tax_return=tr, form_line=lines["11"])
        assert fv_11.value == "85000.00"

        # J2 = Line 30 * 21% (if no deductions, 28 = 11, 30 = 28)
        fv_j2 = FormFieldValue.objects.get(tax_return=tr, form_line=lines["J2"])
        assert fv_j2.value == "17850.00"  # 85000 * 0.21


# ---------------------------------------------------------------------------
# Shareholder distributions rollup + linked_client
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestShareholderDistributions:
    def _setup_return(self, http, seeded, tax_year):
        resp = _create_return(http, tax_year.id)
        return resp.json()["id"]

    def test_distributions_field_in_response(self, user_and_http, seeded, tax_year):
        """New distributions field should appear in shareholder API responses."""
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.post(
            f"/api/v1/tax-returns/{rid}/shareholders/",
            data={"name": "Alice", "distributions": "5000.00"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["distributions"] == "5000.00"

    def test_health_insurance_field_in_response(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.post(
            f"/api/v1/tax-returns/{rid}/shareholders/",
            data={"name": "Bob", "health_insurance_premium": "1200.00"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["health_insurance_premium"] == "1200.00"

    def test_distributions_rollup_to_k16d(self, user_and_http, seeded, tax_year):
        """Creating shareholders with distributions should rollup to K16d FormLine."""
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        http.post(
            f"/api/v1/tax-returns/{rid}/shareholders/",
            data={"name": "Alice", "distributions": "3000.00"},
            content_type="application/json",
        )
        http.post(
            f"/api/v1/tax-returns/{rid}/shareholders/",
            data={"name": "Bob", "distributions": "2000.00"},
            content_type="application/json",
        )
        fv = FormFieldValue.objects.get(
            tax_return_id=rid,
            form_line__mapping_key="1120S_K16d",
        )
        assert fv.value == "5000.00"

    def test_distributions_rollup_on_update(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.post(
            f"/api/v1/tax-returns/{rid}/shareholders/",
            data={"name": "Alice", "distributions": "1000.00"},
            content_type="application/json",
        )
        sh_id = resp.json()["id"]
        http.patch(
            f"/api/v1/tax-returns/{rid}/shareholders/{sh_id}/",
            data={"distributions": "4500.00"},
            content_type="application/json",
        )
        fv = FormFieldValue.objects.get(
            tax_return_id=rid,
            form_line__mapping_key="1120S_K16d",
        )
        assert fv.value == "4500.00"

    def test_distributions_rollup_on_delete(self, user_and_http, seeded, tax_year):
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        resp = http.post(
            f"/api/v1/tax-returns/{rid}/shareholders/",
            data={"name": "Alice", "distributions": "6000.00"},
            content_type="application/json",
        )
        sh_id = resp.json()["id"]
        http.delete(f"/api/v1/tax-returns/{rid}/shareholders/{sh_id}/")
        fv = FormFieldValue.objects.get(
            tax_return_id=rid,
            form_line__mapping_key="1120S_K16d",
        )
        assert fv.value == "0.00"

    def test_linked_client_field(self, user_and_http, seeded, tax_year, firm):
        """Shareholder can be linked to a client."""
        _, http = user_and_http
        rid = self._setup_return(http, seeded, tax_year)
        linked = Client.objects.create(firm=firm, name="Linked Person")
        resp = http.post(
            f"/api/v1/tax-returns/{rid}/shareholders/",
            data={"name": "Alice", "linked_client": str(linked.id)},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["linked_client"] == str(linked.id)
        assert resp.json()["linked_client_name"] == "Linked Person"


# ---------------------------------------------------------------------------
# Shared entity visibility
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSharedEntityVisibility:
    def test_entity_visible_under_linked_client(self, user_and_http, seeded, firm):
        """An entity should appear under a client linked via shareholder."""
        _, http = user_and_http
        # Client A owns the entity directly
        client_a = Client.objects.create(firm=firm, name="Client A")
        entity = Entity.objects.create(client=client_a, name="Shared Corp")
        ty = TaxYear.objects.create(entity=entity, year=2025)

        # Create a return
        resp = _create_return(http, ty.id)
        rid = resp.json()["id"]

        # Client B is a shareholder linked to a client record
        client_b = Client.objects.create(firm=firm, name="Client B")
        Shareholder.objects.create(
            tax_return_id=rid,
            name="Client B SH",
            linked_client=client_b,
            ownership_percentage=Decimal("50.0000"),
        )

        # Entity should appear under Client B's entity list
        resp = http.get(f"/api/v1/entities/?client={client_b.id}")
        assert resp.status_code == 200
        entity_ids = [e["id"] for e in resp.json()]
        assert str(entity.id) in entity_ids

    def test_entity_not_visible_for_unlinked_client(self, user_and_http, seeded, firm):
        """An entity should NOT appear under an unrelated client."""
        _, http = user_and_http
        client_a = Client.objects.create(firm=firm, name="Owner")
        entity = Entity.objects.create(client=client_a, name="Private Corp")
        TaxYear.objects.create(entity=entity, year=2025)

        client_c = Client.objects.create(firm=firm, name="Unrelated")
        resp = http.get(f"/api/v1/entities/?client={client_c.id}")
        assert resp.status_code == 200
        entity_ids = [e["id"] for e in resp.json()]
        assert str(entity.id) not in entity_ids
