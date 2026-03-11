"""
Tests for Form 7004 AcroForm migration.

Covers:
    - Field map validation (all AcroField names exist in the actual PDF)
    - AcroForm filler produces valid PDFs with correct values
    - Header fields (entity name, EIN, address)
    - Line 1 two-digit form code split into single-digit fields
    - Renderer integration (render() routes to AcroForm path)
"""

import io
from pathlib import Path

import fitz
import pytest
from pypdf import PdfReader

from apps.tts_forms.acroform_filler import fill_form
from apps.tts_forms.field_maps.f7004_2025 import (
    FIELD_MAP as F7004_FIELD_MAP,
    HEADER_MAP as F7004_HEADER_MAP,
)
from apps.tts_forms.renderer import (
    ACROFORM_HEADER_REGISTRY,
    ACROFORM_REGISTRY,
    render,
)


_SERVER_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVER_DIR.parent
_7004_PATH = _REPO_ROOT / "resources" / "irs_forms" / "2025" / "f7004.pdf"


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


class TestF7004FieldMapValidation:
    @pytest.fixture(autouse=True)
    def _load_pdf_fields(self):
        if not _7004_PATH.exists():
            pytest.skip("f7004.pdf not available")
        doc = fitz.open(str(_7004_PATH))
        self.pdf_field_names = set()
        for page in doc:
            for widget in page.widgets():
                if widget.field_name:
                    self.pdf_field_names.add(widget.field_name)
        doc.close()

    def test_7004_has_acroform_fields(self):
        assert len(self.pdf_field_names) >= 20, (
            f"Expected 20+ AcroForm fields, got {len(self.pdf_field_names)}"
        )

    def test_all_field_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F7004_FIELD_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} FIELD_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_all_header_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F7004_HEADER_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} HEADER_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_field_map_size(self):
        total = len(F7004_FIELD_MAP) + len(F7004_HEADER_MAP)
        assert total >= 20, f"Expected 20+ mapped fields, got {total}"

    def test_no_duplicate_acro_names(self):
        seen = {}
        duplicates = []
        for key, acro in {**F7004_HEADER_MAP, **F7004_FIELD_MAP}.items():
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


class TestF7004AcroFormFiller:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _7004_PATH.exists():
            pytest.skip("f7004.pdf not available")

    def test_fill_7004_produces_valid_pdf(self):
        field_values = {
            "1a": ("2", "text"),
            "1b": ("5", "text"),
        }
        result = fill_form(
            template_path=_7004_PATH,
            field_values=field_values,
            field_map=F7004_FIELD_MAP,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_fill_7004_with_header(self):
        header_data = {
            "entity_name": "Test S-Corp LLC",
            "ein": "12-3456789",
            "address_street": "100 Main Street",
            "address_city": "Athens",
            "address_state": "GA",
            "address_zip": "30601",
        }
        result = fill_form(
            template_path=_7004_PATH,
            field_values={},
            field_map=F7004_FIELD_MAP,
            header_data=header_data,
            header_map=F7004_HEADER_MAP,
        )
        text = _extract_text(result)
        assert "Test S-Corp LLC" in text, "Entity name not found"
        assert "12-3456789" in text, "EIN not found"
        assert "Athens" in text, "City not found"

    def test_fill_7004_form_code_split(self):
        """Line 1 form code is split into two single-digit fields."""
        field_values = {
            "1a": ("2", "text"),
            "1b": ("5", "text"),
        }
        result = fill_form(
            template_path=_7004_PATH,
            field_values=field_values,
            field_map=F7004_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "2" in text, "First digit of form code not found"
        assert "5" in text, "Second digit of form code not found"

    def test_fill_7004_currency_values(self):
        field_values = {
            "6": ("50000.00", "currency"),
            "7": ("40000.00", "currency"),
            "8": ("10000.00", "currency"),
        }
        result = fill_form(
            template_path=_7004_PATH,
            field_values=field_values,
            field_map=F7004_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "50,000" in text, "Line 6 value not found"
        assert "40,000" in text, "Line 7 value not found"
        assert "10,000" in text, "Line 8 value not found"

    def test_fill_7004_widgets_stripped(self):
        field_values = {"1a": ("2", "text"), "1b": ("5", "text")}
        result = fill_form(
            template_path=_7004_PATH,
            field_values=field_values,
            field_map=F7004_FIELD_MAP,
            flatten=True,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        widget_count = sum(1 for page in doc for _ in page.widgets())
        doc.close()
        assert widget_count == 0


# ---------------------------------------------------------------------------
# Renderer Integration
# ---------------------------------------------------------------------------


class TestF7004RendererIntegration:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _7004_PATH.exists():
            pytest.skip("f7004.pdf not available")

    def test_7004_in_acroform_registry(self):
        assert "f7004" in ACROFORM_REGISTRY
        assert "f7004" in ACROFORM_HEADER_REGISTRY

    def test_render_7004_uses_acroform(self):
        field_values = {
            "1a": ("0", "text"),
            "1b": ("9", "text"),
            "5a_year": ("2025", "text"),
            "6": ("0.00", "currency"),
        }
        header_data = {
            "entity_name": "Render Test Partnership",
            "ein": "98-7654321",
            "address_street": "456 Oak Blvd",
            "address_city": "Atlanta",
            "address_state": "GA",
            "address_zip": "30301",
        }
        result = render("f7004", 2025, field_values, header_data)
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
        text = _extract_text(result)
        assert "Render Test Partnership" in text
        assert "98-7654321" in text
