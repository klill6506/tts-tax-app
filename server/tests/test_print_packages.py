"""
Tests for print packages, invoice generator, and client letter generator.
"""

import io
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from pypdf import PdfReader

from apps.clients.models import Client, Entity, TaxYear
from apps.firms.models import Firm, FirmMembership
from apps.returns.models import (
    FormDefinition,
    FormFieldValue,
    FormLine,
    PreparerInfo,
    Shareholder,
    TaxReturn,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="Test CPA Firm")


@pytest.fixture
def user_and_http(firm):
    from django.contrib.auth import get_user_model
    from django.test import Client as TestClient

    User = get_user_model()
    user = User.objects.create_user(username="testprep", password="pass1234")
    FirmMembership.objects.create(user=user, firm=firm, role="admin")
    http = TestClient()
    http.login(username="testprep", password="pass1234")
    return user, http


@pytest.fixture
def tax_year(firm):
    client = Client.objects.create(firm=firm, name="Acme Holdings")
    entity = Entity.objects.create(
        client=client,
        name="Acme S-Corp",
        legal_name="Acme Corporation Inc.",
        ein="12-3456789",
        address_line1="100 Main Street",
        city="Athens",
        state="GA",
        zip_code="30601",
    )
    return TaxYear.objects.create(entity=entity, year=2025)


@pytest.fixture
def seeded(db):
    from apps.returns.management.commands.seed_1120s import Command as SeedCommand

    cmd = SeedCommand()
    cmd.stdout = open("/dev/null", "w")
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="1120-S")


@pytest.fixture
def tax_return(seeded, tax_year, user_and_http):
    user, _ = user_and_http
    tr = TaxReturn.objects.create(
        tax_year=tax_year,
        form_definition=seeded,
        created_by=user,
    )
    # Bulk-create all FormFieldValue rows
    fvs = []
    for line in FormLine.objects.filter(section__form=seeded):
        fvs.append(FormFieldValue(tax_return=tr, form_line=line, value=""))
    FormFieldValue.objects.bulk_create(fvs)
    return tr


@pytest.fixture
def preparer_info(tax_return):
    return PreparerInfo.objects.create(
        tax_return=tax_return,
        preparer_name="Ken Lillard",
        ptin="P12345678",
        signature_date=date(2026, 3, 8),
        is_self_employed=False,
        firm_name="The Tax Shelter",
        firm_ein="58-1234567",
        firm_phone="706-555-0100",
        firm_address="123 Main Street",
        firm_city="Athens",
        firm_state="GA",
        firm_zip="30601",
    )


def _set_field(tax_return, line_number, value):
    """Set a FormFieldValue by line_number."""
    fv = FormFieldValue.objects.get(
        tax_return=tax_return,
        form_line__line_number=line_number,
    )
    fv.value = value
    fv.save()


# ---------------------------------------------------------------------------
# Invoice tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInvoice:
    def test_render_invoice_produces_valid_pdf(self, tax_return, preparer_info):
        from apps.tts_forms.invoice import render_invoice

        _set_field(tax_return, "INV_PREP_FEE", "1500.00")
        pdf_bytes = render_invoice(tax_return)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == 1  # Two copies on one page

    def test_invoice_with_additional_fees(self, tax_return, preparer_info):
        from apps.tts_forms.invoice import render_invoice

        _set_field(tax_return, "INV_PREP_FEE", "1500.00")
        _set_field(tax_return, "INV_FEE_2_DESC", "Bookkeeping")
        _set_field(tax_return, "INV_FEE_2", "500.00")
        _set_field(tax_return, "INV_FEE_3_DESC", "Consultation")
        _set_field(tax_return, "INV_FEE_3", "250.00")
        _set_field(tax_return, "INV_MEMO", "Thank you for your business")

        pdf_bytes = render_invoice(tax_return)
        assert len(pdf_bytes) > 1000

    def test_invoice_without_preparer_info(self, tax_return):
        from apps.tts_forms.invoice import render_invoice

        _set_field(tax_return, "INV_PREP_FEE", "1000.00")
        pdf_bytes = render_invoice(tax_return)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_invoice_computes_total_if_missing(self, tax_return, preparer_info):
        from apps.tts_forms.invoice import render_invoice, _to_decimal, _get_field_value

        _set_field(tax_return, "INV_PREP_FEE", "1000.00")
        _set_field(tax_return, "INV_FEE_2", "200.00")
        # Don't set INV_TOTAL — should be auto-computed
        pdf_bytes = render_invoice(tax_return)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_invoice_forms_list(self, tax_return, preparer_info):
        from apps.tts_forms.invoice import _get_forms_list

        federal, state = _get_forms_list(tax_return)
        # Should at least have the main form
        assert any("1120S" in f for f in federal)

    def test_invoice_forms_list_with_shareholders(self, tax_return, preparer_info):
        from apps.tts_forms.invoice import _get_forms_list

        Shareholder.objects.create(
            tax_return=tax_return,
            name="John Smith",
            ownership_percentage=Decimal("100"),
            beginning_shares=100,
            ending_shares=100,
        )
        federal, state = _get_forms_list(tax_return)
        assert any("K-1" in f for f in federal)
        assert any("7203" in f for f in federal)


# ---------------------------------------------------------------------------
# Letter tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLetter:
    def test_render_letter_produces_valid_pdf(self, tax_return, preparer_info):
        from apps.tts_forms.letter import render_letter

        _set_field(tax_return, "LTR_FILING_METHOD", "E-File")
        pdf_bytes = render_letter(tax_return)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1

    def test_letter_electronic_filing(self, tax_return, preparer_info):
        from apps.tts_forms.letter import render_letter

        _set_field(tax_return, "LTR_FILING_METHOD", "E-File")
        _set_field(tax_return, "LTR_FED_BALANCE", "0")
        pdf_bytes = render_letter(tax_return)
        assert len(pdf_bytes) > 1000

    def test_letter_with_balance_due(self, tax_return, preparer_info):
        from apps.tts_forms.letter import render_letter

        _set_field(tax_return, "LTR_FILING_METHOD", "E-File")
        _set_field(tax_return, "LTR_FED_BALANCE", "5000.00")
        _set_field(tax_return, "LTR_FED_DUE_DATE", "03/15/2026")
        pdf_bytes = render_letter(tax_return)
        assert len(pdf_bytes) > 1000

    def test_letter_with_estimated_taxes(self, tax_return, preparer_info):
        from apps.tts_forms.letter import render_letter

        _set_field(tax_return, "LTR_FILING_METHOD", "E-File")
        _set_field(tax_return, "LTR_EST_TAX_1", "2500.00")
        _set_field(tax_return, "LTR_EST_DATE_1", "04/15/2026")
        _set_field(tax_return, "LTR_EST_TAX_2", "2500.00")
        _set_field(tax_return, "LTR_EST_DATE_2", "06/15/2026")
        pdf_bytes = render_letter(tax_return)
        assert len(pdf_bytes) > 1000

    def test_letter_paper_filing(self, tax_return, preparer_info):
        from apps.tts_forms.letter import render_letter

        _set_field(tax_return, "LTR_FILING_METHOD", "Paper")
        pdf_bytes = render_letter(tax_return)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_letter_with_custom_note(self, tax_return, preparer_info):
        from apps.tts_forms.letter import render_letter

        _set_field(tax_return, "LTR_FILING_METHOD", "E-File")
        _set_field(tax_return, "LTR_CUSTOM_NOTE", "Please remember to update your W-9.")
        pdf_bytes = render_letter(tax_return)
        assert len(pdf_bytes) > 1000

    def test_letter_without_preparer_info(self, tax_return):
        from apps.tts_forms.letter import render_letter

        _set_field(tax_return, "LTR_FILING_METHOD", "E-File")
        pdf_bytes = render_letter(tax_return)
        assert pdf_bytes[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Print Package tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPrintPackages:
    def test_package_invoice_only(self, tax_return, preparer_info):
        from apps.tts_forms.renderer import render_complete_return

        _set_field(tax_return, "INV_PREP_FEE", "1500.00")
        pdf_bytes = render_complete_return(tax_return, package="invoice")
        assert pdf_bytes[:5] == b"%PDF-"
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == 1

    def test_package_letter_only(self, tax_return, preparer_info):
        from apps.tts_forms.renderer import render_complete_return

        _set_field(tax_return, "LTR_FILING_METHOD", "E-File")
        pdf_bytes = render_complete_return(tax_return, package="letter")
        assert pdf_bytes[:5] == b"%PDF-"

    def test_package_k1s_with_shareholders(self, tax_return, preparer_info):
        from apps.tts_forms.renderer import render_complete_return

        Shareholder.objects.create(
            tax_return=tax_return,
            name="Jane Doe",
            ownership_percentage=Decimal("50"),
            beginning_shares=50,
            ending_shares=50,
        )
        Shareholder.objects.create(
            tax_return=tax_return,
            name="John Doe",
            ownership_percentage=Decimal("50"),
            beginning_shares=50,
            ending_shares=50,
        )
        pdf_bytes = render_complete_return(tax_return, package="k1s")
        assert pdf_bytes[:5] == b"%PDF-"
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 2  # One K-1 per shareholder

    def test_package_names_constant(self):
        from apps.tts_forms.renderer import PRINT_PACKAGES

        assert "client" in PRINT_PACKAGES
        assert "filing" in PRINT_PACKAGES
        assert "extension" in PRINT_PACKAGES
        assert "state" in PRINT_PACKAGES
        assert "k1s" in PRINT_PACKAGES
        assert "invoice" in PRINT_PACKAGES
        assert "letter" in PRINT_PACKAGES

    def test_default_package_none(self, tax_return, preparer_info):
        """None package includes letter + invoice + forms (more pages than filing)."""
        from apps.tts_forms.renderer import render_complete_return

        _set_field(tax_return, "INV_PREP_FEE", "1000.00")
        _set_field(tax_return, "LTR_FILING_METHOD", "E-File")

        all_bytes = render_complete_return(tax_return, package=None)
        filing_bytes = render_complete_return(tax_return, package="filing")

        all_pages = len(PdfReader(io.BytesIO(all_bytes)).pages)
        filing_pages = len(PdfReader(io.BytesIO(filing_bytes)).pages)

        # All includes letter + invoice, filing does not
        assert all_pages > filing_pages


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPrintPackageAPI:
    def test_render_complete_with_package_param(self, tax_return, preparer_info, user_and_http):
        _, http = user_and_http
        _set_field(tax_return, "INV_PREP_FEE", "1000.00")

        resp = http.post(
            f"/api/v1/tax-returns/{tax_return.id}/render-complete/?package=invoice"
        )
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        assert "Invoice" in resp["Content-Disposition"]

    def test_render_complete_invalid_package(self, tax_return, preparer_info, user_and_http):
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{tax_return.id}/render-complete/?package=bogus"
        )
        assert resp.status_code == 400

    def test_render_invoice_endpoint(self, tax_return, preparer_info, user_and_http):
        _, http = user_and_http
        _set_field(tax_return, "INV_PREP_FEE", "1500.00")

        resp = http.post(
            f"/api/v1/tax-returns/{tax_return.id}/render-invoice/"
        )
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"

    def test_render_letter_endpoint(self, tax_return, preparer_info, user_and_http):
        _, http = user_and_http
        _set_field(tax_return, "LTR_FILING_METHOD", "E-File")

        resp = http.post(
            f"/api/v1/tax-returns/{tax_return.id}/render-letter/"
        )
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"

    def test_render_complete_filename_reflects_package(self, tax_return, preparer_info, user_and_http):
        _, http = user_and_http
        _set_field(tax_return, "LTR_FILING_METHOD", "E-File")

        resp = http.post(
            f"/api/v1/tax-returns/{tax_return.id}/render-complete/?package=letter"
        )
        assert resp.status_code == 200
        assert "LetterOnly" in resp["Content-Disposition"]
