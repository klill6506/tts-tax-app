"""
Tests for Form 8453-S AcroForm migration.

Covers:
    - Field map validation (all AcroField names exist in the actual PDF)
    - AcroForm filler produces valid PDFs with correct values
    - Header fields (entity name, EIN, tax year)
    - Part I financial lines (currency formatting)
    - Renderer integration (render() routes to AcroForm path)
"""

from pathlib import Path

import fitz
import pytest

from apps.tts_forms.acroform_filler import fill_form
from apps.tts_forms.field_maps.f8453s_2025 import (
    FIELD_MAP as F8453S_FIELD_MAP,
    HEADER_MAP as F8453S_HEADER_MAP,
)
from apps.tts_forms.renderer import (
    ACROFORM_FORM_IDS,

    render,
)
_SERVER_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVER_DIR.parent
_8453S_PATH = _REPO_ROOT / "resources" / "irs_forms" / "2025" / "f8453s.pdf"
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
class TestF8453SFieldMapValidation:
    @pytest.fixture(autouse=True)
    def _load_pdf_fields(self):
        if not _8453S_PATH.exists():
            pytest.skip("f8453s.pdf not available")
        doc = fitz.open(str(_8453S_PATH))
        self.pdf_field_names = set()
        for page in doc:
            for widget in page.widgets():
                if widget.field_name:
                    self.pdf_field_names.add(widget.field_name)
        doc.close()

    def test_8453s_has_acroform_fields(self):
        assert len(self.pdf_field_names) >= 20, (
            f"Expected 20+ AcroForm fields, got {len(self.pdf_field_names)}"
        )

    def test_all_field_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F8453S_FIELD_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} FIELD_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_all_header_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F8453S_HEADER_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} HEADER_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_field_map_size(self):
        total = len(F8453S_FIELD_MAP) + len(F8453S_HEADER_MAP)
        assert total >= 20, f"Expected 20+ mapped fields, got {total}"

    def test_no_duplicate_acro_names(self):
        seen = {}
        duplicates = []
        for key, acro in {**F8453S_HEADER_MAP, **F8453S_FIELD_MAP}.items():
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
class TestF8453SAcroFormFiller:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _8453S_PATH.exists():
            pytest.skip("f8453s.pdf not available")

    def test_fill_8453s_produces_valid_pdf(self):
        field_values = {"1": ("100000.00", "currency")}
        result = fill_form(
            template_path=_8453S_PATH,
            field_values=field_values,
            field_map=F8453S_FIELD_MAP,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_fill_8453s_with_header(self):
        header_data = {
            "entity_name": "Test S-Corp LLC",
            "ein": "12-3456789",
        }
        result = fill_form(
            template_path=_8453S_PATH,
            field_values={},
            field_map=F8453S_FIELD_MAP,
            header_data=header_data,
            header_map=F8453S_HEADER_MAP,
        )
        text = _extract_text(result)
        assert "Test S-Corp LLC" in text, "Entity name not found"
        assert "12-3456789" in text, "EIN not found"

    def test_fill_8453s_currency_values(self):
        field_values = {
            "1": ("300000.00", "currency"),
            "2": ("250000.00", "currency"),
            "3": ("80000.00", "currency"),
            "4": ("15000.00", "currency"),
            "5": ("95000.00", "currency"),
        }
        result = fill_form(
            template_path=_8453S_PATH,
            field_values=field_values,
            field_map=F8453S_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "300,000" in text, "Line 1 value not found"
        assert "250,000" in text, "Line 2 value not found"
        assert "80,000" in text, "Line 3 value not found"

    def test_fill_8453s_preparer_info(self):
        field_values = {
            "ero_firm_name": ("The Tax Shelter", "text"),
            "preparer_name": ("Ken CPA", "text"),
            "chk_paid_preparer": ("true", "boolean"),
        }
        result = fill_form(
            template_path=_8453S_PATH,
            field_values=field_values,
            field_map=F8453S_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "The Tax Shelter" in text, "Firm name not found"
        assert "Ken CPA" in text, "Preparer name not found"

    def test_fill_8453s_widgets_stripped(self):
        field_values = {"1": ("100000.00", "currency")}
        result = fill_form(
            template_path=_8453S_PATH,
            field_values=field_values,
            field_map=F8453S_FIELD_MAP,
            flatten=True,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        widget_count = sum(1 for page in doc for _ in page.widgets())
        doc.close()
        assert widget_count == 0
# ---------------------------------------------------------------------------
# Renderer Integration
# ---------------------------------------------------------------------------
class TestF8453SRendererIntegration:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _8453S_PATH.exists():
            pytest.skip("f8453s.pdf not available")

    def test_8453s_in_acroform_registry(self):
        assert "f8453s" in ACROFORM_FORM_IDS

    def test_render_8453s_uses_acroform(self):
        field_values = {
            "1": ("750000.00", "currency"),
            "5": ("200000.00", "currency"),
        }
        header_data = {
            "entity_name": "Render Test Corp",
            "ein": "11-2233445",
        }
        result = render("f8453s", 2025, field_values, header_data)
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
        text = _extract_text(result)
        assert "750,000" in text
        assert "Render Test Corp" in text
