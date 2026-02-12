import pytest
from django.contrib.auth.models import User
from django.test import Client as TestClient

from apps.audit.models import AuditAction, AuditEntry
from apps.audit.service import PII_FIELDS, log_create, log_delete, log_update, snapshot
from apps.clients.models import Client, Entity
from apps.firms.models import Firm, FirmMembership, Role


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Audit Test Firm")


@pytest.fixture
def user_and_http(firm):
    user = User.objects.create_user(username="auditor", password="testpass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.ADMIN)
    http = TestClient()
    http.login(username="auditor", password="testpass123")
    return user, http


@pytest.fixture
def sample_client(firm):
    return Client.objects.create(firm=firm, name="Audit Client")


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuditService:
    def test_log_create(self, user_and_http, sample_client):
        user, http = user_and_http
        # Simulate via the service directly
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        request.firm = sample_client.firm

        entry = log_create(request, sample_client)
        assert entry.action == AuditAction.CREATE
        assert entry.model_name == "clients.Client"
        assert entry.record_id == str(sample_client.pk)
        assert entry.actor == user

    def test_log_update_captures_changes(self, user_and_http, sample_client):
        user, _ = user_and_http
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        request.firm = sample_client.firm

        old_snap = snapshot(sample_client)
        sample_client.name = "Updated Name"
        sample_client.save()

        entry = log_update(request, sample_client, old_snap)
        assert entry is not None
        assert entry.action == AuditAction.UPDATE
        assert "name" in entry.changes
        assert entry.changes["name"]["old"] == "Audit Client"
        assert entry.changes["name"]["new"] == "Updated Name"

    def test_log_update_skips_noop(self, user_and_http, sample_client):
        user, _ = user_and_http
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        request.firm = sample_client.firm

        old_snap = snapshot(sample_client)
        # Don't change anything
        entry = log_update(request, sample_client, old_snap)
        assert entry is None

    def test_log_delete(self, user_and_http, sample_client):
        user, _ = user_and_http
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        request.firm = sample_client.firm

        entry = log_delete(request, sample_client)
        assert entry.action == AuditAction.DELETE

    def test_pii_fields_redacted(self):
        """Ensure known PII field names are in the redaction set."""
        assert "ssn" in PII_FIELDS
        assert "ein" in PII_FIELDS
        assert "itin" in PII_FIELDS


# ---------------------------------------------------------------------------
# Integration: CRUD endpoints produce audit entries
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuditIntegration:
    def test_create_client_produces_audit_entry(self, user_and_http):
        _, http = user_and_http
        resp = http.post(
            "/api/v1/clients/",
            data={"name": "New Audited Client"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        entries = AuditEntry.objects.filter(action=AuditAction.CREATE)
        assert entries.count() == 1
        assert entries[0].model_name == "clients.Client"

    def test_update_client_produces_audit_entry(self, user_and_http, sample_client):
        _, http = user_and_http
        http.patch(
            f"/api/v1/clients/{sample_client.id}/",
            data={"name": "Renamed"},
            content_type="application/json",
        )
        entries = AuditEntry.objects.filter(action=AuditAction.UPDATE)
        assert entries.count() == 1
        assert entries[0].changes["name"]["new"] == "Renamed"

    def test_delete_client_produces_audit_entry(self, user_and_http, sample_client):
        _, http = user_and_http
        resp = http.delete(f"/api/v1/clients/{sample_client.id}/")
        assert resp.status_code == 204
        entries = AuditEntry.objects.filter(action=AuditAction.DELETE)
        assert entries.count() == 1


# ---------------------------------------------------------------------------
# Audit log API (read-only)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuditLogEndpoint:
    def test_list_audit_log(self, user_and_http, sample_client):
        user, http = user_and_http
        # Create an audit entry via the client endpoint
        http.post(
            "/api/v1/clients/",
            data={"name": "Logged Client"},
            content_type="application/json",
        )
        resp = http.get("/api/v1/audit-log/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_filter_by_model(self, user_and_http):
        _, http = user_and_http
        http.post(
            "/api/v1/clients/",
            data={"name": "Filter Test"},
            content_type="application/json",
        )
        resp = http.get("/api/v1/audit-log/?model=Client")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_filter_by_action(self, user_and_http):
        _, http = user_and_http
        http.post(
            "/api/v1/clients/",
            data={"name": "Action Test"},
            content_type="application/json",
        )
        resp = http.get("/api/v1/audit-log/?action=create")
        assert resp.status_code == 200
        assert all(e["action"] == "create" for e in resp.json())

    def test_audit_log_requires_auth(self):
        http = TestClient()
        resp = http.get("/api/v1/audit-log/")
        assert resp.status_code == 403

    def test_audit_log_is_read_only(self, user_and_http):
        _, http = user_and_http
        resp = http.post(
            "/api/v1/audit-log/",
            data={},
            content_type="application/json",
        )
        assert resp.status_code == 405  # Method Not Allowed
