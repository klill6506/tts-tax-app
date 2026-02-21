import json

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.clients.models import Client as ClientModel, Entity, TaxYear
from apps.firms.models import Firm, FirmMembership, Preparer, Role
from apps.returns.models import FormDefinition, TaxReturn


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


# ---------------------------------------------------------------------------
# Preparer model & API tests
# ---------------------------------------------------------------------------


@pytest.fixture
def other_firm(db):
    return Firm.objects.create(name="Other Firm")


@pytest.fixture
def admin_http(firm):
    user = User.objects.create_user(username="firmadmin", password="testpass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.ADMIN)
    http = Client()
    http.login(username="firmadmin", password="testpass123")
    return user, http


@pytest.fixture
def other_http(other_firm):
    user = User.objects.create_user(username="otherguy", password="testpass123")
    FirmMembership.objects.create(user=user, firm=other_firm, role=Role.ADMIN)
    http = Client()
    http.login(username="otherguy", password="testpass123")
    return user, http


@pytest.fixture
def preparer(firm):
    return Preparer.objects.create(
        firm=firm,
        name="Jane Smith",
        ptin="P12345678",
        firm_name="The Tax Shelter",
        firm_ein="12-3456789",
        firm_phone="555-0100",
        firm_address="123 Main St",
        firm_city="Anytown",
        firm_state="TX",
        firm_zip="75001",
    )


@pytest.mark.django_db
def test_preparer_model_str(preparer):
    assert "Jane Smith" in str(preparer)
    assert "P12345678" in str(preparer)


@pytest.mark.django_db
def test_list_preparers(admin_http, preparer):
    _, http = admin_http
    resp = http.get("/api/v1/preparers/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Jane Smith"


@pytest.mark.django_db
def test_list_excludes_other_firm(admin_http, other_firm):
    _, http = admin_http
    Preparer.objects.create(firm=other_firm, name="Not Mine", ptin="P99999999")
    resp = http.get("/api/v1/preparers/")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


@pytest.mark.django_db
def test_list_requires_auth():
    http = Client()
    resp = http.get("/api/v1/preparers/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_create_preparer(admin_http, firm):
    _, http = admin_http
    resp = http.post(
        "/api/v1/preparers/",
        data=json.dumps({"name": "Bob Jones", "ptin": "P87654321", "is_self_employed": True}),
        content_type="application/json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Bob Jones"
    assert Preparer.objects.get(id=data["id"]).firm_id == firm.id


@pytest.mark.django_db
def test_create_requires_name(admin_http):
    _, http = admin_http
    resp = http.post(
        "/api/v1/preparers/",
        data=json.dumps({"ptin": "P11111111"}),
        content_type="application/json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_retrieve_preparer(admin_http, preparer):
    _, http = admin_http
    resp = http.get(f"/api/v1/preparers/{preparer.id}/")
    assert resp.status_code == 200
    assert resp.json()["firm_address"] == "123 Main St"


@pytest.mark.django_db
def test_cannot_retrieve_other_firm_preparer(other_http, preparer):
    _, http = other_http
    resp = http.get(f"/api/v1/preparers/{preparer.id}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_update_preparer(admin_http, preparer):
    _, http = admin_http
    resp = http.patch(
        f"/api/v1/preparers/{preparer.id}/",
        data=json.dumps({"ptin": "P99999999", "is_active": False}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["ptin"] == "P99999999"
    assert resp.json()["is_active"] is False


@pytest.mark.django_db
def test_cannot_update_other_firm_preparer(other_http, preparer):
    _, http = other_http
    resp = http.patch(
        f"/api/v1/preparers/{preparer.id}/",
        data=json.dumps({"name": "Hacked"}),
        content_type="application/json",
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_delete_preparer(admin_http, preparer):
    _, http = admin_http
    resp = http.delete(f"/api/v1/preparers/{preparer.id}/")
    assert resp.status_code == 204
    assert not Preparer.objects.filter(id=preparer.id).exists()


@pytest.mark.django_db
def test_cannot_delete_other_firm_preparer(other_http, preparer):
    _, http = other_http
    resp = http.delete(f"/api/v1/preparers/{preparer.id}/")
    assert resp.status_code == 404
    assert Preparer.objects.filter(id=preparer.id).exists()


# ---------------------------------------------------------------------------
# Preparer ↔ TaxReturn linking via update_info
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_assign_preparer_to_return(admin_http, firm, preparer):
    _, http = admin_http
    fd = FormDefinition.objects.create(code="1120-S-link", name="Test", tax_year_applicable=2025)
    cl = ClientModel.objects.create(firm=firm, name="Link Client")
    ent = Entity.objects.create(client=cl, name="Link Entity")
    ty = TaxYear.objects.create(entity=ent, year=2025)
    tr = TaxReturn.objects.create(tax_year=ty, form_definition=fd)

    resp = http.patch(
        f"/api/v1/tax-returns/{tr.id}/info/",
        data=json.dumps({"preparer": str(preparer.id), "signature_date": "2026-02-21"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["preparer"] == str(preparer.id)
    assert data["preparer_display_name"] == "Jane Smith"
    assert data["signature_date"] == "2026-02-21"


@pytest.mark.django_db
def test_clear_preparer_from_return(admin_http, firm, preparer):
    _, http = admin_http
    fd = FormDefinition.objects.create(code="1120-S-clear", name="Test", tax_year_applicable=2025)
    cl = ClientModel.objects.create(firm=firm, name="Clear Client")
    ent = Entity.objects.create(client=cl, name="Clear Entity")
    ty = TaxYear.objects.create(entity=ent, year=2025)
    tr = TaxReturn.objects.create(tax_year=ty, form_definition=fd, preparer=preparer)

    resp = http.patch(
        f"/api/v1/tax-returns/{tr.id}/info/",
        data=json.dumps({"preparer": ""}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["preparer"] is None
