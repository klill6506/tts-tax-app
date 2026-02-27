"""Tests for the ClientEntityLink model and API."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client as TestClient

from apps.clients.models import (
    Client,
    ClientEntityLink,
    Entity,
    EntityType,
    LinkRole,
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
    user = User.objects.create_user(username="preparer1", password="testpass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    http = TestClient()
    http.login(username="preparer1", password="testpass123")
    return user, http


@pytest.fixture
def other_user_and_client(other_firm):
    user = User.objects.create_user(username="outsider", password="testpass123")
    FirmMembership.objects.create(user=user, firm=other_firm, role=Role.PREPARER)
    http = TestClient()
    http.login(username="outsider", password="testpass123")
    return user, http


@pytest.fixture
def john_client(firm):
    return Client.objects.create(firm=firm, name="Smith, John")


@pytest.fixture
def jane_client(firm):
    return Client.objects.create(firm=firm, name="Doe, Jane")


@pytest.fixture
def john_individual(john_client):
    return Entity.objects.create(
        client=john_client,
        name="Smith, John",
        entity_type=EntityType.INDIVIDUAL,
    )


@pytest.fixture
def scorp_entity(john_client):
    return Entity.objects.create(
        client=john_client,
        name="Smith Auto Repair",
        entity_type=EntityType.SCORP,
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestClientEntityLinkModel:

    def test_create_taxpayer_link(self, john_client, john_individual):
        link = ClientEntityLink.objects.create(
            client=john_client,
            entity=john_individual,
            role=LinkRole.TAXPAYER,
            is_primary=True,
        )
        assert link.client == john_client
        assert link.entity == john_individual
        assert link.role == LinkRole.TAXPAYER
        assert link.is_primary is True
        assert link.ownership_percentage is None

    def test_create_shareholder_link(self, john_client, scorp_entity):
        link = ClientEntityLink.objects.create(
            client=john_client,
            entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
            ownership_percentage=Decimal("60.0000"),
        )
        assert link.ownership_percentage == Decimal("60.0000")
        assert link.role == LinkRole.SHAREHOLDER

    def test_unique_constraint(self, john_client, scorp_entity):
        ClientEntityLink.objects.create(
            client=john_client,
            entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
        )
        with pytest.raises(Exception):
            ClientEntityLink.objects.create(
                client=john_client,
                entity=scorp_entity,
                role=LinkRole.SHAREHOLDER,
            )

    def test_same_client_entity_different_roles_allowed(
        self, john_client, scorp_entity
    ):
        ClientEntityLink.objects.create(
            client=john_client,
            entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
        )
        link2 = ClientEntityLink.objects.create(
            client=john_client,
            entity=scorp_entity,
            role=LinkRole.OFFICER,
        )
        assert ClientEntityLink.objects.filter(
            client=john_client, entity=scorp_entity
        ).count() == 2

    def test_multiple_clients_linked_to_one_entity(
        self, john_client, jane_client, scorp_entity
    ):
        ClientEntityLink.objects.create(
            client=john_client,
            entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
            ownership_percentage=Decimal("60.0000"),
        )
        ClientEntityLink.objects.create(
            client=jane_client,
            entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
            ownership_percentage=Decimal("40.0000"),
        )
        links = ClientEntityLink.objects.filter(entity=scorp_entity)
        assert links.count() == 2

    def test_str_representation(self, john_client, scorp_entity):
        link = ClientEntityLink.objects.create(
            client=john_client,
            entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
        )
        assert "Smith, John" in str(link)
        assert "Smith Auto Repair" in str(link)
        assert "Shareholder" in str(link)

    def test_cascade_delete_client(self, john_client, scorp_entity):
        ClientEntityLink.objects.create(
            client=john_client,
            entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
        )
        john_client.delete()
        assert ClientEntityLink.objects.count() == 0

    def test_cascade_delete_entity(self, john_client, scorp_entity):
        ClientEntityLink.objects.create(
            client=john_client,
            entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
        )
        scorp_entity.delete()
        assert ClientEntityLink.objects.count() == 0


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestClientEntityLinkAPI:

    def test_list_links(self, user_and_client, john_client, john_individual):
        ClientEntityLink.objects.create(
            client=john_client,
            entity=john_individual,
            role=LinkRole.TAXPAYER,
            is_primary=True,
        )
        _, http = user_and_client
        resp = http.get("/api/v1/entity-links/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["client_name"] == "Smith, John"
        assert data[0]["entity_name"] == "Smith, John"
        assert data[0]["entity_type"] == "individual"
        assert data[0]["role"] == "taxpayer"

    def test_filter_by_client(
        self, user_and_client, john_client, jane_client,
        john_individual, scorp_entity
    ):
        ClientEntityLink.objects.create(
            client=john_client, entity=john_individual,
            role=LinkRole.TAXPAYER, is_primary=True,
        )
        ClientEntityLink.objects.create(
            client=john_client, entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
        )
        ClientEntityLink.objects.create(
            client=jane_client, entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
        )
        _, http = user_and_client
        resp = http.get(f"/api/v1/entity-links/?client={john_client.id}")
        assert len(resp.json()) == 2  # John's individual + S-Corp

    def test_filter_by_entity(
        self, user_and_client, john_client, jane_client, scorp_entity
    ):
        ClientEntityLink.objects.create(
            client=john_client, entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
        )
        ClientEntityLink.objects.create(
            client=jane_client, entity=scorp_entity,
            role=LinkRole.SHAREHOLDER,
        )
        _, http = user_and_client
        resp = http.get(f"/api/v1/entity-links/?entity={scorp_entity.id}")
        assert len(resp.json()) == 2  # Both owners

    def test_create_link_via_api(
        self, user_and_client, john_client, scorp_entity
    ):
        _, http = user_and_client
        resp = http.post(
            "/api/v1/entity-links/",
            data={
                "client": str(john_client.id),
                "entity": str(scorp_entity.id),
                "role": "shareholder",
                "ownership_percentage": "60.0000",
                "is_primary": True,
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert ClientEntityLink.objects.count() == 1

    def test_other_firm_cannot_see_links(
        self, user_and_client, other_user_and_client,
        john_client, john_individual
    ):
        ClientEntityLink.objects.create(
            client=john_client, entity=john_individual,
            role=LinkRole.TAXPAYER,
        )
        _, other_http = other_user_and_client
        resp = other_http.get("/api/v1/entity-links/")
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_unauthenticated_denied(self):
        http = TestClient()
        resp = http.get("/api/v1/entity-links/")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Management command tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLinkIndividualsCommand:

    def test_links_individual_entities(self, firm):
        c1 = Client.objects.create(firm=firm, name="Person A")
        Entity.objects.create(
            client=c1, name="Person A", entity_type=EntityType.INDIVIDUAL,
        )
        c2 = Client.objects.create(firm=firm, name="Person B")
        Entity.objects.create(
            client=c2, name="Person B", entity_type=EntityType.INDIVIDUAL,
        )

        call_command("link_individuals")
        assert ClientEntityLink.objects.count() == 2
        assert ClientEntityLink.objects.filter(role=LinkRole.TAXPAYER).count() == 2
        assert ClientEntityLink.objects.filter(is_primary=True).count() == 2

    def test_skips_non_individual_entities(self, firm):
        c = Client.objects.create(firm=firm, name="Biz Owner")
        Entity.objects.create(
            client=c, name="Biz Owner", entity_type=EntityType.INDIVIDUAL,
        )
        Entity.objects.create(
            client=c, name="Owner's S-Corp", entity_type=EntityType.SCORP,
        )

        call_command("link_individuals")
        # Only the individual entity gets a link
        assert ClientEntityLink.objects.count() == 1

    def test_idempotent(self, firm):
        c = Client.objects.create(firm=firm, name="Person")
        Entity.objects.create(
            client=c, name="Person", entity_type=EntityType.INDIVIDUAL,
        )

        call_command("link_individuals")
        call_command("link_individuals")  # run again
        assert ClientEntityLink.objects.count() == 1  # no duplicates

    def test_dry_run(self, firm):
        c = Client.objects.create(firm=firm, name="Person")
        Entity.objects.create(
            client=c, name="Person", entity_type=EntityType.INDIVIDUAL,
        )

        call_command("link_individuals", "--dry-run")
        assert ClientEntityLink.objects.count() == 0
