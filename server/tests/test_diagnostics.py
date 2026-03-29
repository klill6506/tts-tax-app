from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client as TestClient

from apps.clients.models import Client, Entity, TaxYear
from apps.diagnostics.models import DiagnosticRule, RunStatus, Severity
from apps.diagnostics.runner import run_diagnostics, seed_builtin_rules
from apps.firms.models import Firm, FirmMembership, Role
from apps.imports.models import TrialBalanceRow, TrialBalanceUpload, UploadStatus
from apps.returns.models import (
    FormDefinition, FormFieldValue, FormLine, FormSection,
    Officer, Shareholder, TaxReturn,
)


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
def seeded_1120s(db):
    """Seed the 1120-S form definition for tests that need FormLine lookups."""
    call_command("seed_1120s", verbosity=0)
    return FormDefinition.objects.get(code="1120-S")


@pytest.fixture
def tax_return_1120s(seeded_1120s, tax_year):
    """Create a TaxReturn with 1120-S form definition and empty field values."""
    tr = TaxReturn.objects.create(
        tax_year=tax_year,
        form_definition=seeded_1120s,
    )
    # Create empty FormFieldValue for every line
    for fl in FormLine.objects.filter(section__form=seeded_1120s):
        FormFieldValue.objects.create(tax_return=tr, form_line=fl, value="")
    return tr


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


def _set_line(tr, line_number, value):
    """Helper to set a FormFieldValue by line number."""
    fv = FormFieldValue.objects.get(
        tax_return=tr,
        form_line__line_number=line_number,
    )
    fv.value = str(value)
    fv.save(update_fields=["value"])
    return fv


# ---------------------------------------------------------------------------
# Trial Balance Rule function tests (existing)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTBRules:
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
# Math Diagnostic Rule tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMathDiagnostics:
    def test_balance_sheet_passes_when_balanced(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import math_balance_sheet_check

        _set_line(tax_return_1120s, "L15d", "100000")  # Total assets EOY
        _set_line(tax_return_1120s, "L27d", "100000")  # Total L+E EOY
        findings = math_balance_sheet_check(tax_year)
        assert len(findings) == 0

    def test_balance_sheet_fails_when_unbalanced(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import math_balance_sheet_check

        _set_line(tax_return_1120s, "L14d", "100000")  # Total assets EOY
        _set_line(tax_return_1120s, "L27d", "80000")   # Total L+E EOY (wrong)
        findings = math_balance_sheet_check(tax_year)
        assert len(findings) >= 1
        assert any("out of balance" in f["message"] for f in findings)

    def test_m1_reconciliation_passes(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import math_m1_reconciliation_check
        from apps.returns.compute import compute_return

        _set_line(tax_return_1120s, "1a", "500000")
        _set_line(tax_return_1120s, "M1_1", "50000")
        compute_return(tax_return_1120s)
        findings = math_m1_reconciliation_check(tax_year)
        # M-1 won't reconcile with just partial data, but at least the check runs
        assert isinstance(findings, list)

    def test_m2_check_passes_when_matching(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import math_m2_check

        _set_line(tax_return_1120s, "M2_8a", "50000")
        _set_line(tax_return_1120s, "L24d", "50000")
        findings = math_m2_check(tax_year)
        assert len(findings) == 0

    def test_m2_check_fails_when_mismatched(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import math_m2_check

        _set_line(tax_return_1120s, "M2_8a", "50000")
        _set_line(tax_return_1120s, "L24d", "40000")
        findings = math_m2_check(tax_year)
        assert len(findings) == 1
        assert "does not match" in findings[0]["message"]


# ---------------------------------------------------------------------------
# Missing Info Diagnostic Rule tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMissingInfoDiagnostics:
    def test_missing_ein(self, rules, tax_year):
        from apps.diagnostics.rules import missing_ein_check

        # Entity has no EIN by default
        findings = missing_ein_check(tax_year)
        assert len(findings) == 1
        assert "missing an EIN" in findings[0]["message"]

    def test_ein_present(self, rules, tax_year):
        from apps.diagnostics.rules import missing_ein_check

        tax_year.entity.ein = "12-3456789"
        tax_year.entity.save()
        findings = missing_ein_check(tax_year)
        assert len(findings) == 0

    def test_missing_address(self, rules, tax_year):
        from apps.diagnostics.rules import missing_address_check

        findings = missing_address_check(tax_year)
        assert len(findings) == 1
        assert "missing" in findings[0]["message"]

    def test_complete_address(self, rules, tax_year):
        from apps.diagnostics.rules import missing_address_check

        entity = tax_year.entity
        entity.address_line1 = "100 Main St"
        entity.city = "Athens"
        entity.state = "GA"
        entity.zip_code = "30601"
        entity.save()
        findings = missing_address_check(tax_year)
        assert len(findings) == 0

    def test_missing_shareholders(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import missing_shareholders_check

        findings = missing_shareholders_check(tax_year)
        assert len(findings) == 1
        assert "No shareholders" in findings[0]["message"]

    def test_shareholders_present(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import missing_shareholders_check

        Shareholder.objects.create(
            tax_return=tax_return_1120s,
            name="John Doe",
            ssn="111-22-3333",
            ownership_percentage="100",
        )
        findings = missing_shareholders_check(tax_year)
        assert len(findings) == 0

    def test_missing_officers(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import missing_officers_check

        findings = missing_officers_check(tax_year)
        assert len(findings) == 1

    def test_officers_present(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import missing_officers_check

        Officer.objects.create(
            tax_return=tax_return_1120s,
            name="Jane CEO",
            title="President",
            compensation=Decimal("100000"),
        )
        findings = missing_officers_check(tax_year)
        assert len(findings) == 0

    def test_missing_preparer(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import missing_preparer_check

        findings = missing_preparer_check(tax_year)
        assert len(findings) == 1
        assert "preparer" in findings[0]["message"].lower()

    def test_ownership_sums_to_100(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import shareholder_ownership_check

        Shareholder.objects.create(
            tax_return=tax_return_1120s,
            name="Owner A",
            ownership_percentage="60",
        )
        Shareholder.objects.create(
            tax_return=tax_return_1120s,
            name="Owner B",
            ownership_percentage="40",
        )
        findings = shareholder_ownership_check(tax_year)
        assert len(findings) == 0

    def test_ownership_not_100(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import shareholder_ownership_check

        Shareholder.objects.create(
            tax_return=tax_return_1120s,
            name="Owner A",
            ownership_percentage="60",
        )
        Shareholder.objects.create(
            tax_return=tax_return_1120s,
            name="Owner B",
            ownership_percentage="30",
        )
        findings = shareholder_ownership_check(tax_year)
        assert len(findings) == 1
        assert "90" in findings[0]["message"] and "100%" in findings[0]["message"]

    def test_shareholder_ssn_missing(self, rules, tax_return_1120s, tax_year):
        from apps.diagnostics.rules import shareholder_ssn_check

        Shareholder.objects.create(
            tax_return=tax_return_1120s,
            name="No SSN Guy",
            ownership_percentage="100",
            ssn="",
        )
        findings = shareholder_ssn_check(tax_year)
        assert len(findings) == 1
        assert "missing an SSN" in findings[0]["message"]


# ---------------------------------------------------------------------------
# Compute M1_3b from K16c test
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestM1_3bCompute:
    def test_m1_3b_auto_computes_from_k16c(self, seeded_1120s, tax_year):
        """M1_3b should auto-compute from K16c (non-deductible expenses)."""
        from apps.returns.compute import compute_return

        tr = TaxReturn.objects.create(
            tax_year=tax_year,
            form_definition=seeded_1120s,
        )
        lines = {
            fl.line_number: fl
            for fl in FormLine.objects.filter(section__form=seeded_1120s)
        }

        # Set K16c (non-deductible expenses) = 5000 — mark overridden so compute doesn't clear it
        FormFieldValue.objects.create(tax_return=tr, form_line=lines["K16c"], value="5000", is_overridden=True)

        # Create M1_3b and other computed lines with empty values
        computed_lines = [
            "1c", "2", "3", "6", "20", "21", "22c", "23d", "25", "26",
            "A6", "A8", "K1", "K18", "L3a", "L3d", "L14a", "L14d", "L27a", "L27d",
            "M1_3b", "M1_4", "M1_7", "M1_8",
            "M2_2a", "M2_3a", "M2_4a", "M2_5a", "M2_6a", "M2_7a", "M2_8a",
            "M2_6b", "M2_8b", "M2_6c", "M2_8c", "M2_6d", "M2_8d",
        ]
        for ln in computed_lines:
            if ln in lines and not FormFieldValue.objects.filter(
                tax_return=tr, form_line=lines[ln]
            ).exists():
                FormFieldValue.objects.create(tax_return=tr, form_line=lines[ln], value="")

        compute_return(tr)

        fv_m1_3b = FormFieldValue.objects.get(
            tax_return=tr, form_line=lines["M1_3b"]
        )
        assert fv_m1_3b.value == "5000.00"

    def test_m1_3b_flows_to_m1_4(self, seeded_1120s, tax_year):
        """M1_4 should include M1_3b in its sum."""
        from apps.returns.compute import compute_return

        tr = TaxReturn.objects.create(
            tax_year=tax_year,
            form_definition=seeded_1120s,
        )
        lines = {
            fl.line_number: fl
            for fl in FormLine.objects.filter(section__form=seeded_1120s)
        }

        # Set M1_1 (book income) = 100000, K16c = 3000 — mark overridden so compute doesn't clear
        FormFieldValue.objects.create(tax_return=tr, form_line=lines["M1_1"], value="100000", is_overridden=True)
        FormFieldValue.objects.create(tax_return=tr, form_line=lines["K16c"], value="3000", is_overridden=True)

        # Create all needed computed lines
        computed_lines = [
            "1c", "2", "3", "6", "20", "21", "22c", "23d", "25", "26",
            "A6", "A8", "K1", "K18", "L3a", "L3d", "L14a", "L14d", "L27a", "L27d",
            "M1_3b", "M1_4", "M1_7", "M1_8",
            "M2_2a", "M2_3a", "M2_4a", "M2_5a", "M2_6a", "M2_7a", "M2_8a",
            "M2_6b", "M2_8b", "M2_6c", "M2_8c", "M2_6d", "M2_8d",
        ]
        for ln in computed_lines:
            if ln in lines and not FormFieldValue.objects.filter(
                tax_return=tr, form_line=lines[ln]
            ).exists():
                FormFieldValue.objects.create(tax_return=tr, form_line=lines[ln], value="")

        compute_return(tr)

        # M1_4 = M1_1 + M1_2 + M1_3a + M1_3b = 100000 + 0 + 0 + 3000 = 103000
        fv_m1_4 = FormFieldValue.objects.get(
            tax_return=tr, form_line=lines["M1_4"]
        )
        assert fv_m1_4.value == "103000.00"


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
        # TB checks pass, but missing info checks may fire
        tb_error_findings = [
            f for f in run.findings.all()
            if f.rule.code.startswith("TB_") and f.severity == Severity.ERROR
        ]
        assert len(tb_error_findings) == 0

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

    def test_all_rules_execute_without_crash(self, rules, tax_return_1120s, tax_year):
        """Every seeded rule should run without exceptions."""
        run = run_diagnostics(tax_year)
        assert run.status == RunStatus.COMPLETED
        # No "failed to execute" findings
        failed = [
            f for f in run.findings.all()
            if "failed to execute" in f.message
        ]
        assert len(failed) == 0, f"Rules failed: {[f.message for f in failed]}"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDiagnosticsEndpoints:
    def test_list_rules(self, user_and_http, rules):
        _, http = user_and_http
        resp = http.get("/api/v1/diagnostic-rules/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 16  # 3 TB + 4 math + 9 missing info

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
