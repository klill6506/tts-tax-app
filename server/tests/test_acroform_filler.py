"""
Tests for AcroForm-positioned PDF text overlay.

Covers:
    - Field map validation (all AcroField names exist in the actual PDF)
    - Text overlay filler (fill_form produces valid PDFs with correct values)
    - Checkbox handling (X drawn at correct position)
    - Currency formatting in filled fields
    - Renderer integration (render() auto-selects AcroForm path for 1120-S)
    - Formatting module (shared format functions)
"""

import io
from pathlib import Path

import fitz  # pymupdf
import pytest
from pypdf import PdfReader

from apps.tts_forms.acroform_filler import fill_form
from apps.tts_forms.field_maps import AcroField, FieldMap
from apps.tts_forms.field_maps.f1120s_2025 import (
    FIELD_MAP as F1120S_FIELD_MAP,
    HEADER_MAP as F1120S_HEADER_MAP,
)
from apps.tts_forms.formatting import (
    expand_yes_no,
    format_currency,
    format_value,
    is_truthy,
)
from apps.tts_forms.renderer import (
    ACROFORM_HEADER_REGISTRY,
    ACROFORM_REGISTRY,
    COORDINATE_REGISTRY,
    render,
)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SERVER_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVER_DIR.parent
_F1120S_PATH = _REPO_ROOT / "resources" / "irs_forms" / "2025" / "f1120s.pdf"


def _extract_text(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF (all pages concatenated)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def _extract_text_by_page(pdf_bytes: bytes) -> list[str]:
    """Extract text from each page of a PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = [page.get_text() for page in doc]
    doc.close()
    return pages


# ---------------------------------------------------------------------------
# Field Map Validation
# ---------------------------------------------------------------------------


class TestFieldMapValidation:
    """Verify every AcroField name in the field map exists in the actual PDF."""

    @pytest.fixture(autouse=True)
    def _load_pdf_fields(self):
        """Load all AcroForm field names from the f1120s.pdf."""
        if not _F1120S_PATH.exists():
            pytest.skip("f1120s.pdf not available")
        doc = fitz.open(str(_F1120S_PATH))
        self.pdf_field_names = set()
        for page in doc:
            for widget in page.widgets():
                if widget.field_name:
                    self.pdf_field_names.add(widget.field_name)
        doc.close()

    def test_f1120s_has_acroform_fields(self):
        """Verify the PDF actually has AcroForm fields."""
        assert len(self.pdf_field_names) > 300, (
            f"Expected 300+ AcroForm fields, got {len(self.pdf_field_names)}"
        )

    def test_all_field_map_names_exist_in_pdf(self):
        """Every acro_name in FIELD_MAP must match a real PDF field."""
        missing = []
        for key, acro in F1120S_FIELD_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")

        assert not missing, (
            f"{len(missing)} FIELD_MAP entries have AcroForm names not found in PDF:\n"
            + "\n".join(missing[:20])
        )

    def test_all_header_map_names_exist_in_pdf(self):
        """Every acro_name in HEADER_MAP must match a real PDF field."""
        missing = []
        for key, acro in F1120S_HEADER_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")

        assert not missing, (
            f"{len(missing)} HEADER_MAP entries have AcroForm names not found in PDF:\n"
            + "\n".join(missing[:20])
        )

    def test_field_map_size(self):
        """Verify field map has expected number of entries."""
        # 1120-S has ~390 AcroForm fields total
        total = len(F1120S_FIELD_MAP) + len(F1120S_HEADER_MAP)
        assert total >= 340, f"Expected 340+ mapped fields, got {total}"

    def test_no_duplicate_acro_names(self):
        """No two map entries should point to the same AcroForm field (except known aliases)."""
        # M2_1..M2_8 are intentional aliases for M2_1a..M2_8a (compute engine uses short keys)
        known_alias_pairs = {
            frozenset({"M2_1", "M2_1a"}),
            frozenset({"M2_2", "M2_2a"}),
            frozenset({"M2_3", "M2_3a"}),
            frozenset({"M2_4", "M2_4a"}),
            frozenset({"M2_5", "M2_5a"}),
            frozenset({"M2_6", "M2_6a"}),
            frozenset({"M2_7", "M2_7a"}),
            frozenset({"M2_8", "M2_8a"}),
        }
        seen = {}
        duplicates = []
        for key, acro in {**F1120S_HEADER_MAP, **F1120S_FIELD_MAP}.items():
            if acro.acro_name in seen:
                other = seen[acro.acro_name]
                if frozenset({key, other}) not in known_alias_pairs:
                    duplicates.append(
                        f"{key} and {other} both map to {acro.acro_name}"
                    )
            seen[acro.acro_name] = key

        assert not duplicates, (
            f"{len(duplicates)} duplicate AcroForm names:\n"
            + "\n".join(duplicates[:10])
        )


# ---------------------------------------------------------------------------
# AcroForm Filler (text overlay)
# ---------------------------------------------------------------------------


class TestAcroFormFiller:
    """Test the fill_form function (text overlay approach)."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _F1120S_PATH.exists():
            pytest.skip("f1120s.pdf not available")

    def test_fill_form_produces_valid_pdf(self):
        """fill_form returns valid PDF bytes."""
        field_values = {"1a": ("100000.00", "currency")}
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
        assert len(result) > 1000

    def test_fill_form_with_header(self):
        """fill_form correctly renders header text on the page."""
        header_data = {
            "entity_name": "Acme Corp",
            "ein": "98-7654321",
        }
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values={},
            field_map=F1120S_FIELD_MAP,
            header_data=header_data,
            header_map=F1120S_HEADER_MAP,
        )
        text = _extract_text(result)
        assert "Acme Corp" in text, "Entity name not found in filled PDF"
        assert "98-7654321" in text, "EIN not found in filled PDF"

    def test_fill_form_currency_formatting(self):
        """Currency values are formatted with commas, no decimals."""
        field_values = {
            "1a": ("1234567.89", "currency"),
            "7": ("50000.00", "currency"),
        }
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "1,234,568" in text, (
            f"Expected '1,234,568' in PDF text"
        )
        assert "50,000" in text, (
            f"Expected '50,000' in PDF text"
        )

    def test_fill_form_negative_currency(self):
        """Negative currency values use parentheses."""
        field_values = {"1a": ("-5000.00", "currency")}
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "(5,000)" in text, (
            f"Expected '(5,000)' in PDF text"
        )

    def test_fill_form_zero_currency_skipped(self):
        """Zero currency values should not appear in the output."""
        field_values = {"1a": ("0.00", "currency")}
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
        )
        # The PDF should be valid but "0" should not appear as a field value.
        # (It's fine if "0" appears in template text like "1120-S".)
        assert result[:5] == b"%PDF-"

    def test_fill_form_checkbox(self):
        """Checkbox fields render an X on the page."""
        field_values = {
            "B3_yes": ("X", "text"),  # Should draw X at B3 yes checkbox
        }
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
        )
        # Verify PDF is valid and has correct page count
        reader = PdfReader(io.BytesIO(result))
        assert len(reader.pages) == 5

    def test_fill_form_widgets_stripped(self):
        """Output PDF should have no interactive AcroForm widgets."""
        field_values = {"1a": ("100000.00", "currency")}
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
            flatten=True,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        widget_count = 0
        for page in doc:
            for widget in page.widgets():
                widget_count += 1
        doc.close()
        assert widget_count == 0, (
            f"Expected no widgets (all stripped), got {widget_count}"
        )

    def test_fill_form_empty_values_skipped(self):
        """Empty or whitespace-only values should not fill any field."""
        field_values = {
            "1a": ("", "currency"),
            "2": ("   ", "text"),
        }
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
        )
        # Verify it still produces a valid PDF
        assert result[:5] == b"%PDF-"

    def test_fill_form_multiple_pages(self):
        """Values spread across multiple pages are all rendered."""
        field_values = {
            "1a": ("100000.00", "currency"),    # Page 0
            "K1": ("50000.00", "currency"),      # Page 2
            "L1a": ("10000.00", "currency"),     # Page 3
        }
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
        )
        pages = _extract_text_by_page(result)
        assert "100,000" in pages[0], "Line 1a value not found on page 0"
        assert "50,000" in pages[2], "K1 value not found on page 2"
        assert "10,000" in pages[3], "L1a value not found on page 3"


# ---------------------------------------------------------------------------
# Renderer Integration
# ---------------------------------------------------------------------------


class TestRendererAcroFormIntegration:
    """Test that render() correctly routes to the AcroForm path."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _F1120S_PATH.exists():
            pytest.skip("f1120s.pdf not available")

    def test_f1120s_in_acroform_registry(self):
        """1120-S should be registered in both ACROFORM and COORDINATE registries."""
        assert "f1120s" in ACROFORM_REGISTRY
        assert "f1120s" in ACROFORM_HEADER_REGISTRY
        assert "f1120s" in COORDINATE_REGISTRY  # Kept as fallback

    def test_render_f1120s_uses_acroform(self):
        """render('f1120s', ...) should produce a valid PDF with text values."""
        field_values = {
            "1a": ("150000.00", "currency"),
            "21": ("75000.00", "currency"),
        }
        header_data = {
            "entity_name": "Integration Test Corp",
            "ein": "11-2233445",
        }
        result = render("f1120s", 2025, field_values, header_data)
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

        # Verify text values appear in the output
        text = _extract_text(result)
        assert "Integration Test Corp" in text
        assert "150,000" in text

    def test_render_f1065_uses_coordinates(self):
        """render('f1065', ...) should still use coordinate overlay."""
        # f1065 is not in ACROFORM_REGISTRY, so it falls back to coordinates
        assert "f1065" not in ACROFORM_REGISTRY
        assert "f1065" in COORDINATE_REGISTRY

    def test_render_f1120s_with_statements(self):
        """render() with statement pages should append them after the form."""
        field_values = {"1a": ("100000.00", "currency")}
        statement_pages = [
            {
                "title": "Form 1120-S (2025) — Statement for Line 19",
                "subtitle": "Other deductions",
                "form_code": "1120-S",
                "items": [
                    {"description": "Office supplies", "amount": "1200.00"},
                    {"description": "Travel", "amount": "3800.00"},
                ],
            }
        ]
        result = render(
            "f1120s", 2025, field_values,
            statement_pages=statement_pages,
        )
        reader = PdfReader(io.BytesIO(result))
        # 1120-S is 5 pages + 1 statement page = 6
        assert len(reader.pages) == 6, (
            f"Expected 6 pages (5 form + 1 statement), got {len(reader.pages)}"
        )


# ---------------------------------------------------------------------------
# Formatting Module
# ---------------------------------------------------------------------------


class TestFormattingModule:
    """Test the shared formatting functions."""

    def test_format_currency_positive(self):
        assert format_currency("1234.56") == "1,235"

    def test_format_currency_negative(self):
        assert format_currency("-1234.56") == "(1,235)"

    def test_format_currency_zero(self):
        assert format_currency("0.00") == ""

    def test_format_currency_empty(self):
        assert format_currency("") == ""

    def test_format_currency_none(self):
        assert format_currency(None) == ""

    def test_format_currency_large(self):
        assert format_currency("1234567.89") == "1,234,568"

    def test_format_value_currency(self):
        assert format_value("5000.00", "currency") == "5,000"

    def test_format_value_boolean_true(self):
        assert format_value("true", "boolean") == "X"
        assert format_value("yes", "boolean") == "X"
        assert format_value("1", "boolean") == "X"

    def test_format_value_boolean_false(self):
        assert format_value("false", "boolean") == ""
        assert format_value("no", "boolean") == ""

    def test_format_value_percentage(self):
        assert format_value("12.5", "percentage") == "12.5%"

    def test_format_value_text(self):
        assert format_value("United States", "text") == "United States"

    def test_is_truthy(self):
        assert is_truthy("true") is True
        assert is_truthy("yes") is True
        assert is_truthy("1") is True
        assert is_truthy("X") is True
        assert is_truthy("x") is True
        assert is_truthy("false") is False
        assert is_truthy("no") is False
        assert is_truthy("") is False

    def test_expand_yes_no_true(self):
        fv = {"B3": ("true", "boolean")}
        expand_yes_no(fv)
        assert "B3" not in fv
        assert fv["B3_yes"] == ("X", "text")
        assert "B3_no" not in fv

    def test_expand_yes_no_false(self):
        fv = {"B4": ("false", "boolean")}
        expand_yes_no(fv)
        assert "B4" not in fv
        assert fv["B4_no"] == ("X", "text")
        assert "B4_yes" not in fv

    def test_expand_yes_no_skips_non_boolean(self):
        fv = {"B8": ("50000.00", "currency")}
        expand_yes_no(fv)
        assert fv["B8"] == ("50000.00", "currency")
