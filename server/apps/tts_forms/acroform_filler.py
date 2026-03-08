"""
AcroForm-positioned PDF text overlay.

Extracts field positions from IRS fillable PDF AcroForm widgets, then renders
values as a ReportLab text overlay merged onto a flattened copy of the template.
This avoids AcroForm appearance stream issues (doubled/missing borders) by not
modifying form fields at all — text is drawn directly onto the page.

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

import io
import logging
from pathlib import Path

import fitz  # pymupdf — used only to extract widget positions
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from .field_maps import AcroField, FieldMap
from .formatting import format_value, is_truthy

logger = logging.getLogger(__name__)

# Font settings (matches coordinate overlay approach)
DEFAULT_FONT = "Courier"
DEFAULT_FONT_SIZE = 10

# Small margin inside field edges (pts)
_FIELD_MARGIN = 2


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
            # Checkboxes: pass raw value through (handled in overlay loop)
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
    Fill an IRS PDF by overlaying text at AcroForm field positions.

    Extracts widget positions from the fillable template using pymupdf,
    strips all AcroForm widgets, then draws values as a ReportLab text
    overlay merged onto the clean template via pypdf.

    Args:
        template_path: Path to the fillable IRS PDF template.
        field_values: {line_number: (raw_value, field_type)} from the database.
        field_map: {line_number: AcroField} mapping our keys to AcroForm names.
        header_data: {field_name: display_value} for entity/header info.
        header_map: {field_name: AcroField} for header field names.
        flatten: Ignored (kept for API compatibility). Widgets are always
            stripped from the output.

    Returns:
        Filled PDF as bytes.
    """
    # --- 1. Extract widget positions from the fillable PDF ---
    doc = fitz.open(str(template_path))
    widget_positions: dict[str, tuple[int, tuple, float]] = {}
    page_sizes: list[tuple[float, float]] = []

    for page_idx, page in enumerate(doc):
        page_sizes.append((page.rect.width, page.rect.height))
        for widget in page.widgets():
            fs = widget.text_fontsize
            if not fs or fs <= 0:
                fs = DEFAULT_FONT_SIZE
            # Store rect as plain tuple (x0, y0, x1, y1) — pymupdf y from top
            widget_positions[widget.field_name] = (
                page_idx,
                (widget.rect.x0, widget.rect.y0, widget.rect.x1, widget.rect.y1),
                fs,
            )

    page_count = len(doc)
    doc.close()

    # --- 2. Pre-format all values keyed by AcroForm field name ---
    pending = _build_pending_values(field_values, field_map, header_data, header_map)

    # --- 3. Flatten template (strip AcroForm widgets, keep printed grid lines) ---
    writer = PdfWriter()
    for page in PdfReader(str(template_path)).pages:
        writer.add_page(page)
    writer.remove_annotations(subtypes="/Widget")
    flat_buf = io.BytesIO()
    writer.write(flat_buf)
    flat_buf.seek(0)
    flat_reader = PdfReader(flat_buf)

    # --- 4. Create ReportLab text overlay at widget positions ---
    overlay_buf = io.BytesIO()
    c = canvas.Canvas(overlay_buf)
    filled_count = 0

    for page_idx in range(page_count):
        page_w, page_h = page_sizes[page_idx]
        c.setPageSize((page_w, page_h))

        for acro_name, (display_value, acro) in pending.items():
            pos = widget_positions.get(acro_name)
            if not pos:
                continue
            w_page, rect, font_size = pos
            if w_page != page_idx:
                continue

            x0, y0_mu, x1, y1_mu = rect  # pymupdf: y0=top edge, y1=bottom edge

            if acro.field_type == "checkbox":
                if is_truthy(display_value):
                    # Draw "X" centered in the checkbox box
                    box_h = y1_mu - y0_mu
                    chk_fs = max(box_h * 0.75, 6)
                    c.setFont(DEFAULT_FONT, chk_fs)
                    cx = (x0 + x1) / 2
                    # Center vertically: convert center to RL, adjust for baseline
                    cy = page_h - (y0_mu + y1_mu) / 2 - chk_fs * 0.3
                    c.drawCentredString(cx, cy, "X")
                    filled_count += 1
            else:
                # Text field — draw at baseline near bottom of field
                c.setFont(DEFAULT_FONT, font_size)
                baseline_y = page_h - y1_mu + _FIELD_MARGIN

                if acro.format == "currency":
                    # Right-align currency values
                    c.drawRightString(x1 - _FIELD_MARGIN, baseline_y, display_value)
                else:
                    # Left-align text values
                    c.drawString(x0 + _FIELD_MARGIN, baseline_y, display_value)
                filled_count += 1

        c.showPage()

    c.save()
    overlay_buf.seek(0)

    # --- 5. Merge overlay onto flattened template ---
    overlay_reader = PdfReader(overlay_buf)
    result_writer = PdfWriter()
    for i in range(page_count):
        page = flat_reader.pages[i]
        if i < len(overlay_reader.pages):
            page.merge_page(overlay_reader.pages[i])
        result_writer.add_page(page)

    output = io.BytesIO()
    result_writer.write(output)

    # --- Log results ---
    missing = [n for n in pending if n not in widget_positions]
    if missing:
        logger.info(
            "Filled %d fields; %d AcroForm names not found in PDF: %s",
            filled_count, len(missing), missing[:5],
        )
    else:
        logger.info("Filled %d fields (all matched)", filled_count)

    return output.getvalue()
