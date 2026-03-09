"""
Tests for Form 8825 (Rental Real Estate) AcroForm migration.

Covers:
    - Field map validation (all AcroField names exist in the actual PDF)
    - AcroForm filler produces valid PDFs with correct values
    - Header fields (entity name, EIN)
    - Property descriptors and expense lines
    - Summary lines (20a, 20b, 21)
    - Renderer integration (render() routes to AcroForm path)
"""

from pathlib import Path

import fitz
import pytest

from apps.tts_forms.acroform_filler import fill_form
from apps.tts_forms.field_maps.f8825 import (
    FIELD_MAP as F8825_FIELD_MAP,
    HEADER_MAP as F8825_HEADER_MAP,
)
from apps.tts_forms.renderer import (
    ACROFORM_HEADER_REGISTRY,
    ACROFORM_REGISTRY,
    render,
)


_SERVER_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVER_DIR.parent
_8825_PATH = _REPO_ROOT / "resources" / "irs_forms" / "2025" / "f8825.pdf"


def _extract_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


# ---------------------------------------------------------------------------
# Field Map Validation
# ---------------------------------------------------------------------------


class TestF8825FieldMapValidation:
    @pytest.fixture(autouse=True)
    def _load_pdf_fields(self):
        if not _8825_PATH.exists():
            pytest.skip("f8825.pdf not available")
        doc = fitz.open(str(_8825_PATH))
        self.pdf_field_names = set()
        for page in doc:
            for widget in page.widgets():
                if widget.field_name:
                    self.pdf_field_names.add(widget.field_name)
        doc.close()

    def test_8825_has_acroform_fields(self):
        assert len(self.pdf_field_names) >= 200, (
            f"Expected 200+ AcroForm fields, got {len(self.pdf_field_names)}"
        )

    def test_all_field_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F8825_FIELD_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} FIELD_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_all_header_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F8825_HEADER_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} HEADER_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_field_map_size(self):
        total = len(F8825_FIELD_MAP) + len(F8825_HEADER_MAP)
        assert total >= 200, f"Expected 200+ mapped fields, got {total}"

    def test_no_duplicate_acro_names(self):
        seen = {}
        duplicates = []
        for key, acro in {**F8825_HEADER_MAP, **F8825_FIELD_MAP}.items():
            if acro.acro_name in seen:
                duplicates.append(
                    f"{key} and {seen[acro.acro_name]} both map to {acro.acro_name}"
                )
            seen[acro.acro_name] = key
        assert not duplicates, (
            f"{len(duplicates)} duplicate AcroForm names:\n"
            + "\n".join(duplicates)
        )


# ---------------------------------------------------------------------------
# AcroForm Filler
# ---------------------------------------------------------------------------


class TestF8825AcroFormFiller:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _8825_PATH.exists():
            pytest.skip("f8825.pdf not available")

    def test_fill_8825_produces_valid_pdf(self):
        field_values = {"2a_A": ("5000.00", "currency")}
        result = fill_form(
            template_path=_8825_PATH,
            field_values=field_values,
            field_map=F8825_FIELD_MAP,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_fill_8825_with_header(self):
        header_data = {
            "entity_name": "Rental Properties LLC",
            "ein": "88-7654321",
        }
        result = fill_form(
            template_path=_8825_PATH,
            field_values={},
            field_map=F8825_FIELD_MAP,
            header_data=header_data,
            header_map=F8825_HEADER_MAP,
        )
        text = _extract_text(result)
        assert "Rental Properties LLC" in text, "Entity name not found"
        assert "88-7654321" in text, "EIN not found"

    def test_fill_8825_property_descriptor(self):
        field_values = {
            "1_A_desc": ("Office Building", "text"),
            "1_A_type": ("Commercial", "text"),
            "1_A_fair_days": ("365", "text"),
        }
        result = fill_form(
            template_path=_8825_PATH,
            field_values=field_values,
            field_map=F8825_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "Office Building" in text, "Property A description not found"

    def test_fill_8825_expense_lines(self):
        field_values = {
            "4_A": ("12000.00", "currency"),   # Insurance
            "7_B": ("8500.00", "currency"),     # Repairs
            "8_C": ("6200.00", "currency"),     # Taxes
            "20a": ("50000.00", "currency"),    # Total gross rents
            "21": ("15000.00", "currency"),     # Net income
        }
        result = fill_form(
            template_path=_8825_PATH,
            field_values=field_values,
            field_map=F8825_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "12,000" in text, "Insurance amount not found"
        assert "50,000" in text, "Total gross rents not found"

    def test_fill_8825_page2_properties(self):
        field_values = {
            "1_E_desc": ("Warehouse E", "text"),
            "2a_E": ("3000.00", "currency"),
            "7_F": ("4500.00", "currency"),
        }
        result = fill_form(
            template_path=_8825_PATH,
            field_values=field_values,
            field_map=F8825_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "Warehouse E" in text, "Page 2 property E description not found"

    def test_fill_8825_widgets_stripped(self):
        field_values = {"2a_A": ("5000.00", "currency")}
        result = fill_form(
            template_path=_8825_PATH,
            field_values=field_values,
            field_map=F8825_FIELD_MAP,
            flatten=True,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        widget_count = sum(1 for page in doc for _ in page.widgets())
        doc.close()
        assert widget_count == 0


# ---------------------------------------------------------------------------
# Renderer Integration
# ---------------------------------------------------------------------------


class TestF8825RendererIntegration:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _8825_PATH.exists():
            pytest.skip("f8825.pdf not available")

    def test_8825_in_acroform_registry(self):
        assert "f8825" in ACROFORM_REGISTRY
        assert "f8825" in ACROFORM_HEADER_REGISTRY

    def test_render_8825_uses_acroform(self):
        field_values = {
            "4_A": ("9500.00", "currency"),
            "20a": ("30000.00", "currency"),
        }
        header_data = {
            "entity_name": "Render Test Rentals Inc",
            "ein": "22-3344556",
        }
        result = render("f8825", 2025, field_values, header_data)
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
        text = _extract_text(result)
        assert "9,500" in text
        assert "Render Test Rentals Inc" in text
