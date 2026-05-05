"""Tests for apps.documents — model, list/upload/folders endpoints, permissions."""
import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.clients.models import Client, Entity, EntityType
from apps.documents.models import ClientDocument, DocumentCategory
from apps.firms.models import Firm, FirmMembership, Role


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test Firm Documents")


@pytest.fixture
def other_firm(db):
    return Firm.objects.create(name="Other Firm Documents")


@pytest.fixture
def member_user(firm):
    user = User.objects.create_user(username="docs_preparer", password="x")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    return user


@pytest.fixture
def authed_api(member_user):
    api = APIClient()
    api.force_login(member_user)
    return api


@pytest.fixture
def sample_client(firm):
    return Client.objects.create(firm=firm, name="Acme Corp")


@pytest.fixture
def sample_entity(sample_client):
    return Entity.objects.create(
        client=sample_client, name="Acme S-Corp", entity_type=EntityType.SCORP,
    )


def _fake_upload(name="form.pdf", content=b"%PDF-1.4 fake bytes"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestClientDocumentModel:
    def test_create(self, firm, sample_client, sample_entity, member_user):
        doc = ClientDocument.objects.create(
            firm=firm, client=sample_client, entity=sample_entity,
            file=_fake_upload(), filename="form.pdf", file_size=42,
            content_type="application/pdf",
            category=DocumentCategory.W2, tax_year=2025,
            uploaded_by=member_user,
        )
        assert doc.id is not None
        assert doc.firm == firm
        assert doc.entity == sample_entity
        assert doc.category == "w2"
        assert doc.tax_year == 2025
        assert "W-2" in str(doc)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDocumentEndpoints:
    def test_list_empty(self, authed_api):
        resp = authed_api.get("/api/v1/documents/")
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_upload_creates_document(self, authed_api, sample_entity):
        resp = authed_api.post(
            "/api/v1/documents/upload/",
            data={
                "entity": str(sample_entity.id),
                "file": _fake_upload("w2.pdf"),
                "category": "w2",
                "tax_year": 2025,
                "notes": "Synthetic",
            },
            format="multipart",
        )
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["filename"] == "w2.pdf"
        assert body["category"] == "w2"
        assert body["tax_year"] == 2025
        assert ClientDocument.objects.filter(entity=sample_entity).count() == 1

    def test_upload_rejects_entity_in_other_firm(self, authed_api, other_firm):
        outsider_client = Client.objects.create(firm=other_firm, name="Foreign Co")
        outsider_entity = Entity.objects.create(
            client=outsider_client, name="Foreign LLC", entity_type=EntityType.PARTNERSHIP,
        )
        resp = authed_api.post(
            "/api/v1/documents/upload/",
            data={"entity": str(outsider_entity.id), "file": _fake_upload(), "category": "other"},
            format="multipart",
        )
        assert resp.status_code == 404

    def test_folders_aggregates_by_entity(self, authed_api, firm, sample_client, sample_entity, member_user):
        ClientDocument.objects.create(
            firm=firm, client=sample_client, entity=sample_entity,
            file=_fake_upload("a.pdf"), filename="a.pdf", file_size=10,
            category=DocumentCategory.W2, uploaded_by=member_user,
        )
        ClientDocument.objects.create(
            firm=firm, client=sample_client, entity=sample_entity,
            file=_fake_upload("b.pdf"), filename="b.pdf", file_size=15,
            category=DocumentCategory.RECEIPT, uploaded_by=member_user,
        )
        resp = authed_api.get("/api/v1/documents/folders/")
        assert resp.status_code == 200
        body = resp.json()
        assert "counts" in body
        assert body["counts"]["all"] == 1  # one entity
        assert body["counts"]["scorp"] == 1
        assert len(body["results"]) == 1
        row = body["results"][0]
        assert row["entity_id"] == str(sample_entity.id)
        assert row["document_count"] == 2
        assert row["total_size"] == 25


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPermissions:
    def test_unauthenticated_list_denied(self, db):
        resp = APIClient().get("/api/v1/documents/")
        assert resp.status_code in (401, 403)

    def test_authed_but_no_firm_membership_denied(self, db):
        loner = User.objects.create_user(username="no_firm", password="x")
        api = APIClient()
        api.force_login(loner)
        resp = api.get("/api/v1/documents/")
        assert resp.status_code == 403
