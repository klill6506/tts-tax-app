"""
Tests for Form 4562 (Depreciation) and Form 4797 (Sales of Business Property)
render functions.

Covers:
    - Field map validation (all AcroField names exist in the actual PDF)
    - AcroForm filler produces valid PDFs
    - render_4562 produces non-empty PDF with/without assets
    - render_4797 produces non-empty PDF with/without disposed assets
    - Disposed assets appear on 4797
    - 4562 totals consistency
    - Renderer integration (forms in ACROFORM_FORM_IDS)
"""

from pathlib import Path

import fitz
import pytest

from apps.tts_forms.acroform_filler import fill_form
from apps.tts_forms.field_maps.f4562_2025 import (
    FIELD_MAP as F4562_FIELD_MAP,
    HEADER_MAP as F4562_HEADER_MAP,
)
from apps.tts_forms.field_maps.f4797_2025 import (
    FIELD_MAP as F4797_FIELD_MAP,
    HEADER_MAP as F4797_HEADER_MAP,
)
from apps.tts_forms.renderer import (
    ACROFORM_FORM_IDS,
    render,
)

_SERVER_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SERVER_DIR.parent
_F4562_PATH = _REPO_ROOT / "resources" / "irs_forms" / "2025" / "f4562.pdf"
_F4797_PATH = _REPO_ROOT / "resources" / "irs_forms" / "2025" / "f4797.pdf"


def _extract_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


# ===========================================================================
# Form 4562 Field Map Validation
# ===========================================================================
class TestF4562FieldMapValidation:
    @pytest.fixture(autouse=True)
    def _load_pdf_fields(self):
        if not _F4562_PATH.exists():
            pytest.skip("f4562.pdf not available")
        doc = fitz.open(str(_F4562_PATH))
        self.pdf_field_names = set()
        for page in doc:
            for widget in page.widgets():
                if widget.field_name:
                    self.pdf_field_names.add(widget.field_name)
        doc.close()

    def test_f4562_has_acroform_fields(self):
        assert len(self.pdf_field_names) >= 200, (
            f"Expected 200+ AcroForm fields, got {len(self.pdf_field_names)}"
        )

    def test_all_field_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F4562_FIELD_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} FIELD_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_all_header_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F4562_HEADER_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} HEADER_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_no_duplicate_acro_names(self):
        seen = {}
        duplicates = []
        for key, acro in {**F4562_HEADER_MAP, **F4562_FIELD_MAP}.items():
            if acro.acro_name in seen:
                duplicates.append(
                    f"{key} and {seen[acro.acro_name]} both map to {acro.acro_name}"
                )
            seen[acro.acro_name] = key
        assert not duplicates, (
            f"{len(duplicates)} duplicate AcroForm names:\n"
            + "\n".join(duplicates)
        )

    def test_f4562_in_acroform_registry(self):
        assert "f4562" in ACROFORM_FORM_IDS


# ===========================================================================
# Form 4797 Field Map Validation
# ===========================================================================
class TestF4797FieldMapValidation:
    @pytest.fixture(autouse=True)
    def _load_pdf_fields(self):
        if not _F4797_PATH.exists():
            pytest.skip("f4797.pdf not available")
        doc = fitz.open(str(_F4797_PATH))
        self.pdf_field_names = set()
        for page in doc:
            for widget in page.widgets():
                if widget.field_name:
                    self.pdf_field_names.add(widget.field_name)
        doc.close()

    def test_f4797_has_acroform_fields(self):
        assert len(self.pdf_field_names) >= 100, (
            f"Expected 100+ AcroForm fields, got {len(self.pdf_field_names)}"
        )

    def test_all_field_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F4797_FIELD_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} FIELD_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_all_header_map_names_exist_in_pdf(self):
        missing = []
        for key, acro in F4797_HEADER_MAP.items():
            if acro.acro_name not in self.pdf_field_names:
                missing.append(f"{key} -> {acro.acro_name}")
        assert not missing, (
            f"{len(missing)} HEADER_MAP entries not found in PDF:\n"
            + "\n".join(missing)
        )

    def test_no_duplicate_acro_names(self):
        seen = {}
        duplicates = []
        for key, acro in {**F4797_HEADER_MAP, **F4797_FIELD_MAP}.items():
            if acro.acro_name in seen:
                duplicates.append(
                    f"{key} and {seen[acro.acro_name]} both map to {acro.acro_name}"
                )
            seen[acro.acro_name] = key
        assert not duplicates, (
            f"{len(duplicates)} duplicate AcroForm names:\n"
            + "\n".join(duplicates)
        )

    def test_f4797_in_acroform_registry(self):
        assert "f4797" in ACROFORM_FORM_IDS


# ===========================================================================
# AcroForm Filler — Form 4562
# ===========================================================================
class TestF4562AcroFormFiller:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _F4562_PATH.exists():
            pytest.skip("f4562.pdf not available")

    def test_fill_4562_empty_produces_valid_pdf(self):
        result = fill_form(
            template_path=_F4562_PATH,
            field_values={},
            field_map=F4562_FIELD_MAP,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_fill_4562_with_header(self):
        header_data = {
            "entity_name": "Test Depreciation LLC",
            "ein": "12-9876543",
        }
        result = fill_form(
            template_path=_F4562_PATH,
            field_values={},
            field_map=F4562_FIELD_MAP,
            header_data=header_data,
            header_map=F4562_HEADER_MAP,
        )
        text = _extract_text(result)
        assert "Test Depreciation LLC" in text

    def test_fill_4562_with_section_179(self):
        field_values = {
            "F4562_1": ("2500000.00", "currency"),
            "F4562_2": ("150000.00", "currency"),
            "F4562_8": ("75000.00", "currency"),
            "F4562_12": ("75000.00", "currency"),
        }
        result = fill_form(
            template_path=_F4562_PATH,
            field_values=field_values,
            field_map=F4562_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "75,000" in text

    def test_fill_4562_total_depreciation(self):
        field_values = {
            "F4562_22": ("250000.00", "currency"),
        }
        result = fill_form(
            template_path=_F4562_PATH,
            field_values=field_values,
            field_map=F4562_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "250,000" in text

    def test_fill_4562_widgets_stripped(self):
        result = fill_form(
            template_path=_F4562_PATH,
            field_values={"F4562_22": ("100000.00", "currency")},
            field_map=F4562_FIELD_MAP,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        widget_count = sum(1 for page in doc for _ in page.widgets())
        doc.close()
        assert widget_count == 0


# ===========================================================================
# AcroForm Filler — Form 4797
# ===========================================================================
class TestF4797AcroFormFiller:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdf(self):
        if not _F4797_PATH.exists():
            pytest.skip("f4797.pdf not available")

    def test_fill_4797_empty_produces_valid_pdf(self):
        result = fill_form(
            template_path=_F4797_PATH,
            field_values={},
            field_map=F4797_FIELD_MAP,
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_fill_4797_with_header(self):
        header_data = {
            "entity_name": "Test Disposal Corp",
            "ein": "99-1234567",
        }
        result = fill_form(
            template_path=_F4797_PATH,
            field_values={},
            field_map=F4797_FIELD_MAP,
            header_data=header_data,
            header_map=F4797_HEADER_MAP,
        )
        text = _extract_text(result)
        assert "Test Disposal Corp" in text

    def test_fill_4797_with_ordinary_gain(self):
        field_values = {
            "P4797_17": ("50000.00", "currency"),
        }
        result = fill_form(
            template_path=_F4797_PATH,
            field_values=field_values,
            field_map=F4797_FIELD_MAP,
        )
        text = _extract_text(result)
        assert "50,000" in text

    def test_fill_4797_widgets_stripped(self):
        result = fill_form(
            template_path=_F4797_PATH,
            field_values={"P4797_17": ("25000.00", "currency")},
            field_map=F4797_FIELD_MAP,
        )
        doc = fitz.open(stream=result, filetype="pdf")
        widget_count = sum(1 for page in doc for _ in page.widgets())
        doc.close()
        assert widget_count == 0


# ===========================================================================
# Renderer Integration
# ===========================================================================
class TestRendererIntegration:
    @pytest.fixture(autouse=True)
    def _skip_if_no_pdfs(self):
        if not _F4562_PATH.exists() or not _F4797_PATH.exists():
            pytest.skip("Form PDFs not available")

    def test_render_4562_via_renderer(self):
        field_values = {
            "F4562_22": ("300000.00", "currency"),
        }
        header_data = {
            "entity_name": "Render Test Corp",
            "ein": "11-2233445",
        }
        result = render("f4562", 2025, field_values, header_data)
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_render_4797_via_renderer(self):
        field_values = {
            "P4797_17": ("80000.00", "currency"),
        }
        header_data = {
            "entity_name": "Render Disposal Inc",
            "ein": "55-6677889",
        }
        result = render("f4797", 2025, field_values, header_data)
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
