"""
IRS Form PDF Renderer.

Renders tax return data onto official IRS PDF templates by creating
transparent overlay pages with ReportLab and merging them with the
template PDF using pypdf.

Usage:
    from apps.tts_forms.renderer import render
    pdf_bytes = render(form_id="f1120s", tax_year=2025, data=return_data)

    # Or render from a TaxReturn model instance:
    from apps.tts_forms.renderer import render_tax_return
    pdf_bytes = render_tax_return(tax_return)
"""

import io
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch  # noqa: F401 — useful for callers
from reportlab.pdfgen import canvas

from .coordinates.f1120s import FIELD_MAP as F1120S_FIELD_MAP
from .coordinates.f1120s import HEADER_FIELDS as F1120S_HEADER_FIELDS
from .coordinates.f1120s import FieldCoord
from .statements import render_statement_pages

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Path from project root (server/../resources/irs_forms)
_SERVER_DIR = Path(__file__).resolve().parent.parent.parent
_REPO_ROOT = _SERVER_DIR.parent
RESOURCES_DIR = _REPO_ROOT / "resources" / "irs_forms"
MANIFEST_PATH = RESOURCES_DIR / "forms_manifest.json"

# Coordinate maps keyed by form_id
COORDINATE_REGISTRY: dict[str, dict[str, FieldCoord]] = {
    "f1120s": F1120S_FIELD_MAP,
}

HEADER_REGISTRY: dict[str, dict[str, FieldCoord]] = {
    "f1120s": F1120S_HEADER_FIELDS,
}

# Font settings
DEFAULT_FONT = "Courier"
DEFAULT_FONT_SIZE = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_template_path(form_id: str, tax_year: int) -> Path:
    """Resolve the local path of an IRS PDF template."""
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    for entry in manifest.get("forms", []):
        if entry["form_id"] == form_id and entry["tax_year"] == tax_year:
            return RESOURCES_DIR / entry["local_path"]

    raise FileNotFoundError(
        f"No manifest entry for form_id={form_id!r}, tax_year={tax_year}"
    )


def _format_currency(value: str) -> str:
    """Format a numeric string as currency for display on the form."""
    if not value or value.strip() == "":
        return ""
    try:
        d = Decimal(value)
    except InvalidOperation:
        return value
    if d == 0:
        return ""
    # Negative amounts in parentheses per IRS convention
    if d < 0:
        return f"({abs(d):,.0f})"
    return f"{d:,.0f}"


def _format_value(value: str, field_type: str) -> str:
    """Format a field value based on its type."""
    if field_type == "currency":
        return _format_currency(value)
    if field_type == "boolean":
        return "X" if value.lower() in ("true", "yes", "1", "x") else ""
    if field_type == "percentage":
        if not value:
            return ""
        try:
            return f"{Decimal(value):.1f}%"
        except InvalidOperation:
            return value
    # text, integer — return as-is
    return value


def _create_overlay(
    field_values: dict[str, tuple[str, str]],
    field_map: dict[str, FieldCoord],
    header_data: dict[str, str] | None,
    header_map: dict[str, FieldCoord] | None,
    page_count: int,
) -> io.BytesIO:
    """
    Create a multi-page transparent overlay PDF using ReportLab.

    field_values: {line_number: (raw_value, field_type)}
    field_map: {line_number: FieldCoord}
    header_data: {field_name: display_value} for entity info
    header_map: {field_name: FieldCoord} for entity info positions
    page_count: number of pages in the template PDF
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    for page_idx in range(page_count):
        # Draw header fields on the appropriate page
        if header_data and header_map:
            for field_name, coord in header_map.items():
                if coord.page != page_idx:
                    continue
                text = header_data.get(field_name, "")
                if not text:
                    continue
                c.setFont(DEFAULT_FONT, coord.font_size)
                if coord.alignment == "right":
                    c.drawRightString(coord.x + coord.width, coord.y, text)
                elif coord.alignment == "center":
                    c.drawCentredString(
                        coord.x + coord.width / 2, coord.y, text
                    )
                else:
                    c.drawString(coord.x, coord.y, text)

        # Draw form field values on the appropriate page
        for line_number, coord in field_map.items():
            if coord.page != page_idx:
                continue
            entry = field_values.get(line_number)
            if not entry:
                continue
            raw_value, field_type = entry
            text = _format_value(raw_value, field_type)
            if not text:
                continue

            c.setFont(DEFAULT_FONT, coord.font_size)
            if coord.alignment == "right":
                c.drawRightString(coord.x + coord.width, coord.y, text)
            elif coord.alignment == "center":
                c.drawCentredString(
                    coord.x + coord.width / 2, coord.y, text
                )
            else:
                c.drawString(coord.x, coord.y, text)

        c.showPage()

    c.save()
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render(
    form_id: str,
    tax_year: int,
    field_values: dict[str, tuple[str, str]],
    header_data: dict[str, str] | None = None,
    statement_pages: list[dict] | None = None,
) -> bytes:
    """
    Render a completed IRS form PDF.

    Args:
        form_id: Manifest form identifier (e.g., "f1120s").
        tax_year: Tax year (e.g., 2025).
        field_values: Dict mapping line_number to (raw_value, field_type).
        header_data: Optional dict with entity info (name, address, EIN).
        statement_pages: Optional list of statement page dicts:
            [{"title": "...", "form_code": "...", "items": [...]}]

    Returns:
        PDF file content as bytes.
    """
    field_map = COORDINATE_REGISTRY.get(form_id)
    if not field_map:
        raise ValueError(f"No coordinate map registered for form_id={form_id!r}")

    template_path = _get_template_path(form_id, tax_year)
    if not template_path.exists():
        raise FileNotFoundError(
            f"IRS PDF template not found at {template_path}. "
            f"Run scripts/update_irs_forms.py to download."
        )

    header_map = HEADER_REGISTRY.get(form_id)

    # Read template PDF
    template_reader = PdfReader(str(template_path))
    page_count = len(template_reader.pages)

    # Create overlay
    overlay_buf = _create_overlay(
        field_values=field_values,
        field_map=field_map,
        header_data=header_data,
        header_map=header_map,
        page_count=page_count,
    )
    overlay_reader = PdfReader(overlay_buf)

    # Merge overlay onto template
    writer = PdfWriter()
    for i in range(page_count):
        template_page = template_reader.pages[i]
        if i < len(overlay_reader.pages):
            overlay_page = overlay_reader.pages[i]
            template_page.merge_page(overlay_page)
        writer.add_page(template_page)

    # Append statement pages if provided
    if statement_pages:
        stmt_bytes = render_statement_pages(statement_pages)
        if stmt_bytes:
            stmt_reader = PdfReader(io.BytesIO(stmt_bytes))
            for page in stmt_reader.pages:
                writer.add_page(page)

    # Write final PDF
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def render_tax_return(tax_return, statement_items: dict | None = None) -> bytes:
    """
    Render a TaxReturn model instance to PDF.

    Args:
        tax_return: A TaxReturn model instance (with field_values prefetched).
        statement_items: Optional dict mapping line_number to list of
            detail items for supporting statements. Each item is a dict
            with at minimum {"description": str, "amount": str}.
            Example: {"19": [{"description": "Office supplies", "amount": "1200.00"}, ...]}

    Returns:
        PDF file content as bytes.
    """
    from apps.returns.models import FormFieldValue

    form_code = tax_return.form_definition.code

    # Map form_code to form_id
    form_code_to_id = {
        "1120-S": "f1120s",
    }
    form_id = form_code_to_id.get(form_code)
    if not form_id:
        raise ValueError(f"No PDF renderer registered for form code {form_code!r}")

    tax_year = tax_return.form_definition.tax_year_applicable

    # Load field values
    fvs = (
        FormFieldValue.objects.filter(tax_return=tax_return)
        .select_related("form_line")
    )
    field_values: dict[str, tuple[str, str]] = {}
    for fv in fvs:
        field_values[fv.form_line.line_number] = (
            fv.value,
            fv.form_line.field_type,
        )

    # Build header data from the tax_year's entity/client
    header_data = _build_header_data(tax_return)

    # Build statement pages for lines with detail items
    statement_pages = []
    if statement_items:
        form_display = f"Form {form_code} ({tax_year})"
        for line_number, items in statement_items.items():
            # Look up the line label
            line_label = ""
            for fv in fvs:
                if fv.form_line.line_number == line_number:
                    line_label = fv.form_line.label
                    break
            statement_pages.append({
                "title": f"{form_display} — Statement for Line {line_number}",
                "subtitle": line_label,
                "form_code": form_code,
                "items": items,
            })

    return render(
        form_id=form_id,
        tax_year=tax_year,
        field_values=field_values,
        header_data=header_data,
        statement_pages=statement_pages or None,
    )


def _build_header_data(tax_return) -> dict[str, str]:
    """Extract header/entity info from a TaxReturn for the form header."""
    tax_year = tax_return.tax_year
    entity = tax_year.entity
    client = entity.client

    # Build entity name: use entity name or fall back to client name
    entity_name = entity.name or client.name

    header = {
        "entity_name": entity_name,
    }

    # Add address fields if available on the entity/client model
    for attr in ("address_street", "address_city_state_zip", "ein"):
        val = getattr(entity, attr, None) or getattr(client, attr, None)
        if val:
            header[attr] = str(val)

    # Tax year dates
    header["tax_year_begin"] = f"01/01/{tax_year.year}"
    header["tax_year_end"] = f"12/31/{tax_year.year}"

    return header
