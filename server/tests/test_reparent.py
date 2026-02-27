import pytest
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client as TestClient

from apps.clients.models import (
    Client,
    ClientEntityLink,
    ClientStatus,
    Entity,
    EntityType,
    LinkRole,
    ReturnStatus,
    TaxYear,
)
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.models import FormDefinition, TaxReturn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Tax Firm")


@pytest.fixture
def user_and_client(firm):
    user = User.objects.create_user(username="preparer1", password="testpass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    http = TestClient()
    http.login(username="preparer1", password="testpass123")
    return user, http


@pytest.fixture
def individual_john(firm):
    """Individual client: John Smith."""
    client = Client.objects.create(firm=firm, name="SMITH, JOHN")
    entity = Entity.objects.create(
        client=client, name="SMITH, JOHN", entity_type=EntityType.INDIVIDUAL,
    )
    ClientEntityLink.objects.create(
        client=client, entity=entity, role=LinkRole.TAXPAYER, is_primary=True,
    )
    return client


@pytest.fixture
def individual_jane(firm):
    """Individual client: Jane Doe."""
    client = Client.objects.create(firm=firm, name="DOE, JANE")
    entity = Entity.objects.create(
        client=client, name="DOE, JANE", entity_type=EntityType.INDIVIDUAL,
    )
    ClientEntityLink.objects.create(
        client=client, entity=entity, role=LinkRole.TAXPAYER, is_primary=True,
    )
    return client


@pytest.fixture
def scorp_acme(firm, individual_john, individual_jane):
    """S-Corp with its own Client record + two shareholders."""
    scorp_client = Client.objects.create(firm=firm, name="ACME CORP")
    entity = Entity.objects.create(
        client=scorp_client,
        name="ACME CORP",
        entity_type=EntityType.SCORP,
        ein="12-3456789",
    )
    # John is primary shareholder (60%)
    ClientEntityLink.objects.create(
        client=individual_john,
        entity=entity,
        role=LinkRole.SHAREHOLDER,
        is_primary=True,
        ownership_percentage=60,
    )
    # Jane is secondary (40%)
    ClientEntityLink.objects.create(
        client=individual_jane,
        entity=entity,
        role=LinkRole.SHAREHOLDER,
        is_primary=False,
        ownership_percentage=40,
    )
    return scorp_client, entity


# ---------------------------------------------------------------------------
# Reparent command tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReparentCommand:
    def test_reparent_to_primary_shareholder(self, scorp_acme, individual_john):
        scorp_client, entity = scorp_acme

        call_command("reparent_business_entities", stdout=StringIO())

        entity.refresh_from_db()
        assert entity.client == individual_john
        assert not Client.objects.filter(id=scorp_client.id).exists()

    def test_reparent_picks_highest_ownership(self, firm, individual_john, individual_jane):
        """When no is_primary, pick the shareholder with highest ownership."""
        scorp_client = Client.objects.create(firm=firm, name="BETA LLC")
        entity = Entity.objects.create(
            client=scorp_client,
            name="BETA LLC",
            entity_type=EntityType.SCORP,
        )
        # No is_primary set — Jane has 70%, John has 30%
        ClientEntityLink.objects.create(
            client=individual_jane,
            entity=entity,
            role=LinkRole.SHAREHOLDER,
            is_primary=False,
            ownership_percentage=70,
        )
        ClientEntityLink.objects.create(
            client=individual_john,
            entity=entity,
            role=LinkRole.SHAREHOLDER,
            is_primary=False,
            ownership_percentage=30,
        )

        call_command("reparent_business_entities", stdout=StringIO())

        entity.refresh_from_db()
        assert entity.client == individual_jane

    def test_skips_no_shareholder_links(self, firm):
        """S-Corp with no shareholder links should be skipped."""
        scorp_client = Client.objects.create(firm=firm, name="ORPHAN CORP")
        entity = Entity.objects.create(
            client=scorp_client,
            name="ORPHAN CORP",
            entity_type=EntityType.SCORP,
        )

        call_command("reparent_business_entities", stdout=StringIO())

        entity.refresh_from_db()
        assert entity.client == scorp_client  # unchanged
        assert Client.objects.filter(id=scorp_client.id).exists()  # not deleted

    def test_dry_run_changes_nothing(self, scorp_acme, individual_john):
        scorp_client, entity = scorp_acme
        original_client_id = entity.client_id

        call_command("reparent_business_entities", "--dry-run", stdout=StringIO())

        entity.refresh_from_db()
        assert entity.client_id == original_client_id
        assert Client.objects.filter(id=scorp_client.id).exists()

    def test_firm_scoping_intact_after_reparent(self, scorp_acme, individual_john, firm):
        scorp_client, entity = scorp_acme
        ty = TaxYear.objects.create(entity=entity, year=2025)

        call_command("reparent_business_entities", stdout=StringIO())

        entity.refresh_from_db()
        # The entity → client → firm chain should still work
        assert entity.client.firm == firm
        # TaxYear scoping query should still find this
        assert TaxYear.objects.filter(
            entity__client__firm=firm, id=ty.id,
        ).exists()

    def test_skips_client_with_individual_entity(self, firm):
        """If a Client has both individual + scorp entities, skip it."""
        client = Client.objects.create(firm=firm, name="MULTI, PERSON")
        Entity.objects.create(
            client=client, name="MULTI, PERSON",
            entity_type=EntityType.INDIVIDUAL,
        )
        Entity.objects.create(
            client=client, name="MULTI SCORP",
            entity_type=EntityType.SCORP,
        )

        call_command("reparent_business_entities", stdout=StringIO())

        # Client should still exist — it has an individual entity
        assert Client.objects.filter(id=client.id).exists()

    def test_unique_constraint_conflict_skipped(self, firm, individual_john):
        """If re-parenting would violate unique constraint, skip."""
        # Create an S-Corp client
        scorp_client = Client.objects.create(firm=firm, name="CONFLICT CORP")
        entity = Entity.objects.create(
            client=scorp_client,
            name="CONFLICT CORP",
            entity_type=EntityType.SCORP,
        )
        # John already has an entity with same name + type
        Entity.objects.create(
            client=individual_john,
            name="CONFLICT CORP",
            entity_type=EntityType.SCORP,
        )
        ClientEntityLink.objects.create(
            client=individual_john,
            entity=entity,
            role=LinkRole.SHAREHOLDER,
            is_primary=True,
            ownership_percentage=100,
        )

        call_command("reparent_business_entities", stdout=StringIO())

        entity.refresh_from_db()
        assert entity.client == scorp_client  # not re-parented

    def test_entity_links_preserved_after_reparent(self, scorp_acme, individual_john, individual_jane):
        scorp_client, entity = scorp_acme

        call_command("reparent_business_entities", stdout=StringIO())

        # Shareholder links should still exist
        assert ClientEntityLink.objects.filter(
            client=individual_john, entity=entity, role=LinkRole.SHAREHOLDER,
        ).exists()
        assert ClientEntityLink.objects.filter(
            client=individual_jane, entity=entity, role=LinkRole.SHAREHOLDER,
        ).exists()


# ---------------------------------------------------------------------------
# Client returns endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestClientReturnsEndpoint:
    def test_returns_direct_entity(self, user_and_client, firm):
        user, http = user_and_client
        client = Client.objects.create(firm=firm, name="TEST CLIENT")
        entity = Entity.objects.create(
            client=client, name="TEST CLIENT",
            entity_type=EntityType.INDIVIDUAL,
        )
        TaxYear.objects.create(entity=entity, year=2025)

        resp = http.get(f"/api/v1/clients/{client.id}/returns/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["entity_name"] == "TEST CLIENT"
        assert data[0]["entity_type"] == "individual"
        assert data[0]["relationship"] == "direct"
        assert data[0]["year"] == 2025

    def test_returns_linked_entity(self, user_and_client, firm):
        user, http = user_and_client
        # Individual client
        client = Client.objects.create(firm=firm, name="OWNER")
        ind_entity = Entity.objects.create(
            client=client, name="OWNER",
            entity_type=EntityType.INDIVIDUAL,
        )
        # S-Corp entity (under its own client — pre-migration)
        scorp_client = Client.objects.create(firm=firm, name="SCORP INC")
        scorp_entity = Entity.objects.create(
            client=scorp_client, name="SCORP INC",
            entity_type=EntityType.SCORP,
        )
        ClientEntityLink.objects.create(
            client=client, entity=scorp_entity,
            role=LinkRole.SHAREHOLDER, ownership_percentage=100, is_primary=True,
        )
        TaxYear.objects.create(entity=scorp_entity, year=2025)

        resp = http.get(f"/api/v1/clients/{client.id}/returns/")
        assert resp.status_code == 200
        data = resp.json()
        # Should see both: individual entity (no tax year) + scorp (with tax year)
        entity_names = {r["entity_name"] for r in data}
        assert "OWNER" in entity_names
        assert "SCORP INC" in entity_names

        scorp_row = next(r for r in data if r["entity_name"] == "SCORP INC")
        assert scorp_row["relationship"] == "shareholder"
        assert scorp_row["ownership_percentage"] == "100.0000"

    def test_returns_reparented_entity(self, user_and_client, scorp_acme, individual_john):
        user, http = user_and_client
        scorp_client, entity = scorp_acme

        # Run re-parent
        call_command("reparent_business_entities", stdout=StringIO())

        # Now check John's returns — should include the S-Corp as direct
        resp = http.get(f"/api/v1/clients/{individual_john.id}/returns/")
        assert resp.status_code == 200
        data = resp.json()
        entity_names = {r["entity_name"] for r in data}
        assert "ACME CORP" in entity_names

    def test_entity_without_tax_year_appears(self, user_and_client, firm):
        user, http = user_and_client
        client = Client.objects.create(firm=firm, name="NEW CLIENT")
        Entity.objects.create(
            client=client, name="NEW CLIENT",
            entity_type=EntityType.INDIVIDUAL,
        )

        resp = http.get(f"/api/v1/clients/{client.id}/returns/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["year"] is None
        assert data[0]["return_id"] is None


# ---------------------------------------------------------------------------
# Auto-create individual entity on new client
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAutoCreateEntity:
    def test_new_client_creates_individual_entity(self, user_and_client, firm):
        user, http = user_and_client

        resp = http.post(
            "/api/v1/clients/",
            data={"name": "NEW PERSON", "status": "active"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        client_id = resp.json()["id"]

        # Should have an individual entity
        entities = Entity.objects.filter(client_id=client_id)
        assert entities.count() == 1
        assert entities.first().entity_type == EntityType.INDIVIDUAL
        assert entities.first().name == "NEW PERSON"

        # Should have a taxpayer link
        links = ClientEntityLink.objects.filter(
            client_id=client_id, role=LinkRole.TAXPAYER,
        )
        assert links.count() == 1
        assert links.first().is_primary is True
