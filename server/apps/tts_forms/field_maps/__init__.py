"""
AcroForm field mapping definitions for IRS fillable PDFs.

Each form module defines FIELD_MAP and HEADER_MAP dictionaries that map
our internal line_number / header keys to the AcroForm field names in
the official IRS fillable PDF.

Usage:
    from apps.tts_forms.field_maps.f1120s import FIELD_MAP, HEADER_MAP

Adding a new form:
    1. Run: python scripts/dump_acroform_fields.py resources/irs_forms/2025/<form>.pdf --json
    2. Create field_maps/<form_id>.py with FIELD_MAP and HEADER_MAP
    3. Register in renderer.py ACROFORM_REGISTRY
    4. Run validation tests
"""

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
