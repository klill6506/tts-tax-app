import io
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as TestClient

from apps.clients.models import Client, Entity, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.imports.models import TrialBalanceUpload, UploadStatus
from apps.mappings.engine import apply_template, resolve_template
from apps.mappings.models import MappingRule, MappingTemplate, MatchMode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Mapping Test Firm")


@pytest.fixture
def user_and_http(firm):
    user = User.objects.create_user(username="mapper", password="testpass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.ADMIN)
    http = TestClient()
    http.login(username="mapper", password="testpass123")
    return user, http


@pytest.fixture
def client_obj(firm):
    return Client.objects.create(firm=firm, name="Mapping Client")


@pytest.fixture
def tax_year(client_obj):
    entity = Entity.objects.create(client=client_obj, name="Map S-Corp")
    return TaxYear.objects.create(entity=entity, year=2025)


@pytest.fixture
def firm_template(firm):
    return MappingTemplate.objects.create(
        firm=firm, name="Firm Default", is_default=True
    )


@pytest.fixture
def client_template(firm, client_obj):
    return MappingTemplate.objects.create(
        firm=firm, client=client_obj, name="Client Override"
    )


@pytest.fixture
def upload_with_rows(tax_year):
    """Create a TB upload with 3 parsed rows."""
    csv_content = (
        "Account Number,Account Name,Debit,Credit\n"
        "1000,Cash,50000,0\n"
        "4000,Revenue,0,100000\n"
        "5000,COGS,60000,0\n"
    )
    file = SimpleUploadedFile("tb.csv", csv_content.encode(), content_type="text/csv")
    upload = TrialBalanceUpload.objects.create(
        tax_year=tax_year,
        original_filename="tb.csv",
        file=file,
        status=UploadStatus.PARSED,
        row_count=3,
    )
    from apps.imports.models import TrialBalanceRow

    TrialBalanceRow.objects.bulk_create([
        TrialBalanceRow(
            upload=upload, row_number=1,
            account_number="1000", account_name="Cash",
            debit=Decimal("50000"), credit=Decimal("0"),
        ),
        TrialBalanceRow(
            upload=upload, row_number=2,
            account_number="4000", account_name="Revenue",
            debit=Decimal("0"), credit=Decimal("100000"),
        ),
        TrialBalanceRow(
            upload=upload, row_number=3,
            account_number="5000", account_name="COGS",
            debit=Decimal("60000"), credit=Decimal("0"),
        ),
    ])
    return upload


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMappingModels:
    def test_create_template(self, firm):
        t = MappingTemplate.objects.create(firm=firm, name="Test Template")
        assert str(t) == "Test Template (firm default)"
        assert t.is_default is False

    def test_create_rule_exact(self, firm_template):
        r = MappingRule.objects.create(
            template=firm_template,
            match_mode=MatchMode.EXACT,
            match_value="1000",
            target_line="1120S_L1a",
        )
        assert r.matches("1000", "Cash") is True
        assert r.matches("1001", "Cash") is False

    def test_create_rule_prefix(self, firm_template):
        r = MappingRule.objects.create(
            template=firm_template,
            match_mode=MatchMode.PREFIX,
            match_value="40",
            target_line="1120S_L1a",
        )
        assert r.matches("4000", "Revenue") is True
        assert r.matches("4001", "Other Revenue") is True
        assert r.matches("5000", "COGS") is False

    def test_create_rule_contains(self, firm_template):
        r = MappingRule.objects.create(
            template=firm_template,
            match_mode=MatchMode.CONTAINS,
            match_value="revenue",
            target_line="1120S_L1a",
        )
        assert r.matches("4000", "Revenue") is True
        assert r.matches("4000", "Other Revenue Items") is True
        assert r.matches("5000", "COGS") is False


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMappingEngine:
    def test_resolve_firm_default(self, firm, firm_template):
        t = resolve_template(firm)
        assert t == firm_template

    def test_resolve_client_override(self, firm, firm_template, client_template, client_obj):
        t = resolve_template(firm, client_obj)
        assert t == client_template

    def test_resolve_falls_back_to_firm(self, firm, firm_template):
        other_client = Client.objects.create(firm=firm, name="No Override")
        t = resolve_template(firm, other_client)
        assert t == firm_template

    def test_apply_template(self, firm_template, upload_with_rows):
        MappingRule.objects.create(
            template=firm_template,
            match_mode=MatchMode.EXACT,
            match_value="1000",
            target_line="Balance_Cash",
            target_description="Cash and equivalents",
        )
        MappingRule.objects.create(
            template=firm_template,
            match_mode=MatchMode.PREFIX,
            match_value="40",
            target_line="1120S_L1a",
            target_description="Gross receipts",
        )

        results = apply_template(firm_template, upload_with_rows)
        assert len(results) == 3

        # Cash matched exact
        assert results[0].target_line == "Balance_Cash"
        # Revenue matched prefix
        assert results[1].target_line == "1120S_L1a"
        # COGS not matched
        assert results[2].target_line is None

    def test_priority_ordering(self, firm_template, upload_with_rows):
        # Low priority: broad prefix match
        MappingRule.objects.create(
            template=firm_template,
            match_mode=MatchMode.PREFIX,
            match_value="10",
            target_line="broad_match",
            priority=0,
        )
        # High priority: exact match
        MappingRule.objects.create(
            template=firm_template,
            match_mode=MatchMode.EXACT,
            match_value="1000",
            target_line="exact_match",
            priority=10,
        )

        results = apply_template(firm_template, upload_with_rows)
        # Higher priority rule should win
        assert results[0].target_line == "exact_match"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMappingEndpoints:
    def test_create_template(self, user_and_http):
        _, http = user_and_http
        resp = http.post(
            "/api/v1/mapping-templates/",
            data={"name": "My Template", "is_default": True},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "My Template"

    def test_create_client_template(self, user_and_http, client_obj):
        _, http = user_and_http
        resp = http.post(
            "/api/v1/mapping-templates/",
            data={
                "name": "Client Template",
                "client": str(client_obj.id),
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        template_id = resp.json()["id"]
        # Verify via detail endpoint (uses read serializer with client_name)
        detail = http.get(f"/api/v1/mapping-templates/{template_id}/")
        assert detail.json()["client_name"] == "Mapping Client"

    def test_list_templates(self, user_and_http, firm_template):
        _, http = user_and_http
        resp = http.get("/api/v1/mapping-templates/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_create_rule(self, user_and_http, firm_template):
        _, http = user_and_http
        resp = http.post(
            "/api/v1/mapping-rules/",
            data={
                "template": str(firm_template.id),
                "match_mode": "exact",
                "match_value": "1000",
                "target_line": "1120S_L1a",
                "target_description": "Gross receipts",
                "priority": 0,
            },
            content_type="application/json",
        )
        assert resp.status_code == 201

    def test_apply_mapping_endpoint(
        self, user_and_http, firm_template, upload_with_rows
    ):
        MappingRule.objects.create(
            template=firm_template,
            match_mode=MatchMode.EXACT,
            match_value="1000",
            target_line="Balance_Cash",
        )
        _, http = user_and_http
        resp = http.post(
            "/api/v1/mapping-templates/apply/",
            data={
                "upload": str(upload_with_rows.id),
                "template": str(firm_template.id),
            },
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rows"] == 3
        assert data["mapped_rows"] == 1
        assert data["unmapped_rows"] == 2

    def test_apply_mapping_auto_resolve(
        self, user_and_http, firm_template, upload_with_rows
    ):
        """When no template specified, auto-resolves firm default."""
        MappingRule.objects.create(
            template=firm_template,
            match_mode=MatchMode.PREFIX,
            match_value="40",
            target_line="1120S_L1a",
        )
        _, http = user_and_http
        resp = http.post(
            "/api/v1/mapping-templates/apply/",
            data={"upload": str(upload_with_rows.id)},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["mapped_rows"] == 1

    def test_requires_auth(self):
        http = TestClient()
        resp = http.get("/api/v1/mapping-templates/")
        assert resp.status_code == 403

    def test_firm_isolation(self, user_and_http, firm_template):
        other_firm = Firm.objects.create(name="Other Firm")
        other_user = User.objects.create_user(username="other", password="testpass123")
        FirmMembership.objects.create(
            user=other_user, firm=other_firm, role=Role.PREPARER
        )
        other_http = TestClient()
        other_http.login(username="other", password="testpass123")
        resp = other_http.get("/api/v1/mapping-templates/")
        assert len(resp.json()) == 0
