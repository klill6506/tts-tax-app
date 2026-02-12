import io
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as TestClient

from apps.clients.models import Client, Entity, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.imports.models import TrialBalanceRow, TrialBalanceUpload, UploadStatus
from apps.imports.parsers import ParseError, parse_csv, parse_file


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Import Test Firm")


@pytest.fixture
def user_and_http(firm):
    user = User.objects.create_user(username="importer", password="testpass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    http = TestClient()
    http.login(username="importer", password="testpass123")
    return user, http


@pytest.fixture
def tax_year(firm):
    client = Client.objects.create(firm=firm, name="Import Client")
    entity = Entity.objects.create(client=client, name="Import S-Corp")
    return TaxYear.objects.create(entity=entity, year=2025)


SAMPLE_CSV = (
    "Account Number,Account Name,Debit,Credit\n"
    "1000,Cash,50000.00,0.00\n"
    "2000,Accounts Payable,0.00,15000.00\n"
    "3000,Retained Earnings,0.00,35000.00\n"
)

SAMPLE_CSV_ALT_HEADERS = (
    "Acct No,Description,Dr,Cr\n"
    "1000,Cash,50000,0\n"
    "2000,AP,0,15000\n"
)


def _make_csv_file(content: str, name: str = "tb.csv") -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name=name,
        content=content.encode("utf-8"),
        content_type="text/csv",
    )


def _make_xlsx_file():
    """Create a minimal XLSX file in memory."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Account Number", "Account Name", "Debit", "Credit"])
    ws.append(["1000", "Cash", 50000.00, 0.00])
    ws.append(["2000", "Accounts Payable", 0.00, 15000.00])
    ws.append(["3000", "Retained Earnings", 0.00, 35000.00])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return SimpleUploadedFile(
        name="tb.xlsx",
        content=buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
# Parser unit tests
# ---------------------------------------------------------------------------

class TestCSVParser:
    def test_parse_standard_csv(self):
        file = _make_csv_file(SAMPLE_CSV)
        rows = parse_csv(file)
        assert len(rows) == 3
        assert rows[0]["account_number"] == "1000"
        assert rows[0]["account_name"] == "Cash"
        assert rows[0]["debit"] == Decimal("50000.00")
        assert rows[0]["credit"] == Decimal("0.00")

    def test_parse_alt_headers(self):
        file = _make_csv_file(SAMPLE_CSV_ALT_HEADERS)
        rows = parse_csv(file)
        assert len(rows) == 2
        assert rows[0]["account_number"] == "1000"

    def test_skips_blank_rows(self):
        csv_with_blanks = SAMPLE_CSV + "\n\n\n"
        file = _make_csv_file(csv_with_blanks)
        rows = parse_csv(file)
        assert len(rows) == 3  # blanks skipped

    def test_empty_file_raises(self):
        file = _make_csv_file("Header Only\n")
        with pytest.raises(ParseError):
            parse_csv(file)

    def test_commas_in_amounts(self):
        csv = "Account Number,Account Name,Debit,Credit\n1000,Cash,\"50,000.00\",0\n"
        file = _make_csv_file(csv)
        rows = parse_csv(file)
        assert rows[0]["debit"] == Decimal("50000.00")


class TestXLSXParser:
    def test_parse_xlsx(self):
        file = _make_xlsx_file()
        rows = parse_file(file)
        assert len(rows) == 3
        assert rows[0]["account_number"] == "1000"
        assert rows[0]["debit"] == Decimal("50000.00")


class TestFileRouting:
    def test_unsupported_extension(self):
        file = SimpleUploadedFile("tb.pdf", b"fake", content_type="application/pdf")
        with pytest.raises(ParseError, match="Unsupported"):
            parse_file(file)


# ---------------------------------------------------------------------------
# Upload endpoint integration tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUploadEndpoint:
    def test_upload_csv(self, user_and_http, tax_year):
        _, http = user_and_http
        csv_file = _make_csv_file(SAMPLE_CSV)
        resp = http.post(
            "/api/v1/tb-uploads/upload/",
            data={"tax_year": str(tax_year.id), "file": csv_file},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "parsed"
        assert data["row_count"] == 3
        assert TrialBalanceRow.objects.count() == 3

    def test_upload_xlsx(self, user_and_http, tax_year):
        _, http = user_and_http
        xlsx_file = _make_xlsx_file()
        resp = http.post(
            "/api/v1/tb-uploads/upload/",
            data={"tax_year": str(tax_year.id), "file": xlsx_file},
        )
        assert resp.status_code == 201
        assert resp.json()["row_count"] == 3

    def test_upload_bad_extension(self, user_and_http, tax_year):
        _, http = user_and_http
        bad_file = SimpleUploadedFile("tb.pdf", b"fake", content_type="application/pdf")
        resp = http.post(
            "/api/v1/tb-uploads/upload/",
            data={"tax_year": str(tax_year.id), "file": bad_file},
        )
        assert resp.status_code == 400

    def test_upload_wrong_tax_year(self, user_and_http):
        _, http = user_and_http
        csv_file = _make_csv_file(SAMPLE_CSV)
        import uuid

        resp = http.post(
            "/api/v1/tb-uploads/upload/",
            data={"tax_year": str(uuid.uuid4()), "file": csv_file},
        )
        assert resp.status_code == 404

    def test_upload_requires_auth(self, tax_year):
        http = TestClient()
        csv_file = _make_csv_file(SAMPLE_CSV)
        resp = http.post(
            "/api/v1/tb-uploads/upload/",
            data={"tax_year": str(tax_year.id), "file": csv_file},
        )
        assert resp.status_code == 403

    def test_upload_creates_audit_entry(self, user_and_http, tax_year):
        _, http = user_and_http
        csv_file = _make_csv_file(SAMPLE_CSV)
        http.post(
            "/api/v1/tb-uploads/upload/",
            data={"tax_year": str(tax_year.id), "file": csv_file},
        )
        from apps.audit.models import AuditEntry

        assert AuditEntry.objects.filter(
            model_name="imports.TrialBalanceUpload"
        ).exists()


# ---------------------------------------------------------------------------
# List / retrieve endpoints
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestListEndpoints:
    def test_list_uploads(self, user_and_http, tax_year):
        _, http = user_and_http
        # Upload a file first
        csv_file = _make_csv_file(SAMPLE_CSV)
        http.post(
            "/api/v1/tb-uploads/upload/",
            data={"tax_year": str(tax_year.id), "file": csv_file},
        )
        resp = http.get("/api/v1/tb-uploads/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_uploads_filter_by_tax_year(self, user_and_http, tax_year):
        _, http = user_and_http
        csv_file = _make_csv_file(SAMPLE_CSV)
        http.post(
            "/api/v1/tb-uploads/upload/",
            data={"tax_year": str(tax_year.id), "file": csv_file},
        )
        resp = http.get(f"/api/v1/tb-uploads/?tax_year={tax_year.id}")
        assert len(resp.json()) == 1

    def test_list_rows(self, user_and_http, tax_year):
        _, http = user_and_http
        csv_file = _make_csv_file(SAMPLE_CSV)
        upload_resp = http.post(
            "/api/v1/tb-uploads/upload/",
            data={"tax_year": str(tax_year.id), "file": csv_file},
        )
        upload_id = upload_resp.json()["id"]
        resp = http.get(f"/api/v1/tb-rows/?upload={upload_id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 3
        # Verify row order
        assert resp.json()[0]["row_number"] == 1
        assert resp.json()[0]["account_number"] == "1000"

    def test_firm_isolation(self, user_and_http, tax_year, firm):
        """Another firm's user can't see our uploads."""
        _, http = user_and_http
        csv_file = _make_csv_file(SAMPLE_CSV)
        http.post(
            "/api/v1/tb-uploads/upload/",
            data={"tax_year": str(tax_year.id), "file": csv_file},
        )

        # Create another user in a different firm
        other_firm = Firm.objects.create(name="Other Firm")
        other_user = User.objects.create_user(username="other", password="testpass123")
        FirmMembership.objects.create(
            user=other_user, firm=other_firm, role=Role.PREPARER
        )
        other_http = TestClient()
        other_http.login(username="other", password="testpass123")

        resp = other_http.get("/api/v1/tb-uploads/")
        assert len(resp.json()) == 0
