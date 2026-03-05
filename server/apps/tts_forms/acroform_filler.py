"""
AcroForm-based PDF field filler.

Fills IRS fillable PDF forms by setting AcroForm field values using pymupdf.
This replaces the coordinate-overlay approach for forms that have AcroForm fields.

Usage:
    from apps.tts_forms.acroform_filler import fill_form
    from apps.tts_forms.field_maps.f1120s import FIELD_MAP, HEADER_MAP

    pdf_bytes = fill_form(
        template_path="resources/irs_forms/2025/f1120s.pdf",
        field_values={"1a": ("150000.00", "currency"), ...},
        field_map=FIELD_MAP,
        header_data={"entity_name": "Test Corp", "ein": "12-3456789"},
        header_map=HEADER_MAP,
    )
"""

import logging
from pathlib import Path

import fitz  # pymupdf

from .field_maps import AcroField, FieldMap
from .formatting import format_value, is_truthy

logger = logging.getLogger(__name__)

# pymupdf field flag for read-only
PDF_FIELD_IS_READ_ONLY = 1


def _build_pending_values(
    field_values: dict[str, tuple[str, str]],
    field_map: FieldMap,
    header_data: dict[str, str] | None,
    header_map: FieldMap | None,
) -> dict[str, tuple[str, AcroField]]:
    """Build a lookup: {acro_field_name: (display_value, AcroField)}.

    Merges header fields and form line values into one dict keyed by
    the AcroForm field name. Values are pre-formatted for display.
    This is built BEFORE iterating pages so we can match widgets inline.
    """
    pending: dict[str, tuple[str, AcroField]] = {}

    # Header fields (entity name, EIN, address, etc.)
    if header_data and header_map:
        for key, acro in header_map.items():
            value = header_data.get(key, "")
            if not value:
                continue
            # Header values are already display-formatted strings
            pending[acro.acro_name] = (value, acro)

    # Form line values (income, deductions, Schedule K, etc.)
    for line_number, acro in field_map.items():
        entry = field_values.get(line_number)
        if not entry:
            continue
        raw_value, field_type = entry
        if not raw_value or raw_value.strip() == "":
            continue

        if acro.field_type == "checkbox":
            # Checkboxes: pass raw value through (handled in page loop)
            pending[acro.acro_name] = (raw_value, acro)
        else:
            # Text fields: format for display
            fmt = acro.format if acro.format != "text" else field_type
            formatted = format_value(raw_value, fmt)
            if formatted:
                pending[acro.acro_name] = (formatted, acro)

    return pending


def fill_form(
    template_path: str | Path,
    field_values: dict[str, tuple[str, str]],
    field_map: FieldMap,
    header_data: dict[str, str] | None = None,
    header_map: FieldMap | None = None,
    flatten: bool = True,
) -> bytes:
    """
    Fill an IRS AcroForm PDF with values and return the result.

    Iterates pages and fills widgets inline (never stores widget references
    across pages) to avoid pymupdf's "Annot is not bound to a page" error.

    Args:
        template_path: Path to the fillable IRS PDF template.
        field_values: {line_number: (raw_value, field_type)} from the database.
        field_map: {line_number: AcroField} mapping our keys to AcroForm names.
        header_data: {field_name: display_value} for entity/header info.
        header_map: {field_name: AcroField} for header field names.
        flatten: If True, set fields to read-only after filling.

    Returns:
        Filled PDF as bytes.
    """
    doc = fitz.open(str(template_path))

    # Pre-compute all values keyed by AcroForm field name
    pending = _build_pending_values(field_values, field_map, header_data, header_map)

    filled_count = 0
    missing_names = []

    # Iterate pages and fill widgets inline (widgets stay bound to their page)
    for page in doc:
        for widget in page.widgets():
            fname = widget.field_name

            # Clear purple/blue highlight on ALL widgets (IRS fillable PDF default)
            try:
                widget.fill_color = None
                if fname not in pending:
                    widget.update()
                    continue
            except Exception:
                if fname not in pending:
                    continue

            value, acro = pending[fname]

            try:
                if acro.field_type == "checkbox":
                    if is_truthy(value):
                        on_state = widget.on_state()
                        widget.field_value = on_state if on_state else True
                    else:
                        widget.field_value = "Off"
                else:
                    widget.field_value = value
                widget.update()
                filled_count += 1
            except Exception as e:
                logger.warning("Failed to set %r to %r: %s", fname, value, e)

    # Check for pending values that had no matching widget
    all_widget_names = set()
    for page in doc:
        for widget in page.widgets():
            all_widget_names.add(widget.field_name)

    for acro_name in pending:
        if acro_name not in all_widget_names:
            missing_names.append(acro_name)

    if missing_names:
        logger.info(
            "Filled %d fields; %d AcroForm names not found in PDF: %s",
            filled_count, len(missing_names), missing_names[:5]
        )
    else:
        logger.info("Filled %d fields (all matched)", filled_count)

    # Flatten: set all filled widgets to read-only
    if flatten:
        for page in doc:
            for widget in page.widgets():
                if widget.field_value and widget.field_value != "Off":
                    widget.field_flags = widget.field_flags | PDF_FIELD_IS_READ_ONLY
                    widget.update()

    return doc.tobytes(deflate=True)
