"""
AcroForm field mapping definitions for IRS fillable PDFs.

Each form module defines FIELD_MAP and HEADER_MAP dictionaries that map
our internal line_number / header keys to the AcroForm field names in
the official IRS fillable PDF.

Field map files are named {form_id}_{tax_year}.py (e.g., f1120s_2025.py).
Use get_field_maps(form_id, tax_year) to resolve the correct maps.

Adding a new form:
    1. Run: python scripts/dump_acroform_fields.py resources/irs_forms/<year>/<form>.pdf --json
    2. Create field_maps/<form_id>_<year>.py with FIELD_MAP and HEADER_MAP
    3. Register in renderer.py ACROFORM_REGISTRY
    4. Run validation tests
"""

import importlib
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AcroField:
    """Mapping from our internal key to an IRS AcroForm field.

    Attributes:
        acro_name: Full AcroForm field name from the IRS PDF
            (e.g., "topmostSubform[0].Page1[0].f1_15[0]")
        field_type: How to set the value — "text" or "checkbox"
        format: How to format the value before setting it.
            "currency" -> comma-separated, negatives in parens
            "text" -> as-is
            "boolean" -> "X" for text fields, on_state for checkboxes
            "percentage" -> "12.5%"
            "integer" -> as-is (no commas)
    """
    acro_name: str
    field_type: Literal["text", "checkbox"] = "text"
    format: Literal["currency", "text", "boolean", "percentage", "integer"] = "text"


# Type alias for field maps
FieldMap = dict[str, AcroField]


def get_field_maps(form_id: str, tax_year: int) -> tuple[FieldMap, FieldMap]:
    """Resolve (FIELD_MAP, HEADER_MAP) for a form + tax year.

    Looks for a module named field_maps/{form_id}_{tax_year}.py.
    Raises ValueError if no matching module exists.

    Returns:
        Tuple of (FIELD_MAP, HEADER_MAP).
    """
    module_name = f"apps.tts_forms.field_maps.{form_id}_{tax_year}"
    try:
        mod = importlib.import_module(module_name)
    except ModuleNotFoundError:
        raise ValueError(
            f"No field map module for form_id={form_id!r}, tax_year={tax_year}. "
            f"Expected module: {module_name}"
        )
    return mod.FIELD_MAP, getattr(mod, "HEADER_MAP", {})
