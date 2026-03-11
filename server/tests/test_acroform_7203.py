"""
Tests for Form 7203 (S Corporation Shareholder Stock and Debt Basis Limitations)
AcroForm migration.

Covers:
    - Field map validation (all AcroField names exist in the actual PDF)
    - AcroForm filler produces valid PDFs with correct values
    - Header fields (shareholder name, SSN, entity name, EIN)
    - Part I stock basis lines
    - Part II debt columns
    - Part III loss columns
    - Checkbox fields (Item D, debt type)
    - Renderer integration (render() routes to AcroForm path)
"""

from pathlib import Path

import fitz
import pytest

from apps.tts_forms.acroform_filler import fill_form
from apps.tts_forms.field_maps.f7203_2025 import (
    FIELD_MAP as F7203_FIELD_MAP,
    HEADER_MAP as F7203_HEADER_MAP,
)
from apps.tts_forms.renderer import (
    ACROFORM_FORM_IDS,

    render,
)
_SERVER_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVER_DIR.parent
_7203_PATH = _REPO_ROOT / "resources" / "irs_forms" / "2025" / "f7203.pdf"
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
class TestF7203FieldMapValidation:
    @pytest.fixture(autouse=True)
    def _load_pdf_fields(self):
        if not _7203_PATH.exists():
            pytest.skip("f7203.pdf not available")
        doc = fitz.open(str(_7203_PATH))
        self.pdf_field_names = set()
        for page in doc:
            for widget in page.widgets():
                if widget.field_name:
                    self.pdf_field_names.add(widget.field_name)
        doc.close()

    def test_7203_has_acroform_fields(self):
        assert len(self.pdf_field_names) >= 150, (
            f"Expected 150+ AcroForm fields, got {len(self.pdf_field_names)}"
        )

    def test_all_field_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F7203_FIELD_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} FIELD_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_all_header_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F7203_HEADER_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} HEADER_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_field_map_size(self):
        total = len(F7203_FIELD_MAP) + len(F7203_HEADER_MAP)
        assert total >= 150, f"Expected 150+ mapped fields, got {total}"

    def test_no_duplicate_acro_names(self):
        seen = {}
        duplicates = []
        for key, acro in {**F7203_HEADER_MAP, **F7203_FIELD_MAP}.items():
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
class TestF7203AcroFormFiller:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _7203_PATH.exists():
            pytest.skip("f7203.pdf not available")

    def test_fill_7203_produces_valid_pdf(self):
        field_values = {"1": ("50000.00", "currency")}
        result = fill_form(
            template_path=_7203_PATH,
            field_values=field_values,
            field_map=F7203_FIELD_MAP,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_fill_7203_with_header(self):
        header_data = {
            "taxpayer_name": "John Q. Shareholder",
            "taxpayer_ssn": "123-45-6789",
            "entity_name": "Test S Corp LLC",
            "entity_ein": "99-8877665",
        }
        result = fill_form(
            template_path=_7203_PATH,
            field_values={},
            field_map=F7203_FIELD_MAP,
            header_data=header_data,
            header_map=F7203_HEADER_MAP,
        )
        text = _extract_text(result)
        assert "John Q. Shareholder" in text, "Shareholder name not found"
        assert "Test S Corp LLC" in text, "Entity name not found"

    def test_fill_7203_part_i_stock_basis(self):
        field_values = {
            "1": ("100000.00", "currency"),
            "2": ("25000.00", "currency"),
            "3a": ("50000.00", "currency"),
            "5": ("175000.00", "currency"),
            "15": ("150000.00", "currency"),
        }
        result = fill_form(
            template_path=_7203_PATH,
            field_values=field_values,
            field_map=F7203_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "100,000" in text, "Line 1 value not found"
        assert "175,000" in text, "Line 5 value not found"
        assert "150,000" in text, "Line 15 value not found"

    def test_fill_7203_part_ii_debt(self):
        field_values = {
            "16a": ("80000.00", "currency"),
            "16d": ("80000.00", "currency"),
            "20a": ("70000.00", "currency"),
            "20d": ("70000.00", "currency"),
        }
        result = fill_form(
            template_path=_7203_PATH,
            field_values=field_values,
            field_map=F7203_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "80,000" in text, "Line 16a value not found"
        assert "70,000" in text, "Line 20 value not found"

    def test_fill_7203_part_iii_losses(self):
        field_values = {
            "35a": ("10000.00", "currency"),
            "35c": ("10000.00", "currency"),
            "47a": ("10000.00", "currency"),
            "47c": ("10000.00", "currency"),
        }
        result = fill_form(
            template_path=_7203_PATH,
            field_values=field_values,
            field_map=F7203_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "10,000" in text, "Part III value not found"

    def test_fill_7203_checkboxes(self):
        header_data = {
            "item_d_1": "true",
            "debt1_direct": "true",
        }
        result = fill_form(
            template_path=_7203_PATH,
            field_values={},
            field_map=F7203_FIELD_MAP,
            header_data=header_data,
            header_map=F7203_HEADER_MAP,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_fill_7203_widgets_stripped(self):
        field_values = {"1": ("50000.00", "currency")}
        result = fill_form(
            template_path=_7203_PATH,
            field_values=field_values,
            field_map=F7203_FIELD_MAP,
            flatten=True,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        widget_count = sum(1 for page in doc for _ in page.widgets())
        doc.close()
        assert widget_count == 0
# ---------------------------------------------------------------------------
# Renderer Integration
# ---------------------------------------------------------------------------
class TestF7203RendererIntegration:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _7203_PATH.exists():
            pytest.skip("f7203.pdf not available")

    def test_7203_in_acroform_registry(self):
        assert "f7203" in ACROFORM_FORM_IDS

    def test_render_7203_uses_acroform(self):
        field_values = {
            "1": ("200000.00", "currency"),
            "15": ("180000.00", "currency"),
        }
        header_data = {
            "taxpayer_name": "Render Test Person",
            "entity_name": "Render Test S Corp",
            "entity_ein": "55-6677889",
        }
        result = render("f7203", 2025, field_values, header_data)
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
        text = _extract_text(result)
        assert "200,000" in text
        assert "Render Test Person" in text
