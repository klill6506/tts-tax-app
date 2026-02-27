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
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import Client as TestClient
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from decimal import Decimal

from apps.clients.models import Client, Entity, TaxYear
from apps.firms.models import Firm, FirmMembership, Role
from apps.returns.management.commands.seed_1120s import Command as SeedCommand
from apps.returns.models import (
    FormDefinition,
    FormFieldValue,
    FormLine,
    RentalProperty,
    Shareholder,
    TaxReturn,
)
from apps.tts_forms.coordinates.f1065 import FIELD_MAP as F1065_FIELD_MAP
from apps.tts_forms.coordinates.f1065 import HEADER_FIELDS as F1065_HEADER_FIELDS
from apps.tts_forms.coordinates.f1120 import FIELD_MAP as F1120_FIELD_MAP
from apps.tts_forms.coordinates.f1120 import HEADER_FIELDS as F1120_HEADER_FIELDS
from apps.tts_forms.coordinates.f1120s import (
    FIELD_MAP,
    HEADER_FIELDS,
    FieldCoord,
)
from apps.tts_forms.coordinates.f1120sk1 import (
    K1_FIELD_MAP,
    K1_HEADER,
)
from apps.tts_forms.coordinates.f7206 import (
    FIELD_MAP as F7206_FIELD_MAP,
    HEADER_FIELDS as F7206_HEADER_FIELDS,
)
from apps.tts_forms.coordinates.f1125a import (
    FIELD_MAP as F1125A_FIELD_MAP,
    HEADER_FIELDS as F1125A_HEADER_FIELDS,
)
from apps.tts_forms.coordinates.f7203 import (
    FIELD_MAP as F7203_FIELD_MAP,
    HEADER_FIELDS as F7203_HEADER_FIELDS,
)
from apps.tts_forms.coordinates.f8825 import (
    FIELD_MAP as F8825_FIELD_MAP,
    HEADER_FIELDS as F8825_HEADER_FIELDS,
    PROPERTY_FIELDS as F8825_PROPERTY_FIELDS,
)
from apps.tts_forms.renderer import (
    COORDINATE_REGISTRY,
    HEADER_REGISTRY,
    SCHED_K_TO_K1_MAP,
    _create_overlay,
    _format_currency,
    _format_value,
    render,
    render_1125a,
    render_7203,
    render_7206,
    render_8825,
    render_all_7203s,
    render_all_k1s,
    render_k1,
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

    def test_preparer_fields_mapped(self):
        preparer_keys = [
            "preparer_name", "preparer_date", "preparer_ptin",
            "preparer_self_employed", "firm_name", "firm_ein",
            "firm_address", "firm_phone",
        ]
        for key in preparer_keys:
            assert key in HEADER_FIELDS, f"1120-S: preparer field {key} missing"

    def test_income_lines_mapped(self):
        for ln in ["1a", "1b", "1c", "2", "3", "6"]:
            assert ln in FIELD_MAP, f"Income line {ln} missing from FIELD_MAP"

    def test_deduction_lines_mapped(self):
        for ln in ["7", "8", "19", "20", "21"]:
            assert ln in FIELD_MAP, f"Deduction line {ln} missing from FIELD_MAP"


# ---------------------------------------------------------------------------
# Form 1065 coordinate tests
# ---------------------------------------------------------------------------


class TestCoordinates1065:
    def test_f1065_field_map_has_entries(self):
        assert len(F1065_FIELD_MAP) > 0

    def test_coordinate_registry_contains_f1065(self):
        assert "f1065" in COORDINATE_REGISTRY

    def test_header_registry_contains_f1065(self):
        assert "f1065" in HEADER_REGISTRY

    def test_all_coords_are_field_coord(self):
        for key, coord in F1065_FIELD_MAP.items():
            assert isinstance(coord, FieldCoord), f"1065: {key} is not a FieldCoord"

    def test_all_pages_are_valid(self):
        for key, coord in F1065_FIELD_MAP.items():
            assert 0 <= coord.page <= 6, f"1065: {key} has invalid page {coord.page}"

    def test_all_positions_are_positive(self):
        for key, coord in F1065_FIELD_MAP.items():
            assert coord.x >= 0, f"1065: {key} has negative x"
            assert coord.y >= 0, f"1065: {key} has negative y"
            assert coord.width > 0, f"1065: {key} has non-positive width"

    def test_all_alignments_are_valid(self):
        valid = {"left", "right", "center"}
        for key, coord in F1065_FIELD_MAP.items():
            assert coord.alignment in valid, f"1065: {key} has invalid alignment"

    def test_header_fields_exist(self):
        assert "entity_name" in F1065_HEADER_FIELDS
        assert "ein" in F1065_HEADER_FIELDS

    def test_income_lines_mapped(self):
        for ln in ["1a", "1b", "1c", "2", "3", "8"]:
            assert ln in F1065_FIELD_MAP, f"1065 income line {ln} missing"

    def test_deduction_lines_mapped(self):
        for ln in ["9", "10", "20", "21", "22"]:
            assert ln in F1065_FIELD_MAP, f"1065 deduction line {ln} missing"

    def test_schedule_k_lines_mapped(self):
        for ln in ["K1", "K2", "K4", "K5", "K12"]:
            assert ln in F1065_FIELD_MAP, f"1065 Schedule K line {ln} missing"

    def test_schedule_l_lines_mapped(self):
        for ln in ["L1b", "L1d", "L14b", "L14d"]:
            assert ln in F1065_FIELD_MAP, f"1065 Schedule L line {ln} missing"

    def test_schedule_m1_lines_mapped(self):
        for ln in ["M1_1", "M1_9"]:
            assert ln in F1065_FIELD_MAP, f"1065 Schedule M-1 line {ln} missing"

    def test_schedule_m2_lines_mapped(self):
        for ln in ["M2_1", "M2_9"]:
            assert ln in F1065_FIELD_MAP, f"1065 Schedule M-2 line {ln} missing"

    def test_preparer_fields_mapped(self):
        preparer_keys = [
            "preparer_name", "preparer_date", "preparer_ptin",
            "preparer_self_employed", "firm_name", "firm_ein",
            "firm_address", "firm_phone",
        ]
        for key in preparer_keys:
            assert key in F1065_HEADER_FIELDS, f"1065: preparer field {key} missing"


# ---------------------------------------------------------------------------
# Form 1120 coordinate tests
# ---------------------------------------------------------------------------


class TestCoordinates1120:
    def test_f1120_field_map_has_entries(self):
        assert len(F1120_FIELD_MAP) > 0

    def test_coordinate_registry_contains_f1120(self):
        assert "f1120" in COORDINATE_REGISTRY

    def test_header_registry_contains_f1120(self):
        assert "f1120" in HEADER_REGISTRY

    def test_all_coords_are_field_coord(self):
        for key, coord in F1120_FIELD_MAP.items():
            assert isinstance(coord, FieldCoord), f"1120: {key} is not a FieldCoord"

    def test_all_pages_are_valid(self):
        for key, coord in F1120_FIELD_MAP.items():
            assert 0 <= coord.page <= 5, f"1120: {key} has invalid page {coord.page}"

    def test_all_positions_are_positive(self):
        for key, coord in F1120_FIELD_MAP.items():
            assert coord.x >= 0, f"1120: {key} has negative x"
            assert coord.y >= 0, f"1120: {key} has negative y"
            assert coord.width > 0, f"1120: {key} has non-positive width"

    def test_all_alignments_are_valid(self):
        valid = {"left", "right", "center"}
        for key, coord in F1120_FIELD_MAP.items():
            assert coord.alignment in valid, f"1120: {key} has invalid alignment"

    def test_header_fields_exist(self):
        assert "entity_name" in F1120_HEADER_FIELDS
        assert "ein" in F1120_HEADER_FIELDS

    def test_income_lines_mapped(self):
        for ln in ["1a", "1b", "1c", "2", "3", "11"]:
            assert ln in F1120_FIELD_MAP, f"1120 income line {ln} missing"

    def test_deduction_lines_mapped(self):
        for ln in ["12", "13", "26", "27", "28", "30"]:
            assert ln in F1120_FIELD_MAP, f"1120 deduction line {ln} missing"

    def test_tax_lines_mapped(self):
        for ln in ["31", "32", "34", "36"]:
            assert ln in F1120_FIELD_MAP, f"1120 tax line {ln} missing"

    def test_schedule_c_lines_mapped(self):
        for ln in ["C1a", "C1c", "C19", "C20"]:
            assert ln in F1120_FIELD_MAP, f"1120 Schedule C line {ln} missing"

    def test_schedule_j_lines_mapped(self):
        for ln in ["J1", "J2", "J10"]:
            assert ln in F1120_FIELD_MAP, f"1120 Schedule J line {ln} missing"

    def test_schedule_l_lines_mapped(self):
        for ln in ["L1b", "L1d", "L15b", "L15d", "L28b", "L28d"]:
            assert ln in F1120_FIELD_MAP, f"1120 Schedule L line {ln} missing"

    def test_schedule_m1_lines_mapped(self):
        for ln in ["M1_1", "M1_10"]:
            assert ln in F1120_FIELD_MAP, f"1120 Schedule M-1 line {ln} missing"

    def test_schedule_m2_lines_mapped(self):
        for ln in ["M2_1", "M2_8"]:
            assert ln in F1120_FIELD_MAP, f"1120 Schedule M-2 line {ln} missing"

    def test_preparer_fields_mapped(self):
        preparer_keys = [
            "preparer_name", "preparer_date", "preparer_ptin",
            "preparer_self_employed", "firm_name", "firm_ein",
            "firm_address", "firm_phone",
        ]
        for key in preparer_keys:
            assert key in F1120_HEADER_FIELDS, f"1120: preparer field {key} missing"


# ---------------------------------------------------------------------------
# Cross-form renderer tests (1065 and 1120 rendering)
# ---------------------------------------------------------------------------


class TestRender1065:
    def test_render_1065_produces_valid_pdf(self, test_template_pdf):
        field_values = {
            "1a": ("750000", "currency"),
            "9": ("50000", "currency"),
            "22": ("200000", "currency"),
        }
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render(
                form_id="f1065",
                tax_year=2025,
                field_values=field_values,
                header_data={"entity_name": "Test Partnership LLC", "ein": "98-7654321"},
            )
        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == 6

    def test_render_1065_with_statements(self, test_template_pdf):
        field_values = {"20": ("15000", "currency")}
        statements = [
            {
                "title": "Form 1065 (2025) — Statement for Line 20",
                "subtitle": "Other deductions",
                "form_code": "1065",
                "items": [
                    {"description": "Office rent", "amount": "8000"},
                    {"description": "Utilities", "amount": "7000"},
                ],
            }
        ]
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render(
                form_id="f1065",
                tax_year=2025,
                field_values=field_values,
                statement_pages=statements,
            )
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == 7


class TestRender1120:
    def test_render_1120_produces_valid_pdf(self, test_template_pdf):
        field_values = {
            "1a": ("1000000", "currency"),
            "12": ("200000", "currency"),
            "30": ("300000", "currency"),
            "31": ("100000", "currency"),
        }
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render(
                form_id="f1120",
                tax_year=2025,
                field_values=field_values,
                header_data={"entity_name": "Test Corp Inc", "ein": "55-1234567"},
            )
        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == 6

    def test_render_1120_with_statements(self, test_template_pdf):
        field_values = {"26": ("45000", "currency")}
        statements = [
            {
                "title": "Form 1120 (2025) — Statement for Line 26",
                "subtitle": "Other deductions",
                "form_code": "1120",
                "items": [
                    {"description": "Professional services", "amount": "25000"},
                    {"description": "Office expenses", "amount": "20000"},
                ],
            }
        ]
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render(
                form_id="f1120",
                tax_year=2025,
                field_values=field_values,
                statement_pages=statements,
            )
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) == 7


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
        with pytest.raises(FileNotFoundError):
            render(
                form_id="f1120s",
                tax_year=9999,
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
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            side_effect=FileNotFoundError("IRS PDF template not found"),
        ):
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
        assert len(data["forms"]) == 12  # 9 form templates + 3 instruction PDFs

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


# ---------------------------------------------------------------------------
# K-1 coordinate tests
# ---------------------------------------------------------------------------


class TestCoordinatesK1:
    def test_k1_header_has_entries(self):
        assert len(K1_HEADER) > 0

    def test_k1_field_map_has_entries(self):
        assert len(K1_FIELD_MAP) > 0

    def test_coordinate_registry_contains_k1(self):
        assert "f1120sk1" in COORDINATE_REGISTRY

    def test_header_registry_contains_k1(self):
        assert "f1120sk1" in HEADER_REGISTRY

    def test_all_k1_coords_are_field_coord(self):
        for key, coord in K1_FIELD_MAP.items():
            assert isinstance(coord, FieldCoord), f"K-1: {key} is not a FieldCoord"

    def test_all_k1_header_coords_are_field_coord(self):
        for key, coord in K1_HEADER.items():
            assert isinstance(coord, FieldCoord), f"K-1 header: {key} is not a FieldCoord"

    def test_k1_header_has_required_fields(self):
        required = ["corp_ein", "corp_name", "sh_ssn", "sh_name", "sh_ownership_pct"]
        for field in required:
            assert field in K1_HEADER, f"K-1 header missing {field}"

    def test_k1_income_lines_mapped(self):
        for ln in ["1", "2", "3", "4", "5a", "5b", "6", "7", "8a", "9"]:
            assert ln in K1_FIELD_MAP, f"K-1 income line {ln} missing"

    def test_k1_line_16_sub_items(self):
        for code_key in ["16_code_1", "16_code_2", "16_code_3", "16_code_4"]:
            assert code_key in K1_FIELD_MAP, f"K-1 {code_key} missing"
        for amt_key in ["16_amt_1", "16_amt_2", "16_amt_3", "16_amt_4"]:
            assert amt_key in K1_FIELD_MAP, f"K-1 {amt_key} missing"

    def test_k1_line_17_sub_items(self):
        assert "17_code_1" in K1_FIELD_MAP
        assert "17_amt_1" in K1_FIELD_MAP

    def test_sched_k_to_k1_map_has_entries(self):
        assert len(SCHED_K_TO_K1_MAP) > 0
        assert SCHED_K_TO_K1_MAP["K1"] == "1"
        assert SCHED_K_TO_K1_MAP["K4"] == "4"


# ---------------------------------------------------------------------------
# Form 7206 coordinate tests
# ---------------------------------------------------------------------------


class TestCoordinates7206:
    def test_f7206_field_map_has_entries(self):
        assert len(F7206_FIELD_MAP) > 0

    def test_coordinate_registry_contains_f7206(self):
        assert "f7206" in COORDINATE_REGISTRY

    def test_header_registry_contains_f7206(self):
        assert "f7206" in HEADER_REGISTRY

    def test_all_coords_are_field_coord(self):
        for key, coord in F7206_FIELD_MAP.items():
            assert isinstance(coord, FieldCoord), f"7206: {key} is not a FieldCoord"

    def test_header_has_required_fields(self):
        assert "taxpayer_name" in F7206_HEADER_FIELDS
        assert "taxpayer_ssn" in F7206_HEADER_FIELDS

    def test_line_1_and_3_mapped(self):
        assert "1" in F7206_FIELD_MAP
        assert "3" in F7206_FIELD_MAP


# ---------------------------------------------------------------------------
# K-1 rendering tests
# ---------------------------------------------------------------------------


@pytest.fixture
def tax_return_with_k_data(seeded, tax_year, user_and_http):
    """Create a tax return with Schedule K values populated."""
    user, _ = user_and_http
    tr = TaxReturn.objects.create(
        tax_year=tax_year,
        form_definition=seeded,
        created_by=user,
    )
    lines = FormLine.objects.filter(section__form=seeded)
    fvs = []
    for line in lines:
        fvs.append(FormFieldValue(tax_return=tr, form_line=line, value=""))
    FormFieldValue.objects.bulk_create(fvs)

    # Set Schedule K values
    k_values = {
        "K1": "100000.00",   # Ordinary business income
        "K2": "20000.00",    # Net rental real estate
        "K4": "5000.00",     # Interest income
        "K5a": "3000.00",    # Ordinary dividends
        "K16d": "10000.00",  # Distributions (total)
    }
    for line_num, val in k_values.items():
        fv = FormFieldValue.objects.get(
            tax_return=tr,
            form_line__line_number=line_num,
        )
        fv.value = val
        fv.save()

    return tr


@pytest.fixture
def shareholder_alice(tax_return_with_k_data):
    """Create a 60% shareholder on the test return."""
    return Shareholder.objects.create(
        tax_return=tax_return_with_k_data,
        name="Alice Johnson",
        ssn="111-22-3333",
        ownership_percentage=Decimal("60.0000"),
        beginning_shares=600,
        ending_shares=600,
        city="Dallas",
        state="TX",
        zip_code="75001",
        distributions=Decimal("6000.00"),
        health_insurance_premium=Decimal("1800.00"),
    )


@pytest.fixture
def shareholder_bob(tax_return_with_k_data):
    """Create a 40% shareholder on the test return."""
    return Shareholder.objects.create(
        tax_return=tax_return_with_k_data,
        name="Bob Smith",
        ssn="444-55-6666",
        ownership_percentage=Decimal("40.0000"),
        beginning_shares=400,
        ending_shares=400,
        city="Austin",
        state="TX",
        zip_code="73301",
        distributions=Decimal("4000.00"),
    )


@pytest.mark.django_db
class TestRenderK1:
    def test_render_k1_produces_valid_pdf(
        self, tax_return_with_k_data, shareholder_alice, test_template_pdf
    ):
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render_k1(tax_return_with_k_data, shareholder_alice)

        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1

    def test_render_all_k1s_concatenates(
        self, tax_return_with_k_data, shareholder_alice, shareholder_bob, test_template_pdf
    ):
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render_all_k1s(tax_return_with_k_data)

        reader = PdfReader(io.BytesIO(pdf_bytes))
        # Should have pages from both K-1s (at least 2, one per shareholder)
        assert len(reader.pages) >= 2

    def test_render_all_k1s_raises_if_no_shareholders(
        self, tax_return_with_k_data, test_template_pdf
    ):
        """render_all_k1s should raise ValueError if no active shareholders."""
        with pytest.raises(ValueError, match="No active shareholders"):
            render_all_k1s(tax_return_with_k_data)


@pytest.mark.django_db
class TestRender7206:
    def test_render_7206_produces_valid_pdf(
        self, tax_return_with_k_data, shareholder_alice, test_template_pdf
    ):
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render_7206(tax_return_with_k_data, shareholder_alice)

        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1


# ---------------------------------------------------------------------------
# K-1 and 7206 API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestK1Endpoint:
    def test_render_k1s_endpoint(
        self, user_and_http, tax_return_with_k_data, shareholder_alice, test_template_pdf
    ):
        _, http = user_and_http
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            resp = http.post(
                f"/api/v1/tax-returns/{tax_return_with_k_data.id}/render-k1s/",
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        reader = PdfReader(io.BytesIO(resp.content))
        assert len(reader.pages) >= 1

    def test_render_k1_single_endpoint(
        self, user_and_http, tax_return_with_k_data, shareholder_alice, test_template_pdf
    ):
        _, http = user_and_http
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            resp = http.post(
                f"/api/v1/tax-returns/{tax_return_with_k_data.id}/render-k1/{shareholder_alice.id}/",
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"

    def test_render_k1_single_404_for_wrong_shareholder(
        self, user_and_http, tax_return_with_k_data
    ):
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{tax_return_with_k_data.id}/render-k1/{uuid.uuid4()}/",
            content_type="application/json",
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestForm7206Endpoint:
    def test_render_7206_endpoint(
        self, user_and_http, tax_return_with_k_data, shareholder_alice, test_template_pdf
    ):
        _, http = user_and_http
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            resp = http.post(
                f"/api/v1/tax-returns/{tax_return_with_k_data.id}/render-7206/{shareholder_alice.id}/",
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"

    def test_render_7206_no_premium_returns_400(
        self, user_and_http, tax_return_with_k_data, shareholder_bob, test_template_pdf
    ):
        """Shareholder with no health insurance premium should get 400."""
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{tax_return_with_k_data.id}/render-7206/{shareholder_bob.id}/",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_render_7206_404_for_wrong_shareholder(
        self, user_and_http, tax_return_with_k_data
    ):
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{tax_return_with_k_data.id}/render-7206/{uuid.uuid4()}/",
            content_type="application/json",
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Form 1125-A coordinate tests
# ---------------------------------------------------------------------------


class TestCoordinates1125A:
    def test_f1125a_field_map_has_entries(self):
        assert len(F1125A_FIELD_MAP) > 0

    def test_coordinate_registry_contains_f1125a(self):
        assert "f1125a" in COORDINATE_REGISTRY

    def test_header_registry_contains_f1125a(self):
        assert "f1125a" in HEADER_REGISTRY

    def test_all_coords_are_field_coord(self):
        for key, coord in F1125A_FIELD_MAP.items():
            assert isinstance(coord, FieldCoord), f"1125-A: {key} is not a FieldCoord"

    def test_all_pages_are_valid(self):
        for key, coord in F1125A_FIELD_MAP.items():
            assert coord.page == 0, f"1125-A: {key} should be on page 0"

    def test_all_positions_are_positive(self):
        for key, coord in F1125A_FIELD_MAP.items():
            assert coord.x >= 0, f"1125-A: {key} has negative x"
            assert coord.y >= 0, f"1125-A: {key} has negative y"
            assert coord.width > 0, f"1125-A: {key} has non-positive width"

    def test_header_fields_exist(self):
        assert "entity_name" in F1125A_HEADER_FIELDS
        assert "ein" in F1125A_HEADER_FIELDS

    def test_cogs_lines_mapped(self):
        for ln in ["1", "2", "3", "4", "5", "6", "7", "8"]:
            assert ln in F1125A_FIELD_MAP, f"1125-A line {ln} missing"

    def test_checkbox_fields_exist(self):
        assert "9a_cost" in F1125A_FIELD_MAP
        assert "9a_lcm" in F1125A_FIELD_MAP
        assert "9a_other" in F1125A_FIELD_MAP


class TestRender1125A:
    def test_render_1125a_produces_valid_pdf(self, test_template_pdf):
        field_values = {
            "1": ("50000", "currency"),
            "2": ("200000", "currency"),
            "3": ("80000", "currency"),
            "6": ("330000", "currency"),
            "7": ("60000", "currency"),
            "8": ("270000", "currency"),
        }
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render(
                form_id="f1125a",
                tax_year=2025,
                field_values=field_values,
                header_data={"entity_name": "Test Mfg Corp", "ein": "99-1234567"},
            )
        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1


# ---------------------------------------------------------------------------
# Form 8825 coordinate tests
# ---------------------------------------------------------------------------


class TestCoordinates8825:
    def test_f8825_field_map_has_entries(self):
        assert len(F8825_FIELD_MAP) > 0

    def test_coordinate_registry_contains_f8825(self):
        assert "f8825" in COORDINATE_REGISTRY

    def test_header_registry_contains_f8825(self):
        assert "f8825" in HEADER_REGISTRY

    def test_all_coords_are_field_coord(self):
        for key, coord in F8825_FIELD_MAP.items():
            assert isinstance(coord, FieldCoord), f"8825: {key} is not a FieldCoord"

    def test_all_pages_are_valid(self):
        for key, coord in F8825_FIELD_MAP.items():
            assert 0 <= coord.page <= 1, f"8825: {key} has invalid page {coord.page}"

    def test_all_positions_are_positive(self):
        for key, coord in F8825_FIELD_MAP.items():
            assert coord.x >= 0, f"8825: {key} has negative x"
            assert coord.y >= 0, f"8825: {key} has negative y"
            assert coord.width > 0, f"8825: {key} has non-positive width"

    def test_header_fields_exist(self):
        assert "entity_name" in F8825_HEADER_FIELDS
        assert "ein" in F8825_HEADER_FIELDS

    def test_property_columns_exist(self):
        """Each property column A-D should have expense lines on page 0."""
        for col in "ABCD":
            assert f"p0_{col}_2a" in F8825_FIELD_MAP, f"8825: p0_{col}_2a missing"
            assert f"p0_{col}_3" in F8825_FIELD_MAP, f"8825: p0_{col}_3 missing"
            assert f"p0_{col}_14" in F8825_FIELD_MAP, f"8825: p0_{col}_14 missing"
            assert f"p0_{col}_18" in F8825_FIELD_MAP, f"8825: p0_{col}_18 missing"

    def test_page1_columns_exist(self):
        """Page 1 should also have property columns."""
        for col in "ABCD":
            assert f"p1_{col}_2a" in F8825_FIELD_MAP, f"8825: p1_{col}_2a missing"
            assert f"p1_{col}_18" in F8825_FIELD_MAP, f"8825: p1_{col}_18 missing"

    def test_summary_lines_exist(self):
        assert "20a" in F8825_FIELD_MAP
        assert "20b" in F8825_FIELD_MAP
        assert "21" in F8825_FIELD_MAP

    def test_property_fields_exist(self):
        """Property description fields for each slot."""
        for col in "ABCD":
            assert f"p0_{col}_addr" in F8825_PROPERTY_FIELDS
            assert f"p0_{col}_type" in F8825_PROPERTY_FIELDS
            assert f"p0_{col}_fair_days" in F8825_PROPERTY_FIELDS


class TestRender8825:
    def test_render_8825_produces_valid_pdf(self, test_template_pdf):
        """Render 8825 with basic field values."""
        field_values = {
            "p0_A_2a": ("24000", "currency"),
            "p0_A_7": ("3600", "currency"),
            "p0_A_14": ("5000", "currency"),
            "p0_A_18": ("8600", "currency"),
            "p0_A_19": ("15400", "currency"),
            "20a": ("24000", "currency"),
            "20b": ("8600", "currency"),
            "21": ("15400", "currency"),
        }
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render(
                form_id="f8825",
                tax_year=2025,
                field_values=field_values,
                header_data={"entity_name": "Rental LLC", "ein": "88-7654321"},
            )
        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1


# ---------------------------------------------------------------------------
# Form 1125-A render function tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRender1125AFunction:
    def test_render_1125a_from_tax_return(
        self, tax_return_with_data, test_template_pdf
    ):
        """render_1125a should produce a valid PDF from schedule A field values."""
        # The tax_return_with_data fixture uses 1120-S which has schedule A lines
        # Add some Schedule A values
        from apps.returns.models import FormFieldValue, FormLine

        tr = tax_return_with_data
        # Check if A1-A8 lines exist (they may not if seed doesn't include them)
        a_lines = FormLine.objects.filter(
            section__form=tr.form_definition,
            line_number__startswith="A",
        )
        if a_lines.exists():
            for line in a_lines:
                fv, _ = FormFieldValue.objects.get_or_create(
                    tax_return=tr, form_line=line, defaults={"value": ""}
                )
                if line.line_number == "A1":
                    fv.value = "50000"
                elif line.line_number == "A2":
                    fv.value = "200000"
                elif line.line_number == "A8":
                    fv.value = "180000"
                fv.save()

        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render_1125a(tr)

        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1


# ---------------------------------------------------------------------------
# Form 8825 render function tests
# ---------------------------------------------------------------------------


@pytest.fixture
def tax_return_with_rentals(seeded, tax_year, user_and_http):
    """Create a tax return with rental properties."""
    user, _ = user_and_http
    tr = TaxReturn.objects.create(
        tax_year=tax_year,
        form_definition=seeded,
        created_by=user,
    )
    # Create 3 rental properties
    RentalProperty.objects.create(
        tax_return=tr,
        description="123 Main St, Athens GA",
        property_type="1",
        fair_rental_days=365,
        personal_use_days=0,
        rents_received=Decimal("24000"),
        insurance=Decimal("1200"),
        interest_mortgage=Decimal("8000"),
        taxes=Decimal("3000"),
        repairs=Decimal("500"),
        depreciation=Decimal("5000"),
        sort_order=0,
    )
    RentalProperty.objects.create(
        tax_return=tr,
        description="456 Oak Ave, Atlanta GA",
        property_type="2",
        fair_rental_days=365,
        personal_use_days=0,
        rents_received=Decimal("36000"),
        insurance=Decimal("2400"),
        interest_mortgage=Decimal("12000"),
        taxes=Decimal("4500"),
        depreciation=Decimal("8000"),
        sort_order=1,
    )
    RentalProperty.objects.create(
        tax_return=tr,
        description="789 Pine Rd, Savannah GA",
        property_type="4",
        fair_rental_days=180,
        personal_use_days=30,
        rents_received=Decimal("18000"),
        advertising=Decimal("500"),
        cleaning_and_maintenance=Decimal("2000"),
        utilities=Decimal("3600"),
        depreciation=Decimal("4000"),
        other_expenses=Decimal("800"),
        sort_order=2,
    )
    return tr


@pytest.mark.django_db
class TestRender8825Function:
    def test_render_8825_produces_valid_pdf(
        self, tax_return_with_rentals, test_template_pdf
    ):
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render_8825(tax_return_with_rentals)

        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1

    def test_render_8825_no_properties_raises(
        self, tax_return_with_data, test_template_pdf
    ):
        """render_8825 should raise ValueError if no rental properties."""
        with pytest.raises(ValueError, match="No rental properties"):
            render_8825(tax_return_with_data)

    def test_render_8825_multiple_properties(
        self, tax_return_with_rentals, test_template_pdf
    ):
        """3 properties should fit on one page (columns A, B, C)."""
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render_8825(tax_return_with_rentals)

        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1


# ---------------------------------------------------------------------------
# Form 1125-A and 8825 API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForm1125AEndpoint:
    def test_render_1125a_endpoint(
        self, user_and_http, tax_return_with_data, test_template_pdf
    ):
        _, http = user_and_http
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            resp = http.post(
                f"/api/v1/tax-returns/{tax_return_with_data.id}/render-1125a/",
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        assert "1125-A" in resp["Content-Disposition"]


@pytest.mark.django_db
class TestForm8825Endpoint:
    def test_render_8825_endpoint(
        self, user_and_http, tax_return_with_rentals, test_template_pdf
    ):
        _, http = user_and_http
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            resp = http.post(
                f"/api/v1/tax-returns/{tax_return_with_rentals.id}/render-8825/",
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        assert "8825" in resp["Content-Disposition"]

    def test_render_8825_no_properties_returns_400(
        self, user_and_http, tax_return_with_data
    ):
        """Return with no rental properties should get 400."""
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{tax_return_with_data.id}/render-8825/",
            content_type="application/json",
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Form 7203 coordinate tests
# ---------------------------------------------------------------------------


class TestCoordinates7203:
    def test_f7203_field_map_has_entries(self):
        assert len(F7203_FIELD_MAP) > 0

    def test_coordinate_registry_contains_f7203(self):
        assert "f7203" in COORDINATE_REGISTRY

    def test_header_registry_contains_f7203(self):
        assert "f7203" in HEADER_REGISTRY

    def test_all_coords_are_field_coord(self):
        for key, coord in F7203_FIELD_MAP.items():
            assert isinstance(coord, FieldCoord), f"7203: {key} is not a FieldCoord"

    def test_header_has_required_fields(self):
        assert "taxpayer_name" in F7203_HEADER_FIELDS
        assert "taxpayer_ssn" in F7203_HEADER_FIELDS
        assert "entity_name" in F7203_HEADER_FIELDS
        assert "entity_ein" in F7203_HEADER_FIELDS

    def test_part_i_lines_mapped(self):
        """Part I stock basis lines 1-15 should be in the field map."""
        for ln in ["1", "2", "4", "5", "6", "7", "12", "13", "14", "15"]:
            assert ln in F7203_FIELD_MAP, f"Part I line {ln} missing"

    def test_part_i_sub_lines_mapped(self):
        """Part I sub-lines (3a-3m income, 8a-8c nondeductible) should be mapped."""
        for ln in ["3a", "3b", "3d", "3e", "3f", "3g", "3h", "3i", "3j", "3k"]:
            assert ln in F7203_FIELD_MAP, f"Part I sub-line {ln} missing"
        for ln in ["8a", "8b", "8c"]:
            assert ln in F7203_FIELD_MAP, f"Part I sub-line {ln} missing"

    def test_part_ii_debt_columns(self):
        """Part II has per-debt columns (a/b/c/d) for key lines."""
        for suffix in ["a", "b", "c", "d"]:
            assert f"16{suffix}" in F7203_FIELD_MAP, f"Line 16{suffix} missing"
            assert f"17{suffix}" in F7203_FIELD_MAP, f"Line 17{suffix} missing"
            assert f"18{suffix}" in F7203_FIELD_MAP, f"Line 18{suffix} missing"

    def test_part_iii_loss_columns(self):
        """Part III has 5 columns (a-e) for loss limitation lines."""
        for suffix in ["a", "b", "c", "d", "e"]:
            assert f"35{suffix}" in F7203_FIELD_MAP, f"Line 35{suffix} missing"
            assert f"47{suffix}" in F7203_FIELD_MAP, f"Line 47{suffix} missing"


# ---------------------------------------------------------------------------
# Form 7203 rendering tests
# ---------------------------------------------------------------------------


@pytest.fixture
def shareholder_with_basis(tax_return_with_k_data):
    """Create a shareholder with stock basis data for 7203 rendering."""
    return Shareholder.objects.create(
        tax_return=tax_return_with_k_data,
        name="Carol Basis",
        ssn="777-88-9999",
        ownership_percentage=Decimal("50.0000"),
        beginning_shares=500,
        ending_shares=500,
        city="Atlanta",
        state="GA",
        zip_code="30301",
        distributions=Decimal("5000.00"),
        stock_basis_boy=Decimal("100000.00"),
        capital_contributions=Decimal("10000.00"),
    )


@pytest.mark.django_db
class TestRender7203:
    def test_render_7203_produces_valid_pdf(
        self, tax_return_with_k_data, shareholder_with_basis, test_template_pdf
    ):
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render_7203(tax_return_with_k_data, shareholder_with_basis)

        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1

    def test_render_all_7203s_concatenates(
        self, tax_return_with_k_data, shareholder_with_basis, shareholder_alice, test_template_pdf
    ):
        # Set basis on alice too
        shareholder_alice.stock_basis_boy = Decimal("50000.00")
        shareholder_alice.save()

        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            pdf_bytes = render_all_7203s(tax_return_with_k_data)

        assert len(pdf_bytes) > 0
        reader = PdfReader(io.BytesIO(pdf_bytes))
        # Two shareholders × at least 1 page each
        assert len(reader.pages) >= 2


# ---------------------------------------------------------------------------
# Form 7203 API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestForm7203Endpoint:
    def test_render_7203_endpoint(
        self, user_and_http, tax_return_with_k_data, shareholder_with_basis, test_template_pdf
    ):
        _, http = user_and_http
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            resp = http.post(
                f"/api/v1/tax-returns/{tax_return_with_k_data.id}/render-7203/{shareholder_with_basis.id}/",
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        assert "7203" in resp["Content-Disposition"]

    def test_render_7203s_endpoint(
        self, user_and_http, tax_return_with_k_data, shareholder_with_basis, test_template_pdf
    ):
        _, http = user_and_http
        with patch(
            "apps.tts_forms.renderer._get_template_path",
            return_value=test_template_pdf,
        ):
            resp = http.post(
                f"/api/v1/tax-returns/{tax_return_with_k_data.id}/render-7203s/",
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        assert "7203s" in resp["Content-Disposition"]

    def test_render_7203_404_for_wrong_shareholder(
        self, user_and_http, tax_return_with_k_data
    ):
        _, http = user_and_http
        resp = http.post(
            f"/api/v1/tax-returns/{tax_return_with_k_data.id}/render-7203/{uuid.uuid4()}/",
            content_type="application/json",
        )
        assert resp.status_code == 404
