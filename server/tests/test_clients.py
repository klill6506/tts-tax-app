import pytest
from django.contrib.auth.models import User
from django.test import Client as TestClient

from apps.clients.models import (
    Client,
    ClientStatus,
    Entity,
    EntityType,
    ReturnStatus,
    TaxYear,
)
from apps.firms.models import Firm, FirmMembership, Role


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Tax Firm")


@pytest.fixture
def other_firm(db):
    return Firm.objects.create(name="Other Firm")


@pytest.fixture
def user_and_client(firm):
    """Create a user with firm membership and return (user, http_client)."""
    user = User.objects.create_user(
        username="preparer1", password="testpass123"
    )
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    http = TestClient()
    http.login(username="preparer1", password="testpass123")
    return user, http


@pytest.fixture
def other_user_and_client(other_firm):
    """User in a different firm."""
    user = User.objects.create_user(
        username="outsider", password="testpass123"
    )
    FirmMembership.objects.create(user=user, firm=other_firm, role=Role.PREPARER)
    http = TestClient()
    http.login(username="outsider", password="testpass123")
    return user, http


@pytest.fixture
def sample_client(firm):
    return Client.objects.create(firm=firm, name="Acme Corp")


@pytest.fixture
def sample_entity(sample_client):
    return Entity.objects.create(
        client=sample_client,
        name="Acme S-Corp",
        entity_type=EntityType.SCORP,
    )


@pytest.fixture
def sample_tax_year(sample_entity):
    return TaxYear.objects.create(
        entity=sample_entity,
        year=2025,
        status=ReturnStatus.DRAFT,
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestModels:
    def test_create_client(self, firm):
        c = Client.objects.create(firm=firm, name="Widget Inc")
        assert c.name == "Widget Inc"
        assert c.status == ClientStatus.ACTIVE
        assert c.firm == firm
        assert c.created_at is not None

    def test_create_entity(self, sample_client):
        e = Entity.objects.create(
            client=sample_client, name="Widget S-Corp", entity_type=EntityType.SCORP
        )
        assert str(e) == "Widget S-Corp (S-Corp (1120S))"

    def test_create_tax_year(self, sample_entity):
        ty = TaxYear.objects.create(entity=sample_entity, year=2025)
        assert ty.status == ReturnStatus.DRAFT
        assert ty.year == 2025
        assert ty.created_by is None

    def test_unique_entity_year(self, sample_entity):
        TaxYear.objects.create(entity=sample_entity, year=2025)
        with pytest.raises(Exception):
            TaxYear.objects.create(entity=sample_entity, year=2025)

    def test_full_hierarchy(self, firm):
        client = Client.objects.create(firm=firm, name="Chain Inc")
        entity = Entity.objects.create(client=client, name="Chain SCorp")
        ty = TaxYear.objects.create(entity=entity, year=2024)
        # Navigate the chain
        assert ty.entity.client.firm == firm


# ---------------------------------------------------------------------------
# Client CRUD endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestClientEndpoints:
    def test_list_clients(self, user_and_client, sample_client):
        _, http = user_and_client
        resp = http.get("/api/v1/clients/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Acme Corp"

    def test_create_client(self, user_and_client):
        _, http = user_and_client
        resp = http.post(
            "/api/v1/clients/",
            data={"name": "New Client", "status": "active"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "New Client"
        assert Client.objects.count() == 1

    def test_retrieve_client(self, user_and_client, sample_client):
        _, http = user_and_client
        resp = http.get(f"/api/v1/clients/{sample_client.id}/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Acme Corp"

    def test_update_client(self, user_and_client, sample_client):
        _, http = user_and_client
        resp = http.patch(
            f"/api/v1/clients/{sample_client.id}/",
            data={"name": "Acme Corp Updated"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        sample_client.refresh_from_db()
        assert sample_client.name == "Acme Corp Updated"

    def test_unauthenticated_denied(self, sample_client):
        http = TestClient()
        resp = http.get("/api/v1/clients/")
        assert resp.status_code == 403

    def test_other_firm_cannot_see_clients(
        self, user_and_client, other_user_and_client, sample_client
    ):
        _, other_http = other_user_and_client
        resp = other_http.get("/api/v1/clients/")
        assert resp.status_code == 200
        assert len(resp.json()) == 0  # Sees nothing from the other firm

    def test_other_firm_cannot_access_client_detail(
        self, other_user_and_client, sample_client
    ):
        _, other_http = other_user_and_client
        resp = other_http.get(f"/api/v1/clients/{sample_client.id}/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Entity CRUD endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEntityEndpoints:
    def test_list_entities(self, user_and_client, sample_entity):
        _, http = user_and_client
        resp = http.get("/api/v1/entities/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Acme S-Corp"

    def test_create_entity(self, user_and_client, sample_client):
        _, http = user_and_client
        resp = http.post(
            "/api/v1/entities/",
            data={
                "client": str(sample_client.id),
                "name": "New Entity",
                "entity_type": "scorp",
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert Entity.objects.count() == 1

    def test_filter_entities_by_client(
        self, user_and_client, firm, sample_entity
    ):
        # Create a second client with its own entity
        c2 = Client.objects.create(firm=firm, name="Other Client")
        Entity.objects.create(client=c2, name="Other Entity")
        _, http = user_and_client
        resp = http.get(f"/api/v1/entities/?client={sample_entity.client_id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Acme S-Corp"

    def test_other_firm_cannot_see_entities(
        self, other_user_and_client, sample_entity
    ):
        _, other_http = other_user_and_client
        resp = other_http.get("/api/v1/entities/")
        assert len(resp.json()) == 0


# ---------------------------------------------------------------------------
# Entity duplicate prevention tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEntityDuplicatePrevention:
    def test_cannot_create_duplicate_entity(self, user_and_client, sample_client):
        _, http = user_and_client
        data = {
            "client": str(sample_client.id),
            "name": "Acme S-Corp",
            "entity_type": "scorp",
        }
        resp1 = http.post(
            "/api/v1/entities/", data=data, content_type="application/json"
        )
        assert resp1.status_code == 201
        resp2 = http.post(
            "/api/v1/entities/", data=data, content_type="application/json"
        )
        assert resp2.status_code == 400
        # DRF's built-in UniqueTogetherValidator catches exact-case duplicates
        body = str(resp2.json()).lower()
        assert "unique" in body or "already exists" in body

    def test_can_create_same_name_different_type(
        self, user_and_client, sample_client
    ):
        _, http = user_and_client
        resp1 = http.post(
            "/api/v1/entities/",
            data={
                "client": str(sample_client.id),
                "name": "Smith",
                "entity_type": "scorp",
            },
            content_type="application/json",
        )
        assert resp1.status_code == 201
        resp2 = http.post(
            "/api/v1/entities/",
            data={
                "client": str(sample_client.id),
                "name": "Smith",
                "entity_type": "partnership",
            },
            content_type="application/json",
        )
        assert resp2.status_code == 201

    def test_case_insensitive_duplicate_check(
        self, user_and_client, sample_client
    ):
        _, http = user_and_client
        http.post(
            "/api/v1/entities/",
            data={
                "client": str(sample_client.id),
                "name": "Acme Corp",
                "entity_type": "scorp",
            },
            content_type="application/json",
        )
        resp = http.post(
            "/api/v1/entities/",
            data={
                "client": str(sample_client.id),
                "name": "acme corp",
                "entity_type": "scorp",
            },
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "already exists" in str(resp.json())


# ---------------------------------------------------------------------------
# TaxYear CRUD endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTaxYearEndpoints:
    def test_list_tax_years(self, user_and_client, sample_tax_year):
        _, http = user_and_client
        resp = http.get("/api/v1/tax-years/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["year"] == 2025

    def test_create_tax_year(self, user_and_client, sample_entity):
        user, http = user_and_client
        resp = http.post(
            "/api/v1/tax-years/",
            data={
                "entity": str(sample_entity.id),
                "year": 2025,
                "status": "draft",
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        ty = TaxYear.objects.first()
        assert ty.created_by == user  # auto-set by perform_create
        assert ty.year == 2025

    def test_update_tax_year_status(self, user_and_client, sample_tax_year):
        _, http = user_and_client
        resp = http.patch(
            f"/api/v1/tax-years/{sample_tax_year.id}/",
            data={"status": "in_progress"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        sample_tax_year.refresh_from_db()
        assert sample_tax_year.status == ReturnStatus.IN_PROGRESS

    def test_filter_by_entity(self, user_and_client, sample_tax_year, firm):
        _, http = user_and_client
        resp = http.get(
            f"/api/v1/tax-years/?entity={sample_tax_year.entity_id}"
        )
        assert len(resp.json()) == 1

    def test_filter_by_year(self, user_and_client, sample_tax_year):
        _, http = user_and_client
        resp = http.get("/api/v1/tax-years/?year=2025")
        assert len(resp.json()) == 1
        resp = http.get("/api/v1/tax-years/?year=2024")
        assert len(resp.json()) == 0

    def test_other_firm_cannot_see_tax_years(
        self, other_user_and_client, sample_tax_year
    ):
        _, other_http = other_user_and_client
        resp = other_http.get("/api/v1/tax-years/")
        assert len(resp.json()) == 0

    def test_other_firm_cannot_access_tax_year_detail(
        self, other_user_and_client, sample_tax_year
    ):
        _, other_http = other_user_and_client
        resp = other_http.get(f"/api/v1/tax-years/{sample_tax_year.id}/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Full flow: Client → Entity → 2025 TaxYear
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFullFlow:
    def test_create_client_entity_taxyear_flow(self, user_and_client):
        user, http = user_and_client

        # 1) Create client
        resp = http.post(
            "/api/v1/clients/",
            data={"name": "Flow Test Client"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        client_id = resp.json()["id"]

        # 2) Create entity under that client
        resp = http.post(
            "/api/v1/entities/",
            data={
                "client": client_id,
                "name": "Flow S-Corp",
                "entity_type": "scorp",
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        entity_id = resp.json()["id"]

        # 3) Create 2025 tax year
        resp = http.post(
            "/api/v1/tax-years/",
            data={"entity": entity_id, "year": 2025, "status": "draft"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["year"] == 2025

        # Verify the full chain exists
        assert Client.objects.count() == 1
        assert Entity.objects.count() == 1
        assert TaxYear.objects.count() == 1
        ty = TaxYear.objects.first()
        assert ty.entity.client.name == "Flow Test Client"
        assert ty.created_by == user
