"""
Tests for the IRS Form PDF rendering subsystem (apps.tts_forms).

Tests cover:
    - Statement page generation (standalone, no IRS template needed)
    - Overlay creation (creates transparent overlay pages)
    - Renderer integration (requires a test PDF template)
    - Coordinate registry structure
    - Manifest loading
    - render_tax_return endpoint
"""

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import Client as TestClient
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from apps.clients.models import Client, Entity, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.management.commands.seed_1120s import Command as SeedCommand
from apps.returns.models import FormDefinition, FormFieldValue, TaxReturn
from apps.tts_forms.coordinates.f1120s import (
    FIELD_MAP,
    HEADER_FIELDS,
    FieldCoord,
)
from apps.tts_forms.renderer import (
    COORDINATE_REGISTRY,
    _create_overlay,
    _format_currency,
    _format_value,
    render,
)
from apps.tts_forms.statements import render_statement_pages


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_blank_pdf(pages: int = 6) -> bytes:
    """Create a blank multi-page PDF for use as a test template."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for i in range(pages):
        c.drawString(72, 720, f"Test Page {i + 1}")
        c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def firm(db):
    return Firm.objects.create(name="PDF Test Firm")


@pytest.fixture
def user_and_http(firm):
    user = User.objects.create_user(username="pdfpreparer", password="testpass123")
    FirmMembership.objects.create(user=user, firm=firm, role=Role.PREPARER)
    http = TestClient()
    http.login(username="pdfpreparer", password="testpass123")
    return user, http


@pytest.fixture
def tax_year(firm):
    client = Client.objects.create(firm=firm, name="PDF Test Client")
    entity = Entity.objects.create(client=client, name="PDF Test S-Corp")
    return TaxYear.objects.create(entity=entity, year=2025)


@pytest.fixture
def seeded(db):
    """Seed 1120-S form definition."""
    cmd = SeedCommand()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="1120-S")


@pytest.fixture
def tax_return_with_data(seeded, tax_year, user_and_http):
    """Create a tax return with some field values populated."""
    user, _ = user_and_http
    tr = TaxReturn.objects.create(
        tax_year=tax_year,
        form_definition=seeded,
        created_by=user,
    )
    from apps.returns.models import FormLine

    lines = FormLine.objects.filter(section__form=seeded)
    fvs = []
    for line in lines:
        fvs.append(FormFieldValue(tax_return=tr, form_line=line, value=""))
    FormFieldValue.objects.bulk_create(fvs)

    # Set some values
    test_values = {
        "1a": "500000.00",
        "1b": "5000.00",
        "7": "120000.00",
        "8": "80000.00",
        "19": "25000.00",
    }
    for line_num, val in test_values.items():
        fv = FormFieldValue.objects.get(
            tax_return=tr,
            form_line__line_number=line_num,
        )
        fv.value = val
        fv.save()

    return tr


@pytest.fixture
def test_template_pdf(tmp_path):
    """Write a blank test PDF to use as a template."""
    pdf_bytes = _make_blank_pdf(pages=6)
    pdf_path = tmp_path / "f1120s.pdf"
    pdf_path.write_bytes(pdf_bytes)
    return pdf_path


# ---------------------------------------------------------------------------
# Statement page tests
# ---------------------------------------------------------------------------


class TestStatements:
    def test_render_empty_returns_none(self):
        result = render_statement_pages([])
        assert result is None

    def test_render_single_statement(self):
        pages = [
            {
                "title": "Form 1120-S (2025) — Statement for Line 19",
                "subtitle": "Other deductions",
                "form_code": "1120-S",
                "items": [
                    {"description": "Office supplies", "amount": "1234.00"},
                    {"description": "Professional fees", "amount": "5678.00"},
                ],
            }
        ]
        pdf_bytes = render_statement_pages(pages)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0

        # Verify it's a valid PDF
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == 1

    def test_render_multiple_statements(self):
        pages = [
            {
                "title": "Statement for Line 19",
                "items": [
                    {"description": "Item A", "amount": "100.00"},
                ],
            },
            {
                "title": "Statement for Line 5",
                "items": [
                    {"description": "Item B", "amount": "200.00"},
                ],
            },
        ]
        pdf_bytes = render_statement_pages(pages)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == 2

    def test_statement_with_many_items_paginates(self):
        """A statement with enough items should overflow to a second page."""
        items = [
            {"description": f"Line item {i}", "amount": f"{i * 10}.00"}
            for i in range(80)
        ]
        pages = [{"title": "Long statement", "items": items}]
        pdf_bytes = render_statement_pages(pages)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 2

    def test_statement_with_negative_amounts(self):
        pages = [
            {
                "title": "Statement",
                "items": [
                    {"description": "Loss item", "amount": "-500.00"},
                    {"description": "Gain item", "amount": "1000.00"},
                ],
            }
        ]
        pdf_bytes = render_statement_pages(pages)
        assert pdf_bytes is not None
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == 1


# ---------------------------------------------------------------------------
# Formatting tests
# ---------------------------------------------------------------------------


class TestFormatting:
    def test_format_currency_positive(self):
        assert _format_currency("1234.56") == "1,235"

    def test_format_currency_negative(self):
        assert _format_currency("-1234.56") == "(1,235)"

    def test_format_currency_zero(self):
        assert _format_currency("0.00") == ""

    def test_format_currency_empty(self):
        assert _format_currency("") == ""

    def test_format_currency_none(self):
        assert _format_currency(None) == ""

    def test_format_value_boolean_true(self):
        assert _format_value("true", "boolean") == "X"
        assert _format_value("yes", "boolean") == "X"
        assert _format_value("1", "boolean") == "X"

    def test_format_value_boolean_false(self):
        assert _format_value("false", "boolean") == ""
        assert _format_value("no", "boolean") == ""

    def test_format_value_percentage(self):
        assert _format_value("12.5", "percentage") == "12.5%"

    def test_format_value_text(self):
        assert _format_value("United States", "text") == "United States"


# ---------------------------------------------------------------------------
# Overlay creation tests
# ---------------------------------------------------------------------------


class TestOverlay:
    def test_create_overlay_generates_pdf(self):
        field_values = {
            "1a": ("500000", "currency"),
            "7": ("120000", "currency"),
        }
        overlay_buf = _create_overlay(
            field_values=field_values,
            field_map=FIELD_MAP,
            header_data={"entity_name": "Test Corp"},
            header_map=HEADER_FIELDS,
            page_count=6,
        )
        assert overlay_buf is not None
        reader = PdfReader(overlay_buf)
        assert len(reader.pages) == 6

    def test_create_overlay_empty_values(self):
        overlay_buf = _create_overlay(
            field_values={},
            field_map=FIELD_MAP,
            header_data=None,
            header_map=None,
            page_count=1,
        )
        reader = PdfReader(overlay_buf)
        assert len(reader.pages) == 1


# ---------------------------------------------------------------------------
# Coordinate registry tests
# ---------------------------------------------------------------------------


class TestCoordinates:
    def test_f1120s_field_map_has_entries(self):
        assert len(FIELD_MAP) > 0

    def test_all_coords_are_field_coord(self):
        for key, coord in FIELD_MAP.items():
            assert isinstance(coord, FieldCoord), f"{key} is not a FieldCoord"

    def test_all_pages_are_valid(self):
        for key, coord in FIELD_MAP.items():
            assert 0 <= coord.page <= 5, f"{key} has invalid page {coord.page}"

    def test_all_positions_are_positive(self):
        for key, coord in FIELD_MAP.items():
            assert coord.x >= 0, f"{key} has negative x"
            assert coord.y >= 0, f"{key} has negative y"
            assert coord.width > 0, f"{key} has non-positive width"

    def test_all_alignments_are_valid(self):
        valid = {"left", "right", "center"}
        for key, coord in FIELD_MAP.items():
            assert coord.alignment in valid, f"{key} has invalid alignment"

    def test_coordinate_registry_contains_f1120s(self):
        assert "f1120s" in COORDINATE_REGISTRY

    def test_header_fields_exist(self):
        assert "entity_name" in HEADER_FIELDS
        assert "ein" in HEADER_FIELDS

    def test_income_lines_mapped(self):
        for ln in ["1a", "1b", "1c", "2", "3", "6"]:
            assert ln in FIELD_MAP, f"Income line {ln} missing from FIELD_MAP"

    def test_deduction_lines_mapped(self):
        for ln in ["7", "8", "19", "20", "21"]:
            assert ln in FIELD_MAP, f"Deduction line {ln} missing from FIELD_MAP"


# ---------------------------------------------------------------------------
# Full renderer tests (using a mock template PDF)
# ---------------------------------------------------------------------------


class TestRenderer:
    def test_render_produces_valid_pdf(self, test_template_pdf):
        """Render with a test template and verify the output is a valid PDF."""
        field_values = {
            "1a": ("500000", "currency"),
            "7": ("120000", "currency"),
            "19": ("25000", "currency"),
        }

        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render(
                form_id="f1120s",
                tax_year=2025,
                field_values=field_values,
                header_data={"entity_name": "Test Corp", "ein": "12-3456789"},
            )

        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        # Should have same page count as template
        assert len(reader.pages) == 6

    def test_render_with_statements(self, test_template_pdf):
        """Render with attached statement pages."""
        field_values = {"19": ("25000", "currency")}
        statements = [
            {
                "title": "Form 1120-S (2025) — Statement for Line 19",
                "subtitle": "Other deductions",
                "form_code": "1120-S",
                "items": [
                    {"description": "Office supplies", "amount": "5000"},
                    {"description": "Legal fees", "amount": "20000"},
                ],
            }
        ]

        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render(
                form_id="f1120s",
                tax_year=2025,
                field_values=field_values,
                statement_pages=statements,
            )

        reader = PdfReader(io.BytesIO(pdf_bytes))
        # 6 template pages + 1 statement page
        assert len(reader.pages) == 7

    def test_render_unknown_form_raises(self):
        with pytest.raises(ValueError, match="No coordinate map"):
            render(
                form_id="f9999",
                tax_year=2025,
                field_values={},
            )

    def test_render_missing_template_raises(self):
        with pytest.raises(FileNotFoundError, match="IRS PDF template not found"):
            render(
                form_id="f1120s",
                tax_year=2025,
                field_values={},
            )


# ---------------------------------------------------------------------------
# render_tax_return integration tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRenderTaxReturn:
    def test_render_tax_return_produces_pdf(
        self, tax_return_with_data, test_template_pdf
    ):
        from apps.tts_forms.renderer import render_tax_return

        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render_tax_return(tax_return_with_data)

        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == 6

    def test_render_tax_return_with_statements(
        self, tax_return_with_data, test_template_pdf
    ):
        from apps.tts_forms.renderer import render_tax_return

        statements = {
            "19": [
                {"description": "Office supplies", "amount": "10000"},
                {"description": "Insurance", "amount": "15000"},
            ],
        }

        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render_tax_return(
                tax_return_with_data, statement_items=statements
            )

        reader = PdfReader(io.BytesIO(pdf_bytes))
        # 6 template + 1 statement
        assert len(reader.pages) == 7


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPDFEndpoint:
    def test_render_pdf_endpoint(
        self, user_and_http, tax_return_with_data, test_template_pdf
    ):
        _, http = user_and_http

        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            resp = http.post(
                f"/api/v1/tax-returns/{tax_return_with_data.id}/render-pdf/",
                content_type="application/json",
            )

        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        assert "Content-Disposition" in resp
        assert ".pdf" in resp["Content-Disposition"]

        # Verify it's a valid PDF
        reader = PdfReader(io.BytesIO(resp.content))
        assert len(reader.pages) == 6

    def test_render_pdf_with_statements_body(
        self, user_and_http, tax_return_with_data, test_template_pdf
    ):
        _, http = user_and_http
        body = {
            "statements": {
                "19": [
                    {"description": "Supplies", "amount": "5000"},
                ],
            },
        }

        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            resp = http.post(
                f"/api/v1/tax-returns/{tax_return_with_data.id}/render-pdf/",
                data=json.dumps(body),
                content_type="application/json",
            )

        assert resp.status_code == 200
        reader = PdfReader(io.BytesIO(resp.content))
        assert len(reader.pages) == 7

    def test_render_pdf_missing_template_returns_404(
        self, user_and_http, tax_return_with_data
    ):
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{tax_return_with_data.id}/render-pdf/",
            content_type="application/json",
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------


class TestManifest:
    def test_manifest_file_exists(self):
        manifest_path = (
            Path(__file__).resolve().parent.parent.parent
            / "resources"
            / "irs_forms"
            / "forms_manifest.json"
        )
        assert manifest_path.exists(), "forms_manifest.json should exist"

    def test_manifest_is_valid_json(self):
        manifest_path = (
            Path(__file__).resolve().parent.parent.parent
            / "resources"
            / "irs_forms"
            / "forms_manifest.json"
        )
        with open(manifest_path) as f:
            data = json.load(f)
        assert "forms" in data
        assert len(data["forms"]) > 0

    def test_manifest_entries_have_required_fields(self):
        manifest_path = (
            Path(__file__).resolve().parent.parent.parent
            / "resources"
            / "irs_forms"
            / "forms_manifest.json"
        )
        with open(manifest_path) as f:
            data = json.load(f)

        required = {"form_id", "form_code", "title", "tax_year", "irs_url", "local_path"}
        for entry in data["forms"]:
            missing = required - set(entry.keys())
            assert not missing, f"Entry {entry.get('form_id')} missing fields: {missing}"
