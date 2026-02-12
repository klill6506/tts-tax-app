from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as TestClient

from apps.clients.models import Client, Entity, TaxYear
from apps.diagnostics.models import DiagnosticRule, RunStatus, Severity
from apps.diagnostics.runner import run_diagnostics, seed_builtin_rules
from apps.firms.models import Firm, FirmMembership, Role
from apps.imports.models import TrialBalanceRow, TrialBalanceUpload, UploadStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Diag Test Firm")


@pytest.fixture
def user_and_http(firm):
    user = User.objects.create_user(username="diaguser", password="testpass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.ADMIN)
    http = TestClient()
    http.login(username="diaguser", password="testpass123")
    return user, http


@pytest.fixture
def tax_year(firm):
    client = Client.objects.create(firm=firm, name="Diag Client")
    entity = Entity.objects.create(client=client, name="Diag S-Corp")
    return TaxYear.objects.create(entity=entity, year=2025)


@pytest.fixture
def rules(db):
    seed_builtin_rules()
    return DiagnosticRule.objects.all()


@pytest.fixture
def balanced_upload(tax_year):
    """TB upload where debits == credits."""
    file = SimpleUploadedFile("tb.csv", b"fake", content_type="text/csv")
    upload = TrialBalanceUpload.objects.create(
        tax_year=tax_year,
        original_filename="tb.csv",
        file=file,
        status=UploadStatus.PARSED,
        row_count=2,
    )
    TrialBalanceRow.objects.bulk_create([
        TrialBalanceRow(
            upload=upload, row_number=1,
            account_number="1000", account_name="Cash",
            debit=Decimal("50000"), credit=Decimal("0"),
        ),
        TrialBalanceRow(
            upload=upload, row_number=2,
            account_number="3000", account_name="Equity",
            debit=Decimal("0"), credit=Decimal("50000"),
        ),
    ])
    return upload


@pytest.fixture
def unbalanced_upload(tax_year):
    """TB upload where debits != credits."""
    file = SimpleUploadedFile("tb.csv", b"fake", content_type="text/csv")
    upload = TrialBalanceUpload.objects.create(
        tax_year=tax_year,
        original_filename="tb.csv",
        file=file,
        status=UploadStatus.PARSED,
        row_count=2,
    )
    TrialBalanceRow.objects.bulk_create([
        TrialBalanceRow(
            upload=upload, row_number=1,
            account_number="1000", account_name="Cash",
            debit=Decimal("50000"), credit=Decimal("0"),
        ),
        TrialBalanceRow(
            upload=upload, row_number=2,
            account_number="3000", account_name="Equity",
            debit=Decimal("0"), credit=Decimal("30000"),
        ),
    ])
    return upload


# ---------------------------------------------------------------------------
# Rule function unit tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRuleFunctions:
    def test_tb_exists_fails_when_no_upload(self, rules, tax_year):
        from apps.diagnostics.rules import tb_exists_check

        findings = tb_exists_check(tax_year)
        assert len(findings) == 1
        assert findings[0]["severity"] == "error"

    def test_tb_exists_passes_with_upload(self, rules, balanced_upload, tax_year):
        from apps.diagnostics.rules import tb_exists_check

        findings = tb_exists_check(tax_year)
        assert len(findings) == 0

    def test_tb_balance_passes(self, rules, balanced_upload, tax_year):
        from apps.diagnostics.rules import tb_balance_check

        findings = tb_balance_check(tax_year)
        assert len(findings) == 0

    def test_tb_balance_fails(self, rules, unbalanced_upload, tax_year):
        from apps.diagnostics.rules import tb_balance_check

        findings = tb_balance_check(tax_year)
        assert len(findings) == 1
        assert "out of balance" in findings[0]["message"]

    def test_zero_rows_check(self, rules, tax_year):
        file = SimpleUploadedFile("tb.csv", b"fake", content_type="text/csv")
        upload = TrialBalanceUpload.objects.create(
            tax_year=tax_year,
            original_filename="tb.csv",
            file=file,
            status=UploadStatus.PARSED,
        )
        TrialBalanceRow.objects.create(
            upload=upload, row_number=1,
            account_number="9999", account_name="Inactive",
            debit=Decimal("0"), credit=Decimal("0"),
        )
        from apps.diagnostics.rules import tb_zero_rows_check

        findings = tb_zero_rows_check(tax_year)
        assert len(findings) == 1
        assert findings[0]["severity"] == "info"


# ---------------------------------------------------------------------------
# Runner tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRunner:
    def test_run_with_no_tb(self, rules, tax_year):
        run = run_diagnostics(tax_year)
        assert run.status == RunStatus.COMPLETED
        assert run.finding_count >= 1  # At least TB_EXISTS should fire
        assert run.completed_at is not None

    def test_run_with_balanced_tb(self, rules, balanced_upload, tax_year):
        run = run_diagnostics(tax_year)
        # TB exists = pass, TB balance = pass, zero rows = pass
        # So only zero findings expected (none of the errors should fire)
        error_findings = run.findings.filter(severity=Severity.ERROR)
        assert error_findings.count() == 0

    def test_run_with_unbalanced_tb(self, rules, unbalanced_upload, tax_year):
        run = run_diagnostics(tax_year)
        error_findings = run.findings.filter(severity=Severity.ERROR)
        assert error_findings.count() >= 1
        messages = [f.message for f in error_findings]
        assert any("out of balance" in m for m in messages)

    def test_seed_is_idempotent(self, db):
        seed_builtin_rules()
        count1 = DiagnosticRule.objects.count()
        seed_builtin_rules()
        count2 = DiagnosticRule.objects.count()
        assert count1 == count2


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDiagnosticsEndpoints:
    def test_list_rules(self, user_and_http, rules):
        _, http = user_and_http
        resp = http.get("/api/v1/diagnostic-rules/")
        assert resp.status_code == 200
        assert len(resp.json()) == 3  # 3 built-in rules

    def test_run_diagnostics_endpoint(self, user_and_http, rules, tax_year):
        _, http = user_and_http
        resp = http.post(
            "/api/v1/diagnostic-runs/run/",
            data={"tax_year": str(tax_year.id)},
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "completed"
        assert "findings" in data

    def test_run_with_balanced_tb(
        self, user_and_http, rules, balanced_upload, tax_year
    ):
        _, http = user_and_http
        resp = http.post(
            "/api/v1/diagnostic-runs/run/",
            data={"tax_year": str(tax_year.id)},
            content_type="application/json",
        )
        assert resp.status_code == 201
        errors = [
            f for f in resp.json()["findings"] if f["severity"] == "error"
        ]
        assert len(errors) == 0

    def test_list_past_runs(self, user_and_http, rules, tax_year):
        _, http = user_and_http
        # Create a run first
        http.post(
            "/api/v1/diagnostic-runs/run/",
            data={"tax_year": str(tax_year.id)},
            content_type="application/json",
        )
        resp = http.get(f"/api/v1/diagnostic-runs/?tax_year={tax_year.id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_wrong_tax_year_returns_404(self, user_and_http, rules):
        _, http = user_and_http
        import uuid

        resp = http.post(
            "/api/v1/diagnostic-runs/run/",
            data={"tax_year": str(uuid.uuid4())},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_requires_auth(self):
        http = TestClient()
        resp = http.get("/api/v1/diagnostic-rules/")
        assert resp.status_code == 403

    def test_firm_isolation(self, user_and_http, rules, tax_year):
        _, http = user_and_http
        # Run diagnostics as our user
        http.post(
            "/api/v1/diagnostic-runs/run/",
            data={"tax_year": str(tax_year.id)},
            content_type="application/json",
        )
        # Another firm's user can't see the run
        other_firm = Firm.objects.create(name="Other Firm")
        other_user = User.objects.create_user(username="other", password="testpass123")
        FirmMembership.objects.create(
            user=other_user, firm=other_firm, role=Role.PREPARER
        )
        other_http = TestClient()
        other_http.login(username="other", password="testpass123")
        resp = other_http.get("/api/v1/diagnostic-runs/")
        assert len(resp.json()) == 0
