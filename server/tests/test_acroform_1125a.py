"""
Tests for Form 1125-A (Cost of Goods Sold) AcroForm migration.

Covers:
    - Field map validation (all AcroField names exist in the actual PDF)
    - AcroForm filler produces valid PDFs with correct values
    - Header fields (entity name, EIN)
    - Lines 1-8 currency amounts
    - Line 9 checkbox fields
    - Renderer integration (render() routes to AcroForm path)
"""

from pathlib import Path

import fitz
import pytest

from apps.tts_forms.acroform_filler import fill_form
from apps.tts_forms.field_maps.f1125a_2025 import (
    FIELD_MAP as F1125A_FIELD_MAP,
    HEADER_MAP as F1125A_HEADER_MAP,
)
from apps.tts_forms.renderer import (
    ACROFORM_FORM_IDS,

    render,
)
_SERVER_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVER_DIR.parent
_1125A_PATH = _REPO_ROOT / "resources" / "irs_forms" / "2025" / "f1125a.pdf"
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
class TestF1125AFieldMapValidation:
    @pytest.fixture(autouse=True)
    def _load_pdf_fields(self):
        if not _1125A_PATH.exists():
            pytest.skip("f1125a.pdf not available")
        doc = fitz.open(str(_1125A_PATH))
        self.pdf_field_names = set()
        for page in doc:
            for widget in page.widgets():
                if widget.field_name:
                    self.pdf_field_names.add(widget.field_name)
        doc.close()

    def test_1125a_has_acroform_fields(self):
        assert len(self.pdf_field_names) >= 20, (
            f"Expected 20+ AcroForm fields, got {len(self.pdf_field_names)}"
        )

    def test_all_field_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F1125A_FIELD_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} FIELD_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_all_header_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F1125A_HEADER_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} HEADER_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_field_map_size(self):
        total = len(F1125A_FIELD_MAP) + len(F1125A_HEADER_MAP)
        assert total >= 20, f"Expected 20+ mapped fields, got {total}"

    def test_no_duplicate_acro_names(self):
        seen = {}
        duplicates = []
        for key, acro in {**F1125A_HEADER_MAP, **F1125A_FIELD_MAP}.items():
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
class TestF1125AAcroFormFiller:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _1125A_PATH.exists():
            pytest.skip("f1125a.pdf not available")

    def test_fill_1125a_produces_valid_pdf(self):
        field_values = {"1": ("10000.00", "currency")}
        result = fill_form(
            template_path=_1125A_PATH,
            field_values=field_values,
            field_map=F1125A_FIELD_MAP,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_fill_1125a_with_header(self):
        header_data = {
            "entity_name": "Test Manufacturing LLC",
            "ein": "55-1234567",
        }
        result = fill_form(
            template_path=_1125A_PATH,
            field_values={},
            field_map=F1125A_FIELD_MAP,
            header_data=header_data,
            header_map=F1125A_HEADER_MAP,
        )
        text = _extract_text(result)
        assert "Test Manufacturing LLC" in text, "Entity name not found"
        assert "55-1234567" in text, "EIN not found"

    def test_fill_1125a_cogs_lines(self):
        field_values = {
            "1": ("50000.00", "currency"),
            "2": ("100000.00", "currency"),
            "3": ("25000.00", "currency"),
            "6": ("175000.00", "currency"),
            "7": ("40000.00", "currency"),
            "8": ("135000.00", "currency"),
        }
        result = fill_form(
            template_path=_1125A_PATH,
            field_values=field_values,
            field_map=F1125A_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "50,000" in text, "Line 1 value not found"
        assert "100,000" in text, "Line 2 value not found"
        assert "135,000" in text, "Line 8 value not found"

    def test_fill_1125a_checkboxes(self):
        field_values = {
            "9a_cost": ("true", "boolean"),
            "9f_yes": ("true", "boolean"),
        }
        result = fill_form(
            template_path=_1125A_PATH,
            field_values=field_values,
            field_map=F1125A_FIELD_MAP,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_fill_1125a_widgets_stripped(self):
        field_values = {"1": ("10000.00", "currency")}
        result = fill_form(
            template_path=_1125A_PATH,
            field_values=field_values,
            field_map=F1125A_FIELD_MAP,
            flatten=True,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        widget_count = sum(1 for page in doc for _ in page.widgets())
        doc.close()
        assert widget_count == 0
# ---------------------------------------------------------------------------
# Renderer Integration
# ---------------------------------------------------------------------------
class TestF1125ARendererIntegration:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _1125A_PATH.exists():
            pytest.skip("f1125a.pdf not available")

    def test_1125a_in_acroform_registry(self):
        assert "f1125a" in ACROFORM_FORM_IDS

    def test_render_1125a_uses_acroform(self):
        field_values = {
            "1": ("60000.00", "currency"),
            "8": ("120000.00", "currency"),
        }
        header_data = {
            "entity_name": "Render Test Mfg Corp",
            "ein": "33-4455667",
        }
        result = render("f1125a", 2025, field_values, header_data)
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
        text = _extract_text(result)
        assert "60,000" in text
        assert "Render Test Mfg Corp" in text
