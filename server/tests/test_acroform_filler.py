"""
Tests for AcroForm-based PDF field filling.

Covers:
    - Field map validation (all AcroField names exist in the actual PDF)
    - AcroForm filler (fill_form produces valid PDFs with correct values)
    - Checkbox handling (on/off states)
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
from apps.tts_forms.field_maps.f1120s import (
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
        """No two map entries should point to the same AcroForm field."""
        seen = {}
        duplicates = []
        for key, acro in {**F1120S_HEADER_MAP, **F1120S_FIELD_MAP}.items():
            if acro.acro_name in seen:
                other = seen[acro.acro_name]
                duplicates.append(
                    f"{key} and {other} both map to {acro.acro_name}"
                )
            seen[acro.acro_name] = key

        assert not duplicates, (
            f"{len(duplicates)} duplicate AcroForm names:\n"
            + "\n".join(duplicates[:10])
        )


# ---------------------------------------------------------------------------
# AcroForm Filler
# ---------------------------------------------------------------------------


class TestAcroFormFiller:
    """Test the fill_form function."""

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
        """fill_form correctly fills header fields."""
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
        # Verify by reading the output
        doc = fitz.open(stream=result, filetype="pdf")
        found_name = False
        found_ein = False
        for page in doc:
            for widget in page.widgets():
                if widget.field_value == "Acme Corp":
                    found_name = True
                if widget.field_value == "98-7654321":
                    found_ein = True
        doc.close()
        assert found_name, "Entity name not found in filled PDF"
        assert found_ein, "EIN not found in filled PDF"

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
        doc = fitz.open(stream=result, filetype="pdf")
        values = {}
        for page in doc:
            for widget in page.widgets():
                if widget.field_value:
                    values[widget.field_name] = widget.field_value
        doc.close()

        # Find the field for line 1a
        acro_1a = F1120S_FIELD_MAP["1a"].acro_name
        assert values.get(acro_1a) == "1,234,568", (
            f"Expected '1,234,568', got {values.get(acro_1a)!r}"
        )

    def test_fill_form_negative_currency(self):
        """Negative currency values use parentheses."""
        field_values = {"1a": ("-5000.00", "currency")}
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        acro_1a = F1120S_FIELD_MAP["1a"].acro_name
        for page in doc:
            for widget in page.widgets():
                if widget.field_name == acro_1a:
                    assert widget.field_value == "(5,000)", (
                        f"Expected '(5,000)', got {widget.field_value!r}"
                    )
        doc.close()

    def test_fill_form_zero_currency_skipped(self):
        """Zero currency values should not be filled."""
        field_values = {"1a": ("0.00", "currency")}
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        acro_1a = F1120S_FIELD_MAP["1a"].acro_name
        for page in doc:
            for widget in page.widgets():
                if widget.field_name == acro_1a:
                    val = widget.field_value
                    assert not val or val.strip() == "", (
                        f"Zero value should be empty, got {val!r}"
                    )
        doc.close()

    def test_fill_form_checkbox(self):
        """Checkbox fields are properly checked/unchecked."""
        field_values = {
            "B3_yes": ("X", "text"),  # Should check B3 yes
        }
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        acro_name = F1120S_FIELD_MAP["B3_yes"].acro_name
        found = False
        for page in doc:
            for widget in page.widgets():
                if widget.field_name == acro_name:
                    found = True
                    assert widget.field_value not in (None, "", "Off"), (
                        f"Checkbox should be checked, got {widget.field_value!r}"
                    )
        doc.close()
        assert found, f"Checkbox widget {acro_name} not found"

    def test_fill_form_flatten(self):
        """Flattened fields should be read-only."""
        field_values = {"1a": ("100000.00", "currency")}
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
            flatten=True,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        acro_1a = F1120S_FIELD_MAP["1a"].acro_name
        for page in doc:
            for widget in page.widgets():
                if widget.field_name == acro_1a:
                    assert widget.field_flags & 1, "Filled field should be read-only"
        doc.close()

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
        """Values spread across multiple pages are all filled."""
        field_values = {
            "1a": ("100000.00", "currency"),    # Page 1
            "K1": ("50000.00", "currency"),      # Page 3
            "L1a": ("10000.00", "currency"),     # Page 4
        }
        result = fill_form(
            template_path=_F1120S_PATH,
            field_values=field_values,
            field_map=F1120S_FIELD_MAP,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        filled_pages = set()
        for page_idx, page in enumerate(doc):
            for widget in page.widgets():
                if widget.field_value and widget.field_value.strip():
                    filled_pages.add(page_idx)
        doc.close()
        assert len(filled_pages) >= 3, (
            f"Expected values on 3+ pages, got {filled_pages}"
        )


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
        """render('f1120s', ...) should produce a valid PDF via AcroForm path."""
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

        # Verify it's the AcroForm output (should have widget data, not just overlay)
        doc = fitz.open(stream=result, filetype="pdf")
        has_filled_widgets = False
        for page in doc:
            for widget in page.widgets():
                if widget.field_value and widget.field_value.strip():
                    has_filled_widgets = True
                    break
        doc.close()
        assert has_filled_widgets, "AcroForm path should produce widgets with values"

    def test_render_f1065_uses_coordinates(self):
        """render('f1065', ...) should still use coordinate overlay."""
        # f1065 is not in ACROFORM_REGISTRY, so it falls back to coordinates
        assert "f1065" not in ACROFORM_REGISTRY
        assert "f1065" in COORDINATE_REGISTRY

    def test_render_f1120s_with_statements(self):
        """render() with statement pages should append them after AcroForm output."""
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
