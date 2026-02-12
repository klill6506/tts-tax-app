import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.firms.models import Firm, FirmMembership, Role


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Tax Firm")


@pytest.fixture
def user_with_membership(db, firm):
    user = User.objects.create_user(
        username="preparer1",
        password="testpass123",
        email="prep@example.com",
        first_name="Jane",
        last_name="Doe",
    )
    membership = FirmMembership.objects.create(
        user=user,
        firm=firm,
        role=Role.PREPARER,
    )
    return user, membership


# --- Model tests ---


@pytest.mark.django_db
def test_create_firm():
    firm = Firm.objects.create(name="Acme Tax LLC")
    assert firm.name == "Acme Tax LLC"
    assert firm.is_active is True
    assert firm.id is not None
    assert firm.created_at is not None


@pytest.mark.django_db
def test_create_firm_membership(firm):
    user = User.objects.create_user(username="bob", password="pass123")
    membership = FirmMembership.objects.create(
        user=user, firm=firm, role=Role.ADMIN
    )
    assert membership.role == "admin"
    assert str(membership) == f"bob @ {firm.name} (admin)"


@pytest.mark.django_db
def test_unique_user_per_firm(firm):
    user = User.objects.create_user(username="alice", password="pass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    with pytest.raises(Exception):
        FirmMembership.objects.create(user=user, firm=firm, role=Role.REVIEWER)


@pytest.mark.django_db
def test_role_choices():
    assert Role.ADMIN == "admin"
    assert Role.PREPARER == "preparer"
    assert Role.REVIEWER == "reviewer"


# --- /api/v1/me/ endpoint tests ---


@pytest.mark.django_db
def test_me_endpoint_returns_user_and_firm(user_with_membership):
    user, membership = user_with_membership
    client = Client()
    client.login(username="preparer1", password="testpass123")
    response = client.get("/api/v1/me/")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "preparer1"
    assert data["email"] == "prep@example.com"
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"
    assert len(data["memberships"]) == 1
    assert data["memberships"][0]["firm_name"] == "Test Tax Firm"
    assert data["memberships"][0]["role"] == "preparer"


@pytest.mark.django_db
def test_me_endpoint_requires_auth():
    client = Client()
    response = client.get("/api/v1/me/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_me_endpoint_user_no_firm(db):
    User.objects.create_user(username="lonely", password="testpass123")
    client = Client()
    client.login(username="lonely", password="testpass123")
    response = client.get("/api/v1/me/")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "lonely"
    assert data["memberships"] == []


# --- Middleware tests ---


@pytest.mark.django_db
def test_middleware_attaches_firm_to_request(user_with_membership):
    user, membership = user_with_membership
    client = Client()
    client.login(username="preparer1", password="testpass123")
    # The /api/v1/me/ view uses request indirectly; we verify the firm is
    # attached by checking the response contains firm data
    response = client.get("/api/v1/me/")
    assert response.status_code == 200
    assert response.json()["data"]["memberships"][0]["firm_name"] == "Test Tax Firm"
