"""
Tests for Schedule K-1 (Form 1120-S) AcroForm migration.

Covers:
    - Field map validation (all AcroField names exist in the actual PDF)
    - Text overlay filler produces valid PDFs with correct values
    - Multi-line header fields (corp name/address, shareholder name/address)
    - Currency formatting and code+amount pairs
    - Renderer integration (render() routes to AcroForm path)
"""

import io
from pathlib import Path

import fitz
import pytest
from pypdf import PdfReader

from apps.tts_forms.acroform_filler import fill_form
from apps.tts_forms.field_maps.f1120sk1_2025 import (
    FIELD_MAP as K1_FIELD_MAP,
    HEADER_MAP as K1_HEADER_MAP,
)
from apps.tts_forms.renderer import (
    ACROFORM_FORM_IDS,

    render,
)
_SERVER_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVER_DIR.parent
_K1_PATH = _REPO_ROOT / "resources" / "irs_forms" / "2025" / "f1120ssk.pdf"
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
class TestK1FieldMapValidation:
    @pytest.fixture(autouse=True)
    def _load_pdf_fields(self):
        if not _K1_PATH.exists():
            pytest.skip("f1120ssk.pdf not available")
        doc = fitz.open(str(_K1_PATH))
        self.pdf_field_names = set()
        for page in doc:
            for widget in page.widgets():
                if widget.field_name:
                    self.pdf_field_names.add(widget.field_name)
        doc.close()

    def test_k1_has_acroform_fields(self):
        assert len(self.pdf_field_names) >= 100, (
            f"Expected 100+ AcroForm fields, got {len(self.pdf_field_names)}"
        )

    def test_all_field_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in K1_FIELD_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} FIELD_MAP entries not found in PDF:\n"
            + "\n".join(missing[:20])
        )

    def test_all_header_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in K1_HEADER_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} HEADER_MAP entries not found in PDF:\n"
            + "\n".join(missing[:20])
        )

    def test_field_map_size(self):
        total = len(K1_FIELD_MAP) + len(K1_HEADER_MAP)
        assert total >= 80, f"Expected 80+ mapped fields, got {total}"

    def test_no_duplicate_acro_names(self):
        seen = {}
        duplicates = []
        for key, acro in {**K1_HEADER_MAP, **K1_FIELD_MAP}.items():
            if acro.acro_name in seen:
                duplicates.append(
                    f"{key} and {seen[acro.acro_name]} both map to {acro.acro_name}"
                )
            seen[acro.acro_name] = key
        assert not duplicates, (
            f"{len(duplicates)} duplicate AcroForm names:\n"
            + "\n".join(duplicates[:10])
        )
# ---------------------------------------------------------------------------
# AcroForm Filler
# ---------------------------------------------------------------------------
class TestK1AcroFormFiller:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _K1_PATH.exists():
            pytest.skip("f1120ssk.pdf not available")

    def test_fill_k1_produces_valid_pdf(self):
        field_values = {"1": ("50000.00", "currency")}
        result = fill_form(
            template_path=_K1_PATH,
            field_values=field_values,
            field_map=K1_FIELD_MAP,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_fill_k1_with_header(self):
        header_data = {
            "corp_ein": "12-3456789",
            "corp_name_address": "Test Corp\n123 Main St\nAthens, GA 30601",
            "sh_ssn": "987-65-4321",
            "sh_name_address": "John Doe\n456 Oak Ave\nAtlanta, GA 30301",
            "sh_ownership_pct": "50.00",
        }
        result = fill_form(
            template_path=_K1_PATH,
            field_values={},
            field_map=K1_FIELD_MAP,
            header_data=header_data,
            header_map=K1_HEADER_MAP,
        )
        text = _extract_text(result)
        assert "12-3456789" in text, "Corp EIN not found"
        assert "Test Corp" in text, "Corp name not found"
        assert "987-65-4321" in text, "Shareholder SSN not found"
        assert "John Doe" in text, "Shareholder name not found"

    def test_fill_k1_currency_values(self):
        field_values = {
            "1": ("75000.00", "currency"),
            "16_amt_1": ("10000.00", "currency"),
        }
        result = fill_form(
            template_path=_K1_PATH,
            field_values=field_values,
            field_map=K1_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "75,000" in text, "Line 1 value not found"
        assert "10,000" in text, "Line 16 value not found"

    def test_fill_k1_code_and_amount(self):
        field_values = {
            "16_code_1": ("A", "text"),
            "16_amt_1": ("5000.00", "currency"),
            "17_code_1": ("AC", "text"),
            "17_amt_1": ("3000.00", "currency"),
        }
        result = fill_form(
            template_path=_K1_PATH,
            field_values=field_values,
            field_map=K1_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "5,000" in text
        assert "3,000" in text

    def test_fill_k1_widgets_stripped(self):
        field_values = {"1": ("50000.00", "currency")}
        result = fill_form(
            template_path=_K1_PATH,
            field_values=field_values,
            field_map=K1_FIELD_MAP,
            flatten=True,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        widget_count = sum(1 for page in doc for _ in page.widgets())
        doc.close()
        assert widget_count == 0
# ---------------------------------------------------------------------------
# Renderer Integration
# ---------------------------------------------------------------------------
class TestK1RendererIntegration:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _K1_PATH.exists():
            pytest.skip("f1120ssk.pdf not available")

    def test_k1_in_acroform_registry(self):
        assert "f1120sk1" in ACROFORM_FORM_IDS

    def test_render_k1_uses_acroform(self):
        field_values = {
            "1": ("100000.00", "currency"),
            "4": ("5000.00", "currency"),
        }
        header_data = {
            "corp_ein": "11-2233445",
            "corp_name_address": "Render Test Corp",
            "sh_ssn": "555-66-7777",
            "sh_name_address": "Jane Smith",
            "sh_ownership_pct": "100.00",
        }
        result = render("f1120sk1", 2025, field_values, header_data)
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
        text = _extract_text(result)
        assert "100,000" in text
        assert "Render Test Corp" in text
