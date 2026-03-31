"""
IRS Form PDF Renderer.

Supports two rendering backends:
1. AcroForm filling (preferred) — fills named fields in IRS fillable PDFs using pymupdf
2. Coordinate overlay (legacy) — draws text at pixel positions using ReportLab + pypdf

The renderer auto-selects the backend based on ACROFORM_FORM_IDS. Forms registered
there use AcroForm filling; all others fall back to coordinate overlay.

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

# Coordinate-based rendering (legacy fallback)
from .coordinates.f1065 import FIELD_MAP as F1065_FIELD_MAP
from .coordinates.f1065 import HEADER_FIELDS as F1065_HEADER_FIELDS
from .coordinates.f1120 import FIELD_MAP as F1120_FIELD_MAP
from .coordinates.f1120 import HEADER_FIELDS as F1120_HEADER_FIELDS
from .coordinates.f1120s import FIELD_MAP as F1120S_COORD_FIELD_MAP
from .coordinates.f1120s import HEADER_FIELDS as F1120S_COORD_HEADER_FIELDS
from .coordinates.f1120s import FieldCoord
from .coordinates.f1120sk1 import K1_FIELD_MAP as F1120SK1_FIELD_MAP
from .coordinates.f1120sk1 import K1_HEADER as F1120SK1_HEADER
from .coordinates.f7206 import FIELD_MAP as F7206_FIELD_MAP
from .coordinates.f7206 import HEADER_FIELDS as F7206_HEADER_FIELDS
from .coordinates.f1125a import FIELD_MAP as F1125A_FIELD_MAP
from .coordinates.f1125a import HEADER_FIELDS as F1125A_HEADER_FIELDS
from .coordinates.f7004 import FIELD_MAP as F7004_FIELD_MAP
from .coordinates.f7004 import HEADER_FIELDS as F7004_HEADER_FIELDS
from .coordinates.f7203 import FIELD_MAP as F7203_FIELD_MAP
from .coordinates.f7203 import HEADER_FIELDS as F7203_HEADER_FIELDS
from .coordinates.f8825 import (
    FIELD_MAP as F8825_FIELD_MAP,
    HEADER_FIELDS as F8825_HEADER_FIELDS,
    PROPERTY_FIELDS as F8825_PROPERTY_FIELDS,
)
# GA-600S AcroForm path (migrated from coordinate overlay via AcroForm Creator tool)
# Legacy coordinate imports kept commented for reference during migration validation:
# from .coordinates.fga600s import FIELD_MAP as FGA600S_FIELD_MAP
# from .coordinates.fga600s import HEADER_FIELDS as FGA600S_HEADER_FIELDS

# AcroForm-based rendering (new, preferred)
from .acroform_filler import fill_form as _acroform_fill
from .field_maps import get_field_maps as _get_field_maps
from .formatting import expand_yes_no, format_currency, format_value

# Native generation retired — kept for reference but no longer called
# from .ga600s_native import render_ga600s_native
from .invoice import render_invoice
from .letter import render_letter
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
    "f1120s": F1120S_COORD_FIELD_MAP,
    "f1065": F1065_FIELD_MAP,
    "f1120": F1120_FIELD_MAP,
    "f1120sk1": F1120SK1_FIELD_MAP,
    "f7206": F7206_FIELD_MAP,
    "f1125a": F1125A_FIELD_MAP,
    "f8825": F8825_FIELD_MAP,
    "f7203": F7203_FIELD_MAP,
    "f7004": F7004_FIELD_MAP,
}

HEADER_REGISTRY: dict[str, dict[str, FieldCoord]] = {
    "f1120s": F1120S_COORD_HEADER_FIELDS,
    "f1065": F1065_HEADER_FIELDS,
    "f1120": F1120_HEADER_FIELDS,
    "f1120sk1": F1120SK1_HEADER,
    "f7206": F7206_HEADER_FIELDS,
    "f1125a": F1125A_HEADER_FIELDS,
    "f8825": F8825_HEADER_FIELDS,
    "f7203": F7203_HEADER_FIELDS,
    "f7004": F7004_HEADER_FIELDS,
}

# AcroForm-capable form IDs — field maps resolved dynamically via get_field_maps()
ACROFORM_FORM_IDS: set[str] = {
    "f1120s", "f1120sk1", "f7004", "f8879s", "f8453s", "f1125a", "f8825", "f7203",
    "f4797", "f1120ssd", "f8949", "f1125e", "f4562",
}

# Form code → 2-digit IRS extension code for Form 7004 Line 1
EXTENSION_FORM_CODES: dict[str, str] = {
    "1120-S": "25",
    "1065": "09",
    "1120": "12",
}

# Font settings
DEFAULT_FONT = "Courier-Bold"
DEFAULT_FONT_SIZE = 10

# Data text color for on-screen vs print
DATA_COLOR_BLACK = (0, 0, 0)
DATA_COLOR_BLUE = (0.0, 0.0, 0.75)

import contextvars
_screen_mode_ctx: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "screen_mode", default=False,
)


def _data_color(screen_mode: bool | None = None) -> tuple[float, float, float]:
    """Return RGB tuple for data text — blue on screen, black for print.

    If screen_mode is not explicitly passed, reads from the context variable
    (set by render_complete_return or render).
    """
    if screen_mode is None:
        screen_mode = _screen_mode_ctx.get(False)
    return DATA_COLOR_BLUE if screen_mode else DATA_COLOR_BLACK


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _flatten_template(reader: PdfReader) -> PdfReader:
    """Strip fillable form field widgets (purple backgrounds) from an IRS PDF.

    IRS templates contain AcroForm widgets that render as purple/blue boxes.
    This removes those annotations so the overlay prints on a clean background.
    """
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.remove_annotations(subtypes="/Widget")
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return PdfReader(buf)


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



def _create_overlay(
    field_values: dict[str, tuple[str, str]],
    field_map: dict[str, FieldCoord],
    header_data: dict[str, str] | None,
    header_map: dict[str, FieldCoord] | None,
    page_count: int,
    screen_mode: bool = False,
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
    c.setFillColorRGB(*_data_color(screen_mode))

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
            text = format_value(raw_value, field_type)
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
    screen_mode: bool = False,
) -> bytes:
    """
    Render a completed IRS form PDF.

    Auto-selects the rendering backend:
    - AcroForm filling (preferred): if the form is in ACROFORM_FORM_IDS
    - Coordinate overlay (legacy): fallback for forms without AcroForm maps

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
    # Only set context var if explicitly passed (don't overwrite parent's setting)
    if screen_mode:
        _screen_mode_ctx.set(screen_mode)
    template_path = _get_template_path(form_id, tax_year)
    if not template_path.exists():
        raise FileNotFoundError(
            f"IRS PDF template not found at {template_path}. "
            f"Run scripts/update_irs_forms.py to download."
        )

    # --- Try AcroForm path first (preferred) ---
    form_bytes = None
    if form_id in ACROFORM_FORM_IDS:
        try:
            acro_field_map, acro_header_map = _get_field_maps(form_id, tax_year)
            form_bytes = _acroform_fill(
                template_path=template_path,
                field_values=field_values,
                field_map=acro_field_map,
                header_data=header_data,
                header_map=acro_header_map or None,
                screen_mode=screen_mode,
            )
        except ValueError:
            pass  # Fall through to coordinate overlay

    # --- Coordinate overlay fallback ---
    if form_bytes is None:
        coord_field_map = COORDINATE_REGISTRY.get(form_id)
        if not coord_field_map:
            raise ValueError(
                f"No AcroForm or coordinate map registered for form_id={form_id!r}"
            )

        header_map = HEADER_REGISTRY.get(form_id)

        # Read template PDF and strip fillable form field widgets
        template_reader = _flatten_template(PdfReader(str(template_path)))
        page_count = len(template_reader.pages)

        # Create overlay
        overlay_buf = _create_overlay(
            field_values=field_values,
            field_map=coord_field_map,
            header_data=header_data,
            header_map=header_map,
            page_count=page_count,
            screen_mode=screen_mode,
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

        buf = io.BytesIO()
        writer.write(buf)
        form_bytes = buf.getvalue()

    # Append statement pages if provided (works for both paths)
    if statement_pages:
        stmt_bytes = render_statement_pages(statement_pages)
        if stmt_bytes:
            writer = PdfWriter()
            form_reader = PdfReader(io.BytesIO(form_bytes))
            for page in form_reader.pages:
                writer.add_page(page)
            stmt_reader = PdfReader(io.BytesIO(stmt_bytes))
            for page in stmt_reader.pages:
                writer.add_page(page)
            output = io.BytesIO()
            writer.write(output)
            return output.getvalue()

    return form_bytes


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

    # GA-600S uses coordinate overlay on official GA DOR template
    if form_code == "GA-600S":
        return render_ga600s_overlay(tax_return)

    # Map form_code to form_id
    form_code_to_id = {
        "1120-S": "f1120s",
        "1065": "f1065",
        "1120": "f1120",
        "4797": "f4797",
        "1120-S-SD": "f1120ssd",
        "8949": "f8949",
        "1125-E": "f1125e",
        "4562": "f4562",
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

    # Expand Schedule B boolean fields into _yes / _no coordinate keys.
    # E.g. B3="true" → B3_yes="X"; B3="false" → B3_no="X".
    expand_yes_no(field_values)

    # Schedule B Line 1: Accounting method checkboxes
    # Added AFTER expand_yes_no so it won't be mangled by the B-prefix expansion.
    if tax_return.accounting_method == "cash":
        field_values["B1_cash"] = ("true", "boolean")
    elif tax_return.accounting_method == "accrual":
        field_values["B1_accrual"] = ("true", "boolean")

    # M-1 Lines 5 and 6: DB has sub-lines (M1_5a/M1_5b, M1_6a/M1_6b)
    # but the field map has M1_5 and M1_6 (totals). Synthesize totals for rendering.
    def _fv_decimal(key):
        val = field_values.get(key, ("", ""))[0]
        try:
            return Decimal(val) if val else ZERO
        except InvalidOperation:
            return ZERO

    m1_5_total = _fv_decimal("M1_5a") + _fv_decimal("M1_5b")
    if m1_5_total:
        field_values["M1_5"] = (str(m1_5_total), "currency")
    m1_6_total = _fv_decimal("M1_6a") + _fv_decimal("M1_6b")
    if m1_6_total:
        field_values["M1_6"] = (str(m1_6_total), "currency")

    # Schedule L 4-column line translation.
    # Seed FormLine line_numbers use L10a/L10b/L10d/L10e but the AcroForm
    # field map uses L10a_a/L10b_b/L10a_c/L10b_d (line + IRS column letter).
    # Re-key so the renderer finds the correct AcroForm widget.
    SCHED_L_4COL = {
        # Line 2: Trade notes / bad debts
        "L2a": "L2a_a", "L2d": "L2a_c",      # gross: BOY→col a, EOY→col c
        "L2b": "L2b_b", "L2e": "L2b_d",      # contra: BOY→col b, EOY→col d
        # Line 10: Buildings & depreciable assets / accumulated depreciation
        "L10a": "L10a_a", "L10d": "L10a_c",
        "L10b": "L10b_b", "L10e": "L10b_d",
        # Line 11: Depletable assets / accumulated depletion
        "L11a": "L11a_a", "L11d": "L11a_c",
        "L11b": "L11b_b", "L11e": "L11b_d",
        # Line 13: Intangible assets / accumulated amortization
        "L13a": "L13a_a", "L13d": "L13a_c",
        "L13b": "L13b_b", "L13e": "L13b_d",
    }
    for old_key, new_key in SCHED_L_4COL.items():
        if old_key in field_values:
            field_values[new_key] = field_values.pop(old_key)

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

    # Build entity name: use legal_name, fall back to name
    entity_name = entity.legal_name or entity.name

    header: dict[str, str] = {
        "entity_name": entity_name,
    }

    # Address fields from entity
    if entity.address_line1:
        header["address_street"] = entity.address_line1
    # Split city, state, zip into separate fields for precise positioning
    if entity.city:
        header["address_city"] = entity.city
    if entity.state:
        header["address_state"] = entity.state
    if entity.zip_code:
        header["address_zip"] = entity.zip_code

    if entity.ein:
        header["ein"] = entity.ein
    if entity.date_incorporated:
        header["date_incorporated"] = entity.date_incorporated.strftime("%m/%d/%Y")
    if entity.state_incorporated:
        header["state_incorporated"] = entity.state_incorporated

    # Tax year dates
    # NOTE: tax_year_begin intentionally omitted — calendar year forms
    # display "2025" pre-printed; only populate end date for fiscal year filers.
    if tax_return.tax_year_end:
        header["tax_year_end"] = tax_return.tax_year_end.strftime("%m/%d/%Y")
    else:
        header["tax_year_end"] = f"12/31/{tax_year.year}"

    # Page 1 header checkboxes (render "X" if True)
    if tax_return.is_final_return:
        header["chk_final_return"] = "X"
    if tax_return.is_name_change:
        header["chk_name_change"] = "X"
    if tax_return.is_address_change:
        header["chk_address_change"] = "X"
    if tax_return.is_amended_return:
        header["chk_amended_return"] = "X"

    # S election date
    if tax_return.s_election_date:
        header["s_election_date"] = tax_return.s_election_date.strftime("%m/%d/%Y")

    # Number of shareholders
    if tax_return.number_of_shareholders:
        header["number_of_shareholders"] = str(tax_return.number_of_shareholders)

    # Business activity code (IRS page 1, field B)
    if tax_return.business_activity_code:
        header["business_activity_code"] = tax_return.business_activity_code

    # Schedule B Line 2 — business activity description + product or service
    if entity.business_activity:
        header["B2_business_activity"] = entity.business_activity
    if tax_return.product_or_service:
        header["B2_product_service"] = tax_return.product_or_service

    # Total assets — pull from balance sheet L15d (end-of-year total assets)
    from apps.returns.models import FormFieldValue as _FFV

    try:
        l15d = _FFV.objects.filter(
            tax_return=tax_return, form_line__line_number="L15d"
        ).first()
        if l15d and l15d.value:
            header["total_assets"] = format_currency(l15d.value)
    except Exception:
        pass

    # Preparer info (if exists)
    try:
        prep = tax_return.preparer_info
        if prep.preparer_name:
            header["preparer_name"] = prep.preparer_name
            # IRS accepts printed preparer signature
            header["preparer_signature"] = prep.preparer_name
        if prep.ptin:
            header["preparer_ptin"] = prep.ptin
        if prep.signature_date:
            header["preparer_date"] = prep.signature_date.strftime("%m/%d/%Y")
        if prep.is_self_employed:
            header["preparer_self_employed"] = "X"
        if prep.firm_name:
            header["firm_name"] = prep.firm_name
        if prep.firm_ein:
            header["firm_ein"] = prep.firm_ein
        if prep.firm_phone:
            header["firm_phone"] = prep.firm_phone
        # Split firm address into separate fields for precise positioning
        if prep.firm_address:
            header["firm_street"] = prep.firm_address
        if prep.firm_city:
            header["firm_city"] = prep.firm_city
        if prep.firm_state:
            header["firm_state"] = prep.firm_state
        if prep.firm_zip:
            header["firm_zip"] = prep.firm_zip
    except Exception:
        pass  # No preparer info yet

    # Default: Yes, IRS may discuss with preparer (standard for most firms)
    # TODO: Add model field to make this configurable per return
    if "preparer_name" in header:
        header["chk_discuss_yes"] = "X"

    # Accounting method checkboxes (Page 1, Line I)
    if tax_return.accounting_method == "cash":
        header["chk_accounting_cash"] = "X"
    elif tax_return.accounting_method == "accrual":
        header["chk_accounting_accrual"] = "X"

    # GA-600S now uses native rendering (ga600s_native.py) — no header needed here

    return header


# ---------------------------------------------------------------------------
# Schedule K-1 rendering
# ---------------------------------------------------------------------------

# Maps Schedule K line_number → K-1 Part III field key(s)
# For simple lines, maps to a single amount field.
SCHED_K_TO_K1_MAP: dict[str, str] = {
    "K1": "1",
    "K2": "2",
    "K3": "3",
    "K4": "4",
    "K5a": "5a",
    "K5b": "5b",
    "K6": "6",
    "K7": "7",
    "K8a": "8a",
    "K8b": "8b",
    "K8c": "8c",
    "K9": "9",
    "K10": "10",
    "K11": "11",
}

# Coded-entry K-1 boxes: (Schedule K line, code letter, code_field, amount_field)
# K-1 Boxes 12, 13, 15, 16, 17 use code+amount pairs on the IRS form.
K12_ITEMS = [
    ("K12a", "A", "12_code", "12"),             # Charitable contributions
    ("K12b", "H", "12_code_2", "12_amt_2"),     # Investment interest expense
    ("K12c", "I", "12_code_3", "12_amt_3"),     # Section 59(e)(2) expenditures
    ("K12d", "L", "12_code_4", "12_amt_4"),     # Other deductions
]

K13_ITEMS = [
    ("K13a", "A", "13_code", "13"),             # Low-income housing (42(j)(5))
    ("K13b", "B", "13_code_2", "13_amt_2"),     # Low-income housing (other)
    ("K13c", "C", "13_code_3", "13_amt_3"),     # Qualified rehab expenditures
    ("K13d", "D", "13_code_4", "13_amt_4"),     # Other rental RE credits
    ("K13f", "F", "13_code_5", "13_amt_5"),     # Biofuel producer credit
]

K15_ITEMS = [
    ("K15a", "A", "15_code", "15"),             # Post-1986 depreciation adj
    ("K15b", "B", "15_code_2", "15_amt_2"),     # Adjusted gain or loss
    ("K15c", "C", "15_code_3", "15_amt_3"),     # Depletion
    ("K15d", "D", "15_code_4", "15_amt_4"),     # O&G gross income
    ("K15e", "E", "15_code_5", "15_amt_5"),     # O&G deductions
    ("K15f", "F", "15_code_6", "15_amt_6"),     # Other AMT items
]

K16_ITEMS = [
    ("K16a", "A", "16_code_1", "16_amt_1"),     # Tax-exempt interest
    ("K16b", "B", "16_code_2", "16_amt_2"),     # Other tax-exempt income
    ("K16c", "C", "16_code_3", "16_amt_3"),     # Nondeductible expenses
    ("K16d", "D", "16_code_4", "16_amt_4"),     # Distributions
]

# K17: row 1 reserved for health insurance (Code AC), other items start at row 2
K17_ITEMS = [
    ("K17a", "A", "17_code_2", "17_amt_2"),     # Investment income
    ("K17b", "B", "17_code_3", "17_amt_3"),     # Investment expenses
    ("K17c", "C", "17_code_4", "17_amt_4"),     # Dividend equivalents
]


def render_k1(tax_return, shareholder) -> bytes:
    """
    Render a single Schedule K-1 (Form 1120-S) for one shareholder.

    Part I: corporation info from entity.
    Part II: shareholder info from Shareholder model.
    Part III: Schedule K values × ownership_percentage / 100.
    Line 16d uses shareholder.distributions directly.
    Line 17 code AC added if health_insurance_premium > 0.
    """
    from apps.returns.models import FormFieldValue

    entity = tax_return.tax_year.entity
    year = tax_return.tax_year.year
    tax_year_applicable = tax_return.form_definition.tax_year_applicable
    ownership_pct = shareholder.ownership_percentage / Decimal("100")

    # ---- Part I + Part II header data ----
    city_state_zip = ", ".join(
        p for p in [entity.city, entity.state] if p
    )
    if entity.zip_code:
        city_state_zip += f" {entity.zip_code}"

    sh_city_state_zip = ", ".join(
        p for p in [shareholder.city, shareholder.state] if p
    )
    if shareholder.zip_code:
        sh_city_state_zip += f" {shareholder.zip_code}"

    # Build multi-line name+address strings for AcroForm fillable fields
    corp_name = entity.legal_name or entity.name
    corp_lines = [corp_name]
    if entity.address_line1:
        corp_lines.append(entity.address_line1)
    if city_state_zip:
        corp_lines.append(city_state_zip)

    sh_lines = [shareholder.name]
    if shareholder.address_line1:
        sh_lines.append(shareholder.address_line1)
    if sh_city_state_zip:
        sh_lines.append(sh_city_state_zip)

    header_data = {
        "corp_ein": entity.ein or "",
        "corp_name_address": "\n".join(corp_lines),
        "irs_center": "Ogden, UT",  # Default IRS center for S-Corps
        "corp_shares_boy": "",  # Filled from entity if tracked
        "corp_shares_eoy": "",
        # Tax year dates intentionally omitted — calendar year filers don't
        # populate the beginning/ending date fields on K-1.
        "sh_ssn": shareholder.ssn or "",
        "sh_name_address": "\n".join(sh_lines),
        "sh_ownership_pct": f"{shareholder.ownership_percentage:.4f}".rstrip("0").rstrip("."),
        "sh_shares_boy": str(shareholder.beginning_shares) if shareholder.beginning_shares else "",
        "sh_shares_eoy": str(shareholder.ending_shares) if shareholder.ending_shares else "",
    }

    # ---- Load Schedule K field values ----
    fvs = (
        FormFieldValue.objects.filter(tax_return=tax_return)
        .select_related("form_line")
    )
    k_values: dict[str, str] = {}
    for fv in fvs:
        ln = fv.form_line.line_number
        if ln.startswith("K") or ln.startswith("QBI_"):
            k_values[ln] = fv.value

    # ---- Part III: compute shareholder's share ----
    field_values: dict[str, tuple[str, str]] = {}

    # Simple pro-rata lines
    for k_line, k1_line in SCHED_K_TO_K1_MAP.items():
        raw = k_values.get(k_line, "")
        if not raw:
            continue
        try:
            amount = Decimal(raw)
        except InvalidOperation:
            continue
        if amount == 0:
            continue
        share = (amount * ownership_pct).quantize(Decimal("1"))
        field_values[k1_line] = (str(share), "currency")

    # Coded-entry boxes (K12, K13, K15, K16, K17)
    for items_list in (K12_ITEMS, K13_ITEMS, K15_ITEMS, K16_ITEMS, K17_ITEMS):
        for k_line, code_letter, code_field, amt_field in items_list:
            if k_line == "K16d":
                # Distributions: use per-shareholder amount, not pro rata
                amount = shareholder.distributions
            else:
                raw = k_values.get(k_line, "")
                if not raw:
                    continue
                try:
                    amount = (Decimal(raw) * ownership_pct).quantize(Decimal("1"))
                except InvalidOperation:
                    continue
            if amount == 0:
                continue
            field_values[code_field] = (code_letter, "text")
            field_values[amt_field] = (str(amount), "currency")

    # Line 17 code AC: health insurance (row 1, if applicable)
    if shareholder.health_insurance_premium and shareholder.health_insurance_premium > 0:
        field_values["17_code_1"] = ("AC", "text")
        field_values["17_amt_1"] = (str(shareholder.health_insurance_premium), "currency")

    # ---- QBI (Section 199A) — K-1 Box 17 Code V ----
    # Load entity-level QBI data and build supplemental statement
    qbi_income_raw = k_values.get("K1", "")
    qbi_w2_raw = k_values.get("QBI_W2_WAGES", "")
    qbi_ubia_raw = k_values.get("QBI_UBIA", "")
    qbi_sstb_raw = k_values.get("QBI_IS_SSTB", "")

    qbi_income = ZERO
    qbi_w2 = ZERO
    qbi_ubia = ZERO
    try:
        if qbi_income_raw:
            qbi_income = (Decimal(qbi_income_raw) * ownership_pct).quantize(Decimal("1"))
    except InvalidOperation:
        pass
    try:
        if qbi_w2_raw:
            qbi_w2 = (Decimal(qbi_w2_raw) * ownership_pct).quantize(Decimal("1"))
    except InvalidOperation:
        pass
    try:
        if qbi_ubia_raw:
            qbi_ubia = (Decimal(qbi_ubia_raw) * ownership_pct).quantize(Decimal("1"))
    except InvalidOperation:
        pass

    qbi_statement_pages = None
    # Only populate Code V if there's QBI income OR W-2 wages / UBIA entered
    if qbi_income or qbi_w2 or qbi_ubia:
        # Find next available Box 17 row (after AC and K17 items)
        next_17_row = 5  # rows 1=AC, 2=K17a, 3=K17b, 4=K17c → 5 for QBI
        field_values[f"17_code_{next_17_row}"] = ("V", "text")
        field_values[f"17_amt_{next_17_row}"] = (str(qbi_income), "currency")

        # Build QBI supplemental statement
        is_sstb = qbi_sstb_raw.lower() in ("true", "1", "yes") if qbi_sstb_raw else False
        entity_name = entity.legal_name or entity.name
        qbi_statement_pages = [{
            "title": f"Schedule K-1 ({year}) — Section 199A Statement",
            "subtitle": f"Box 17, Code V — {shareholder.name}",
            "form_code": "1120-S K-1",
            "items": [
                {"description": "Ordinary business income (loss)", "amount": str(qbi_income)},
                {"description": "W-2 wages", "amount": str(qbi_w2)},
                {"description": "UBIA of qualified property", "amount": str(qbi_ubia)},
                {"description": "Specified service trade or business (SSTB)", "amount": "Yes" if is_sstb else "No"},
                {"description": "Entity name", "amount": entity_name},
            ],
        }]

    k1_bytes = render(
        form_id="f1120sk1",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
        statement_pages=qbi_statement_pages,
    )
    return k1_bytes


def render_all_k1s(tax_return) -> bytes:
    """Render all K-1s for a return, concatenated into a single PDF."""
    from apps.returns.models import Shareholder

    shareholders = Shareholder.objects.filter(
        tax_return=tax_return, is_active=True
    ).order_by("sort_order", "name")

    if not shareholders.exists():
        raise ValueError("No active shareholders found for this return.")

    writer = PdfWriter()
    for sh in shareholders:
        k1_bytes = render_k1(tax_return, sh)
        k1_reader = PdfReader(io.BytesIO(k1_bytes))
        for page in k1_reader.pages:
            writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Form 7206 rendering
# ---------------------------------------------------------------------------


def render_7206(tax_return, shareholder) -> bytes:
    """
    Render Form 7206 (Self-Employed Health Insurance Deduction) for a shareholder.

    For S-Corp >2% shareholders, fills:
    - Header: shareholder name + SSN
    - Line 1: health insurance premium amount
    - Line 3: total (= line 1, since line 2 is usually 0)

    Lines 4-10 are skipped for S-Corp shareholders per IRS instructions.
    Lines 11-14 require 1040 data and are left for the individual preparer.
    """
    tax_year_applicable = tax_return.form_definition.tax_year_applicable
    premium = shareholder.health_insurance_premium or Decimal("0")

    header_data = {
        "taxpayer_name": shareholder.name,
        "taxpayer_ssn": shareholder.ssn or "",
    }

    field_values: dict[str, tuple[str, str]] = {
        "1": (str(premium), "currency"),
        "3": (str(premium), "currency"),  # line 3 = line 1 + line 2
    }

    return render(
        form_id="f7206",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


# ---------------------------------------------------------------------------
# Form 1125-A rendering (Cost of Goods Sold)
# ---------------------------------------------------------------------------


def render_1125a(tax_return) -> bytes:
    """
    Render Form 1125-A (Cost of Goods Sold) for a tax return.

    Reads Schedule A field values (lines A1-A8) from FormFieldValue
    and renders them onto the official 1125-A template.
    """
    from apps.returns.models import FormFieldValue

    tax_year_applicable = tax_return.form_definition.tax_year_applicable
    entity = tax_return.tax_year.entity

    header_data = {
        "entity_name": entity.legal_name or entity.name,
        "ein": entity.ein or "",
    }

    # Load Schedule A field values (line numbers A1-A8)
    fvs = (
        FormFieldValue.objects.filter(tax_return=tax_return)
        .select_related("form_line")
    )

    field_values: dict[str, tuple[str, str]] = {}
    for fv in fvs:
        ln = fv.form_line.line_number
        if not ln.startswith("A") or len(ln) < 2 or not fv.value:
            continue

        form_line = ln[1:]

        # Lines 1-8: currency amounts
        if form_line.isdigit():
            field_values[form_line] = (fv.value, "currency")
        # A9a: inventory method dropdown → checkbox
        elif form_line == "9a":
            val = fv.value.lower()
            if "cost" in val and "market" not in val:
                field_values["9a_cost"] = ("true", "boolean")
            elif "market" in val or "lcm" in val.replace(" ", ""):
                field_values["9a_lcm"] = ("true", "boolean")
        # A9f: change in quantities → Yes/No checkboxes
        elif form_line == "9f":
            if fv.value.lower() in ("true", "yes", "1"):
                field_values["9f_yes"] = ("true", "boolean")
            else:
                field_values["9f_no"] = ("true", "boolean")

    return render(
        form_id="f1125a",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


# ---------------------------------------------------------------------------
# Form 1125-E rendering (Compensation of Officers)
# ---------------------------------------------------------------------------


def render_1125e(tax_return) -> bytes:
    """
    Render Form 1125-E (Compensation of Officers) for a tax return.

    Reads Officer model instances and renders them into the 1125-E table.
    """
    from apps.returns.models import Officer

    tax_year_applicable = tax_return.form_definition.tax_year_applicable
    entity = tax_return.tax_year.entity

    header_data = {
        "entity_name": entity.legal_name or entity.name,
        "ein": entity.ein or "",
    }

    officers = Officer.objects.filter(tax_return=tax_return).order_by(
        "sort_order", "name"
    )

    field_values: dict[str, tuple[str, str]] = {}
    total_comp = Decimal("0")

    for i, officer in enumerate(officers[:20], start=1):
        prefix = f"E1R{i}"
        field_values[f"{prefix}_name"] = (officer.name, "text")
        if officer.ssn:
            field_values[f"{prefix}_ssn"] = (officer.ssn, "text")
        if officer.percent_time:
            field_values[f"{prefix}_pct_time"] = (str(officer.percent_time), "text")
        if officer.percent_ownership:
            field_values[f"{prefix}_pct_own"] = (str(officer.percent_ownership), "text")
        if officer.compensation:
            field_values[f"{prefix}_comp"] = (str(officer.compensation), "currency")
            total_comp += officer.compensation

    if total_comp:
        field_values["E2"] = (str(total_comp), "currency")
        # Line 4 = Line 2 - Line 3 (Line 3 is comp claimed on other returns, usually 0)
        field_values["E4"] = (str(total_comp), "currency")

    return render(
        form_id="f1125e",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


# ---------------------------------------------------------------------------
# Form 8825 rendering (Rental Real Estate)
# ---------------------------------------------------------------------------

# Maps RentalProperty model fields to Form 8825 expense line numbers
_RENTAL_EXPENSE_LINES: list[tuple[str, str]] = [
    ("rents_received", "2a"),
    ("advertising", "3"),
    ("auto_and_travel", "4"),
    ("cleaning_and_maintenance", "5"),
    ("commissions", "6"),
    ("insurance", "7"),
    ("interest_mortgage", "8"),
    ("legal_and_professional", "9"),
    ("taxes", "10"),
    ("repairs", "11"),
    ("utilities", "12"),
    ("depreciation", "14"),
    ("other_expenses", "17"),
]


def render_8825(tax_return) -> bytes:
    """
    Render Form 8825 (Rental Real Estate) for a tax return.

    Iterates RentalProperty instances, places each property's data into
    the appropriate column (A-D) on the correct page. Up to 4 properties
    per page (page 0 has A-D, page 1 has E-H which map to A-D columns).

    Lines 20a/20b/21 are computed as totals across all properties.
    """
    from apps.returns.models import RentalProperty

    tax_year_applicable = tax_return.form_definition.tax_year_applicable
    entity = tax_return.tax_year.entity

    properties = RentalProperty.objects.filter(
        tax_return=tax_return
    ).order_by("sort_order", "description")

    if not properties.exists():
        raise ValueError("No rental properties found for this return.")

    header_data = {
        "entity_name": entity.legal_name or entity.name,
        "ein": entity.ein or "",
    }

    # Build field_values for all properties
    # Key pattern: {line}_{slot} where slot is A-H
    field_values: dict[str, tuple[str, str]] = {}
    slots = "ABCDEFGH"
    total_income = Decimal("0")
    total_expenses = Decimal("0")

    for idx, prop in enumerate(properties[:8]):  # max 8 properties (2 pages)
        slot = slots[idx]

        # Property description fields
        field_values[f"1_{slot}_desc"] = (prop.description or "", "text")
        if prop.property_type:
            field_values[f"1_{slot}_type"] = (prop.property_type, "text")
        if prop.fair_rental_days:
            field_values[f"1_{slot}_fair_days"] = (str(prop.fair_rental_days), "text")
        if prop.personal_use_days:
            field_values[f"1_{slot}_personal_days"] = (str(prop.personal_use_days), "text")

        # Expense lines — _RENTAL_EXPENSE_LINES maps model_field → line_num
        for model_field, line_num in _RENTAL_EXPENSE_LINES:
            amount = getattr(prop, model_field, Decimal("0"))
            if amount and amount != 0:
                key = f"{line_num}_{slot}"
                field_values[key] = (str(amount), "currency")

        # Computed lines
        prop_total_exp = prop.total_expenses
        prop_income = prop.rents_received
        prop_net = prop.net_rent

        # Line 2c: total rental income (same as 2a for us, 2b is usually 0)
        if prop_income != 0:
            field_values[f"2c_{slot}"] = (str(prop_income), "currency")

        # Line 18: total expenses
        if prop_total_exp != 0:
            field_values[f"18_{slot}"] = (str(prop_total_exp), "currency")

        # Line 19: net income (loss) per property
        if prop_net != 0:
            field_values[f"19_{slot}"] = (str(prop_net), "currency")

        total_income += prop_income
        total_expenses += prop_total_exp

    # Summary lines — IRS Form 8825 Lines 20-21
    # Line 20a: Combined net income from properties (positive nets only)
    # Line 20b: Combined net loss from properties (negative nets only)
    # Line 21: Net income (loss) = 20a + 20b (+ any 4797 rental gains)
    total_net_income = sum(
        (p.net_rent for p in properties if p.net_rent > 0), ZERO,
    )
    total_net_loss = sum(
        (p.net_rent for p in properties if p.net_rent < 0), ZERO,
    )
    total_net = total_net_income + total_net_loss
    if total_net_income != 0:
        field_values["20a"] = (str(total_net_income), "currency")
    if total_net_loss != 0:
        field_values["20b"] = (str(total_net_loss), "currency")
    if total_net != 0:
        field_values["21"] = (str(total_net), "currency")

    return render(
        form_id="f8825",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


# ---------------------------------------------------------------------------
# Form 7203 rendering (per shareholder)
# ---------------------------------------------------------------------------

ZERO = Decimal("0")


def render_7203(tax_return, shareholder) -> bytes:
    """
    Render Form 7203 (S Corp Shareholder Stock and Debt Basis Limitations)
    for a single shareholder.

    Computes all 7203 values from:
    - Shareholder model fields (stock_basis_boy, capital_contributions, etc.)
    - K-1 data (auto from FormFieldValues x ownership_percentage)
    - ShareholderLoan records (Part II)
    - Prior suspended losses (Part III carry-forward)
    """
    from .compute_7203 import compute_7203 as do_compute

    tax_year_applicable = tax_return.form_definition.tax_year_applicable
    entity = tax_return.tax_year.entity

    # Compute all field values
    computed = do_compute(tax_return, shareholder)

    # Build header
    header_data = {
        "taxpayer_name": shareholder.name,
        "taxpayer_ssn": shareholder.ssn or "",
        "entity_name": entity.legal_name or entity.name,
        "entity_ein": entity.ein or "",
    }

    # Convert computed dict to field_values format
    field_values: dict[str, tuple[str, str]] = {}
    for line_key, amount in computed.items():
        if amount and amount != ZERO:
            # Part II line 25 is a ratio, not currency
            if line_key.startswith("25"):
                field_values[line_key] = (str(amount), "text")
            else:
                field_values[line_key] = (str(amount), "currency")

    return render(
        form_id="f7203",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


def render_all_7203s(tax_return) -> bytes:
    """Render all 7203s for a return, concatenated into a single PDF."""
    from apps.returns.models import Shareholder

    shareholders = Shareholder.objects.filter(
        tax_return=tax_return, is_active=True
    ).order_by("sort_order", "name")

    if not shareholders.exists():
        raise ValueError("No active shareholders found for this return.")

    writer = PdfWriter()
    for sh in shareholders:
        pdf_bytes = render_7203(tax_return, sh)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    output_buf = io.BytesIO()
    writer.write(output_buf)
    return output_buf.getvalue()


# ---------------------------------------------------------------------------
# Form 7004 rendering (Extension)
# ---------------------------------------------------------------------------


def render_7004(tax_return) -> bytes:
    """
    Render Form 7004 (Application for Automatic Extension of Time To File)
    for a tax return.

    Populates:
    - Header: entity name, EIN, address
    - Line 1: 2-digit form code (25 for 1120-S, 09 for 1065, 12 for 1120)
    - Line 5a: tax year begin/end dates
    - Lines 6-8: tentative tax, total payments, balance due
    """
    entity = tax_return.tax_year.entity
    year = tax_return.tax_year.year
    tax_year_applicable = tax_return.form_definition.tax_year_applicable
    form_code = tax_return.form_definition.code

    # Look up the 2-digit IRS extension code
    ext_code = EXTENSION_FORM_CODES.get(form_code)
    if not ext_code:
        raise ValueError(
            f"Form 7004 not supported for form code {form_code!r}. "
            f"Supported: {', '.join(EXTENSION_FORM_CODES.keys())}"
        )

    # Build header
    header_data = {
        "entity_name": entity.legal_name or entity.name,
        "ein": entity.ein or "",
        "address_street": entity.address_line1 or "",
        "address_room": entity.address_line2 or "",
        "address_city": entity.city or "",
        "address_state": entity.state or "",
        "address_zip": entity.zip_code or "",
    }

    # Build field values — Line 1 form code split into two single-digit fields
    field_values: dict[str, tuple[str, str]] = {
        "1a": (ext_code[0], "text"),
        "1b": (ext_code[1], "text"),
    }

    # Line 5a: tax year dates
    # Determine if this is a calendar year filer (Jan 1 – Dec 31)
    from datetime import date

    begin = tax_return.tax_year_start or date(year, 1, 1)
    end = tax_return.tax_year_end or date(year, 12, 31)
    is_calendar_year = (begin.month == 1 and begin.day == 1
                        and end.month == 12 and end.day == 31)

    if is_calendar_year:
        # Calendar year: only fill the 2-digit year suffix ("25" for 2025)
        # The form reads "calendar year 20__" — just the suffix goes here.
        # Do NOT populate begin/end date fields for calendar year filers.
        field_values["5a_year"] = (str(year)[-2:], "text")
    else:
        # Fiscal year: fill begin/end dates, leave calendar year field empty
        field_values["5a_begin"] = (begin.strftime("%m/%d"), "text")
        field_values["5a_begin_year"] = (str(begin.year)[-2:], "text")
        field_values["5a_end"] = (end.strftime("%m/%d"), "text")
        field_values["5a_end_year"] = (str(end.year)[-2:], "text")

    # Lines 6-8: financial amounts
    if tax_return.tentative_tax:
        field_values["6"] = (str(tax_return.tentative_tax), "currency")
    if tax_return.total_payments:
        field_values["7"] = (str(tax_return.total_payments), "currency")
    if tax_return.balance_due:
        field_values["8"] = (str(tax_return.balance_due), "currency")

    return render(
        form_id="f7004",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


def render_8879s(tax_return) -> bytes:
    """
    Render Form 8879-S (IRS e-file Signature Authorization for Form 1120-S).

    Populates:
    - Header: entity name, EIN, tax year dates
    - Part I: Lines 1-5 (financial amounts pulled from 1120-S field values)
    - Part II: ERO firm name, officer PIN authorization
    """
    from apps.returns.models import FormFieldValue

    entity = tax_return.tax_year.entity
    year = tax_return.tax_year.year
    tax_year_applicable = tax_return.form_definition.tax_year_applicable

    # Header
    header_data = {
        "entity_name": entity.legal_name or entity.name,
        "ein": entity.ein or "",
    }
    if tax_return.tax_year_start:
        header_data["tax_year_begin"] = tax_return.tax_year_start.strftime("%m/%d")
    if tax_return.tax_year_end:
        header_data["tax_year_end"] = tax_return.tax_year_end.strftime("%m/%d")
        header_data["tax_year_end_year"] = str(tax_return.tax_year_end.year)[-2:]

    # Part I: financial amounts from the 1120-S return
    # Line 1 = 1120-S line 1c (gross receipts), Line 2 = line 3, Line 3 = line 21
    # Line 4 = Sched K line 2, Line 5 = Sched K line 18
    line_map = {
        "1": "1c",    # Gross receipts
        "2": "3",     # Gross profit
        "3": "21",    # Ordinary business income
        "4": "K2",    # Net rental real estate (Sched K line 2)
        "5": "K18",   # Income reconciliation (Sched K line 18)
    }

    field_values: dict[str, tuple[str, str]] = {}
    for efile_line, return_line in line_map.items():
        try:
            fv = FormFieldValue.objects.filter(
                tax_return=tax_return, form_line__line_number=return_line,
            ).first()
            if fv and fv.value:
                field_values[efile_line] = (fv.value, "currency")
        except Exception:
            pass

    # ERO firm name (from preparer info if available)
    try:
        prep = tax_return.preparer_info
        if prep and prep.firm_name:
            field_values["ero_firm_name"] = (prep.firm_name, "text")
            field_values["chk_authorize_ero"] = ("true", "boolean")
    except Exception:
        pass

    return render(
        form_id="f8879s",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


def render_8453s(tax_return) -> bytes:
    """
    Render Form 8453-S (U.S. S Corporation Income Tax Declaration
    for an IRS e-file Return).

    Populates:
    - Header: entity name, EIN, tax year dates
    - Part I: Lines 1-5 (financial amounts pulled from 1120-S field values)
    - Part III: ERO/preparer info
    """
    from apps.returns.models import FormFieldValue

    entity = tax_return.tax_year.entity
    year = tax_return.tax_year.year
    tax_year_applicable = tax_return.form_definition.tax_year_applicable

    # Header
    header_data = {
        "entity_name": entity.legal_name or entity.name,
        "ein": entity.ein or "",
    }
    if tax_return.tax_year_start:
        header_data["tax_year_begin"] = tax_return.tax_year_start.strftime("%m/%d")
    if tax_return.tax_year_end:
        header_data["tax_year_end"] = tax_return.tax_year_end.strftime("%m/%d")
        header_data["tax_year_end_year"] = str(tax_return.tax_year_end.year)[-2:]

    # Part I: same financial amounts as 8879-S
    line_map = {
        "1": "1c",
        "2": "3",
        "3": "21",
        "4": "K2",
        "5": "K18",
    }

    field_values: dict[str, tuple[str, str]] = {}
    for efile_line, return_line in line_map.items():
        try:
            fv = FormFieldValue.objects.filter(
                tax_return=tax_return, form_line__line_number=return_line,
            ).first()
            if fv and fv.value:
                field_values[efile_line] = (fv.value, "currency")
        except Exception:
            pass

    # ERO/Preparer info (from preparer info if available)
    try:
        prep = tax_return.preparer_info
        if prep:
            if prep.firm_name:
                field_values["ero_firm_name"] = (prep.firm_name, "text")
            if prep.firm_address:
                field_values["ero_firm_address"] = (prep.firm_address, "text")
            if prep.firm_ein:
                field_values["ero_ein"] = (prep.firm_ein, "text")
            if prep.firm_phone:
                field_values["ero_phone"] = (prep.firm_phone, "text")
            if prep.preparer_name:
                field_values["preparer_name"] = (prep.preparer_name, "text")
            if prep.preparer_ptin:
                field_values["preparer_ptin"] = (prep.preparer_ptin, "text")
                field_values["ero_ssn_ptin"] = (prep.preparer_ptin, "text")
            field_values["chk_paid_preparer"] = ("true", "boolean")
    except Exception:
        pass

    return render(
        form_id="f8453s",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


# ---------------------------------------------------------------------------
# Form 4562 rendering (Depreciation and Amortization)
# ---------------------------------------------------------------------------


def render_4562(tax_return) -> bytes:
    """
    Render Form 4562 (Depreciation and Amortization) for a tax return.

    Reads DepreciationAsset model instances and populates:
    - Part I: Section 179 deduction worksheet
    - Part II: Special Depreciation Allowance (Bonus)
    - Part III: MACRS Depreciation (grouped by recovery period)
    - Part V: Listed Property (vehicles)
    - Part VI: Amortization (Section 197 / startup costs)
    - Line 22: Total depreciation
    """
    from apps.returns.models import DepreciationAsset

    tax_year_applicable = tax_return.form_definition.tax_year_applicable
    entity = tax_return.tax_year.entity

    header_data = {
        "entity_name": entity.legal_name or entity.name,
        "activity_desc": entity.business_activity or "",
        "ein": entity.ein or "",
    }

    assets = DepreciationAsset.objects.filter(
        tax_return=tax_return,
    ).order_by("sort_order", "asset_number")

    field_values: dict[str, tuple[str, str]] = {}

    # -----------------------------------------------------------------------
    # Part I: Section 179
    # -----------------------------------------------------------------------
    sec_179_limit = Decimal("2500000")
    sec_179_phaseout = Decimal("4000000")
    total_179_cost = ZERO
    total_179_elected = ZERO

    sec_179_assets = [a for a in assets if a.sec_179_elected and a.sec_179_elected > 0]
    for a in sec_179_assets:
        total_179_cost += a.cost_basis
        total_179_elected += a.sec_179_elected

    if sec_179_assets:
        field_values["F4562_1"] = (str(sec_179_limit), "currency")
        field_values["F4562_2"] = (str(total_179_cost), "currency")
        field_values["F4562_3"] = (str(sec_179_phaseout), "currency")

        # Line 4: Reduction = max(0, total_cost - phaseout)
        reduction = max(ZERO, total_179_cost - sec_179_phaseout)
        field_values["F4562_4"] = (str(reduction), "currency")

        # Line 5: Dollar limitation = max(0, limit - reduction)
        dollar_limit = max(ZERO, sec_179_limit - reduction)
        field_values["F4562_5"] = (str(dollar_limit), "currency")

        # Lines 6-7: Individual 179 property rows (up to 2 in the table)
        for i, a in enumerate(sec_179_assets[:2], start=1):
            field_values[f"L6R{i}_desc"] = (a.description[:40] if a.description else "", "text")
            field_values[f"L6R{i}_cost"] = (str(a.cost_basis), "currency")
            field_values[f"L6R{i}_elected"] = (str(a.sec_179_elected), "currency")

        # Line 8: Total elected cost
        field_values["F4562_8"] = (str(total_179_elected), "currency")

        # Line 9: Tentative deduction = min(line 5, line 8)
        tentative = min(dollar_limit, total_179_elected)
        field_values["F4562_9"] = (str(tentative), "currency")

        # Line 10: Carryover of disallowed deduction from prior year (not tracked yet)
        # Line 11: Business income limitation (not tracked yet)

        # Line 12: Section 179 expense deduction = tentative (simplified)
        field_values["F4562_12"] = (str(tentative), "currency")

        # Line 13: Carryover to next year = max(0, total_elected - tentative)
        carryover = max(ZERO, total_179_elected - tentative)
        if carryover > 0:
            field_values["F4562_13"] = (str(carryover), "currency")

    # -----------------------------------------------------------------------
    # Part II: Special Depreciation Allowance (Bonus)
    # -----------------------------------------------------------------------
    bonus_assets = [a for a in assets if a.bonus_amount and a.bonus_amount > 0
                    and not a.is_amortization]
    total_bonus = sum(a.bonus_amount for a in bonus_assets)

    if total_bonus > 0:
        field_values["F4562_14"] = (str(total_bonus), "currency")

    # -----------------------------------------------------------------------
    # Part III: MACRS Depreciation
    # -----------------------------------------------------------------------
    # Line 17: MACRS deductions for assets placed in service in prior years
    prior_year_assets = [
        a for a in assets
        if a.date_acquired
        and a.date_acquired.year < tax_return.tax_year.year
        and not a.is_amortization
        and a.method != "NONE"
        and a.group_label != "Land"
    ]
    prior_year_depr = sum(a.current_depreciation for a in prior_year_assets)
    if prior_year_depr > 0:
        field_values["F4562_17"] = (str(prior_year_depr), "currency")

    # Section B: GDS MACRS assets placed in service THIS year
    # Group by recovery period → populate lines 19a-19i
    current_year_assets = [
        a for a in assets
        if a.date_acquired
        and a.date_acquired.year == tax_return.tax_year.year
        and not a.is_amortization
        and a.method != "NONE"
        and a.group_label != "Land"
        and not a.is_listed_property
    ]

    # MACRS life → IRS line mapping
    macrs_line_map = {
        Decimal("3"): "a", Decimal("3.0"): "a",
        Decimal("5"): "b", Decimal("5.0"): "b",
        Decimal("7"): "c", Decimal("7.0"): "c",
        Decimal("10"): "d", Decimal("10.0"): "d",
        Decimal("15"): "e", Decimal("15.0"): "e",
        Decimal("20"): "f", Decimal("20.0"): "f",
        Decimal("25"): "g", Decimal("25.0"): "g",
        Decimal("27.5"): "h",
        Decimal("39"): "i", Decimal("39.0"): "i",
    }

    # Aggregate by life
    life_groups: dict[str, dict] = {}
    for a in current_year_assets:
        line_letter = macrs_line_map.get(a.life, "")
        if not line_letter:
            continue
        if line_letter not in life_groups:
            life_groups[line_letter] = {
                "basis": ZERO,
                "depr": ZERO,
                "period": str(a.life) if a.life else "",
                "convention": a.convention or "",
                "method": a.method or "",
                "placed": "",
            }
        life_groups[line_letter]["basis"] += (
            a.cost_basis - a.sec_179_elected - a.bonus_amount
        )
        life_groups[line_letter]["depr"] += a.current_depreciation - a.sec_179_elected - a.bonus_amount

    # Map "a"-"i" to 19a-19i lines (Section B uses single-row suffix)
    # For 27.5-year and 39-year, there are two sub-rows (_1 and _2) — use first
    for letter, data in life_groups.items():
        suffix = letter
        if data["basis"] > 0 or data["depr"] > 0:
            if data["placed"]:
                field_values[f"L19{suffix}_placed"] = (data["placed"], "text")
            field_values[f"L19{suffix}_basis"] = (str(data["basis"]), "currency")
            field_values[f"L19{suffix}_period"] = (data["period"], "text")
            field_values[f"L19{suffix}_convention"] = (data["convention"], "text")
            method_display = {
                "200DB": "200DB", "150DB": "150DB", "SL": "S/L",
            }.get(data["method"], data["method"])
            field_values[f"L19{suffix}_method"] = (method_display, "text")
            field_values[f"L19{suffix}_depr"] = (str(data["depr"]), "currency")

    # -----------------------------------------------------------------------
    # Part V: Listed Property (vehicles)
    # -----------------------------------------------------------------------
    vehicle_assets = [a for a in assets if a.is_listed_property]
    total_listed_depr = ZERO
    for i, va in enumerate(vehicle_assets[:3], start=1):
        field_values[f"LP26R{i}_desc"] = (va.description[:20] if va.description else "", "text")
        if va.date_acquired:
            field_values[f"LP26R{i}_placed"] = (va.date_acquired.strftime("%m/%d/%y"), "text")
        field_values[f"LP26R{i}_cost"] = (str(va.cost_basis), "currency")
        bus_pct = f"{va.business_pct:.0f}%"
        field_values[f"LP26R{i}_buspct"] = (bus_pct, "text")
        field_values[f"LP26R{i}_depr"] = (str(va.current_depreciation), "currency")
        total_listed_depr += va.current_depreciation
        # Method/convention
        method_display = {
            "200DB": "200DB", "150DB": "150DB", "SL": "S/L",
        }.get(va.method, va.method)
        field_values[f"LP26R{i}_method"] = (method_display, "text")

    if total_listed_depr > 0:
        field_values["F4562_21"] = (str(total_listed_depr), "currency")

    # -----------------------------------------------------------------------
    # Part VI: Amortization
    # -----------------------------------------------------------------------
    amort_assets = [a for a in assets if a.is_amortization]
    total_amort = ZERO

    for i, aa in enumerate(amort_assets[:2], start=1):
        field_values[f"AM42R{i}_desc"] = (aa.description[:30] if aa.description else "", "text")
        if aa.date_acquired:
            field_values[f"AM42R{i}_date"] = (aa.date_acquired.strftime("%m/%d/%y"), "text")
        field_values[f"AM42R{i}_amount"] = (str(aa.cost_basis), "currency")
        field_values[f"AM42R{i}_code"] = (aa.amort_code or "197", "text")
        field_values[f"AM42R{i}_period"] = (str(aa.amort_months or 180), "text")
        field_values[f"AM42R{i}_deduction"] = (str(aa.current_depreciation), "currency")
        total_amort += aa.current_depreciation

    if total_amort > 0:
        field_values["F4562_44"] = (str(total_amort), "currency")

    # -----------------------------------------------------------------------
    # Line 22: Total depreciation (all parts combined)
    # -----------------------------------------------------------------------
    total_depr = sum(
        a.current_depreciation for a in assets
        if a.group_label != "Land" and a.method != "NONE"
    )
    if total_depr > 0:
        field_values["F4562_22"] = (str(total_depr), "currency")

    return render(
        form_id="f4562",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


# ---------------------------------------------------------------------------
# Form 4797 rendering (Sales of Business Property)
# ---------------------------------------------------------------------------


def _holding_period_months(date_acquired, date_sold) -> int:
    """Compute holding period in whole months. IRS §1231: >12 months = long-term."""
    return (date_sold.year - date_acquired.year) * 12 + (date_sold.month - date_acquired.month)


def _is_1250_property(group_label: str) -> bool:
    """§1250 property = depreciable real property (buildings, improvements)."""
    return group_label in ("Buildings", "Improvements")


def render_4797(tax_return) -> bytes:
    """
    Render Form 4797 (Sales of Business Property) for a tax return.

    Rebuilt from Rule Studio spec (4797_TY2025_v1).
    Data source: DepreciationAsset instances with date_sold populated.

    Routing (R001/R002):
    - Short-term (≤12 months) → Part II (Line 10 rows)
    - Long-term loss → Part I Line 2 rows
    - Long-term gain, no depreciation → Part I Line 2 rows
    - Long-term gain WITH depreciation → Part III per-property columns
      §1245: recapture = min(gain, depreciation) [R005]
      §1250: recapture = 0 (post-1986 SL) [R007], unrecaptured at 25% [R008]
      L31 → Part II Line 13, L32 → Part I Line 6
    """
    from apps.returns.models import DepreciationAsset

    tax_year_applicable = tax_return.form_definition.tax_year_applicable
    entity = tax_return.tax_year.entity

    header_data = {
        "entity_name": entity.legal_name or entity.name,
        "ein": entity.ein or "",
    }

    # Get all disposed assets (have a date_sold)
    disposed = DepreciationAsset.objects.filter(
        tax_return=tax_return,
        date_sold__isnull=False,
    ).order_by("sort_order", "asset_number")

    if not disposed.exists():
        return render(
            form_id="f4797",
            tax_year=tax_year_applicable,
            field_values={},
            header_data=header_data,
        )

    field_values: dict[str, tuple[str, str]] = {}

    # -----------------------------------------------------------------------
    # Route each disposed asset (R001/R002)
    # -----------------------------------------------------------------------
    part1_line2_entries = []   # (asset, gain) — losses or non-depreciable gains
    part2_assets = []          # short-term assets
    part3_assets = []          # long-term gains with depreciation → Part III

    for a in disposed:
        # R001 — holding period in months
        if a.date_acquired and a.date_sold:
            months = _holding_period_months(a.date_acquired, a.date_sold)
        else:
            months = 13  # assume long-term if dates missing

        is_long_term = months > 12

        # R004 — adjusted basis
        total_depr = (
            a.prior_depreciation + a.current_depreciation
            + a.bonus_amount + a.sec_179_elected
        )
        cost_plus = a.cost_basis + (a.expenses_of_sale or ZERO)
        adjusted_basis = cost_plus - total_depr

        # R003 — gain or loss
        gain = (a.sales_price or ZERO) - adjusted_basis

        # R002 — routing
        if not is_long_term:
            part2_assets.append((a, gain))
        elif gain <= 0:
            part1_line2_entries.append((a, gain))
        elif total_depr > 0:
            part3_assets.append(a)
        else:
            part1_line2_entries.append((a, gain))

    # -----------------------------------------------------------------------
    # Part III: Recapture detail (§1245/§1250)
    # Per-property columns a-d. Summary lines 30, 31, 32.
    # -----------------------------------------------------------------------
    cols = ["a", "b", "c", "d"]
    p3_total_gain = ZERO   # Line 30
    p3_total_recapture = ZERO  # Line 31

    for i, a in enumerate(part3_assets[:4]):
        col = cols[i]
        total_depr = a.prior_depreciation + a.current_depreciation + a.bonus_amount + a.sec_179_elected
        is_1250 = _is_1250_property(a.group_label)

        # Line 19: Description + dates
        field_values[f"P3_19R{i+1}_desc"] = (a.description[:30] if a.description else "", "text")
        if a.date_acquired:
            field_values[f"P3_19R{i+1}_acquired"] = (a.date_acquired.strftime("%m/%d/%y"), "text")
        if a.date_sold:
            field_values[f"P3_19R{i+1}_sold"] = (a.date_sold.strftime("%m/%d/%y"), "text")

        # Line 20: Gross sales price
        sales = a.sales_price or ZERO
        field_values[f"P3_20_{col}"] = (str(sales), "currency")

        # Line 21: Cost or other basis plus expense of sale
        cost_plus = a.cost_basis + (a.expenses_of_sale or ZERO)
        field_values[f"P3_21_{col}"] = (str(cost_plus), "currency")

        # Line 22: Depreciation allowed or allowable
        field_values[f"P3_22_{col}"] = (str(total_depr), "currency")

        # Line 23: Adjusted basis (L21 - L22)
        adjusted_basis = cost_plus - total_depr
        field_values[f"P3_23_{col}"] = (str(adjusted_basis), "currency")

        # Line 24: Total gain (L20 - L23)
        total_gain = sales - adjusted_basis
        field_values[f"P3_24_{col}"] = (str(total_gain), "currency")
        p3_total_gain += total_gain

        if is_1250:
            # §1250 property — Lines 26a through 26g
            # Post-1986 straight-line: additional depreciation = $0 [R007]
            field_values[f"P3_26a_{col}"] = (str(ZERO), "currency")
            # 26b = applicable % (100%) × smaller of Line 24 or 26a = 0
            field_values[f"P3_26b_{col}"] = (str(ZERO), "currency")
            # 26g = sum of 26b + 26e + 26f = 0
            field_values[f"P3_26g_{col}"] = (str(ZERO), "currency")
            recapture = ZERO
        else:
            # §1245 property — Lines 25a and 25b
            # 25a = depreciation allowed or allowable (same as Line 22)
            field_values[f"P3_25a_{col}"] = (str(total_depr), "currency")
            # 25b = smaller of Line 24 (total gain) or Line 25a (depreciation)
            recapture = min(total_gain, total_depr)
            field_values[f"P3_25b_{col}"] = (str(recapture), "currency")

        # Line 27 is ONLY for §1252 farm property — do NOT write anything here
        # for §1245 or §1250 assets.
        p3_total_recapture += recapture

    # Part III summary lines
    p3_section_1231 = p3_total_gain - p3_total_recapture  # Line 32

    if p3_total_gain:
        field_values["P4797_30"] = (str(p3_total_gain), "currency")
    if p3_total_recapture:
        field_values["P4797_31"] = (str(p3_total_recapture), "currency")
    if p3_section_1231:
        field_values["P4797_32"] = (str(p3_section_1231), "currency")

    # -----------------------------------------------------------------------
    # Part I: Section 1231 gains/losses
    # Line 2: losses or non-depreciable property only
    # Line 6: Part III Line 32 (§1231 gain from recapture)
    # Line 7: Total of Lines 2 through 6
    # -----------------------------------------------------------------------
    total_part1_line2 = ZERO
    for i, (a, amount) in enumerate(part1_line2_entries[:4], start=1):
        total_depr = a.prior_depreciation + a.current_depreciation + a.bonus_amount + a.sec_179_elected
        field_values[f"P1_2R{i}_desc"] = (a.description[:20] if a.description else "", "text")
        if a.date_acquired:
            field_values[f"P1_2R{i}_acquired"] = (a.date_acquired.strftime("%m/%d/%y"), "text")
        if a.date_sold:
            field_values[f"P1_2R{i}_sold"] = (a.date_sold.strftime("%m/%d/%y"), "text")
        if a.sales_price:
            field_values[f"P1_2R{i}_gross"] = (str(a.sales_price), "currency")
        field_values[f"P1_2R{i}_depr"] = (str(total_depr), "currency")
        field_values[f"P1_2R{i}_cost"] = (str(a.cost_basis), "currency")
        field_values[f"P1_2R{i}_gain"] = (str(amount), "currency")
        total_part1_line2 += amount

    # Line 6 = Part III Line 32 (Section 1231 gain from recapture)
    if p3_section_1231:
        field_values["P4797_6"] = (str(p3_section_1231), "currency")

    # Line 7 = sum of Lines 2-6
    total_part1 = total_part1_line2 + p3_section_1231
    if total_part1 != 0:
        field_values["P4797_7"] = (str(total_part1), "currency")

    # -----------------------------------------------------------------------
    # Part II: Ordinary Gains and Losses
    # Line 10: short-term dispositions
    # Line 13: Part III Line 31 (recapture → ordinary)
    # Line 17: Total ordinary
    # -----------------------------------------------------------------------
    total_ordinary = ZERO
    for i, (a, gain_loss) in enumerate(part2_assets[:4], start=1):
        total_depr = a.prior_depreciation + a.current_depreciation + a.bonus_amount + a.sec_179_elected
        field_values[f"P2_10R{i}_desc"] = (a.description[:20] if a.description else "", "text")
        if a.date_acquired:
            field_values[f"P2_10R{i}_acquired"] = (a.date_acquired.strftime("%m/%d/%y"), "text")
        if a.date_sold:
            field_values[f"P2_10R{i}_sold"] = (a.date_sold.strftime("%m/%d/%y"), "text")
        if a.sales_price:
            field_values[f"P2_10R{i}_gross"] = (str(a.sales_price), "currency")
        field_values[f"P2_10R{i}_depr"] = (str(total_depr), "currency")
        field_values[f"P2_10R{i}_cost"] = (str(a.cost_basis), "currency")
        field_values[f"P2_10R{i}_gain"] = (str(gain_loss), "currency")
        total_ordinary += gain_loss

    # Line 13 = Part III Line 31 (total recapture → ordinary income)
    if p3_total_recapture:
        field_values["P4797_13"] = (str(p3_total_recapture), "currency")
        total_ordinary += p3_total_recapture

    if total_ordinary != 0:
        field_values["P4797_17"] = (str(total_ordinary), "currency")

    return render(
        form_id="f4797",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


# ---------------------------------------------------------------------------
# Schedule D (Form 1120-S) rendering
# ---------------------------------------------------------------------------


def render_schedule_d(tax_return) -> bytes:
    """
    Render Schedule D (Form 1120-S) — Capital Gains and Losses.

    Data source: Disposition instances where is_4797=False.
    Per spec (SCHD_1120S):
    - Part I: Short-term capital gains/losses (Lines 1a-7)
    - Part II: Long-term capital gains/losses (Lines 8a-15)
    - R004: K7 = Part I Line 7 (net ST); K8a = Part II Line 15 (net LT)
    - R010: Section 1231 does NOT flow through Schedule D on 1120-S
    """
    from apps.returns.models import Disposition

    tax_year_applicable = tax_return.form_definition.tax_year_applicable
    entity = tax_return.tax_year.entity

    header_data = {
        "entity_name": entity.legal_name or entity.name,
        "ein": entity.ein or "",
    }

    dispositions = Disposition.objects.filter(
        tax_return=tax_return,
        is_4797=False,
    ).order_by("term", "sort_order", "description")

    if not dispositions.exists():
        return render(
            form_id="f1120ssd",
            tax_year=tax_year_applicable,
            field_values={},
            header_data=header_data,
        )

    field_values: dict[str, tuple[str, str]] = {}

    # Separate by term
    st_disps = [d for d in dispositions if d.term == "short"]
    lt_disps = [d for d in dispositions if d.term == "long"]

    # Part I — Short-term: aggregate into Line 1b (Box A — basis reported)
    # For simplicity, all ST dispositions aggregate to Line 1a
    # (basis reported to IRS, no adjustments needed)
    st_proceeds = ZERO
    st_cost = ZERO
    st_gain = ZERO
    for d in st_disps:
        st_proceeds += d.sales_price
        st_cost += d.cost_basis + d.expenses_of_sale
        st_gain += d.sales_price - d.cost_basis - d.expenses_of_sale

    if st_disps:
        field_values["SD_1a_proceeds"] = (str(st_proceeds), "currency")
        field_values["SD_1a_cost"] = (str(st_cost), "currency")
        field_values["SD_1a_gain"] = (str(st_gain), "currency")
        # Line 7 = net short-term
        field_values["SD_7"] = (str(st_gain), "currency")

    # Part II — Long-term: aggregate into Line 8a (Box D — basis reported)
    lt_proceeds = ZERO
    lt_cost = ZERO
    lt_gain = ZERO
    for d in lt_disps:
        lt_proceeds += d.sales_price
        lt_cost += d.cost_basis + d.expenses_of_sale
        lt_gain += d.sales_price - d.cost_basis - d.expenses_of_sale

    if lt_disps:
        field_values["SD_8a_proceeds"] = (str(lt_proceeds), "currency")
        field_values["SD_8a_cost"] = (str(lt_cost), "currency")
        field_values["SD_8a_gain"] = (str(lt_gain), "currency")
        # Line 15 = net long-term
        field_values["SD_15"] = (str(lt_gain), "currency")

    return render(
        form_id="f1120ssd",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


# ---------------------------------------------------------------------------
# Form 8949 rendering
# ---------------------------------------------------------------------------


def render_8949(tax_return) -> bytes:
    """
    Render Form 8949 — Sales and Other Dispositions of Capital Assets.

    Data source: Disposition instances where is_4797=False.
    Per spec (8949):
    - Part I: Short-term transactions (Rows 1-11 per page)
    - Part II: Long-term transactions (Rows 1-11 per page)
    - R001: Category A-F based on holding period and basis reporting
    """
    from apps.returns.models import Disposition

    tax_year_applicable = tax_return.form_definition.tax_year_applicable
    entity = tax_return.tax_year.entity

    header_data = {
        "entity_name": entity.legal_name or entity.name,
        "ein": entity.ein or "",
    }

    dispositions = Disposition.objects.filter(
        tax_return=tax_return,
        is_4797=False,
    ).order_by("term", "sort_order", "description")

    if not dispositions.exists():
        return render(
            form_id="f8949",
            tax_year=tax_year_applicable,
            field_values={},
            header_data=header_data,
        )

    field_values: dict[str, tuple[str, str]] = {}

    st_disps = [d for d in dispositions if d.term == "short"]
    lt_disps = [d for d in dispositions if d.term == "long"]

    # Part I — Short-term (Box A = basis reported to IRS)
    if st_disps:
        field_values["F8949_P1_A"] = ("true", "boolean")

    st_total_proceeds = ZERO
    st_total_cost = ZERO
    st_total_gain = ZERO

    for i, d in enumerate(st_disps[:11], start=1):
        gain_loss = d.sales_price - d.cost_basis - d.expenses_of_sale
        field_values[f"F8949_P1_R{i}_desc"] = (
            d.description[:30] if d.description else "", "text"
        )
        if d.date_acquired:
            field_values[f"F8949_P1_R{i}_acquired"] = (
                d.date_acquired.strftime("%m/%d/%y"), "text"
            )
        elif d.date_acquired_various:
            field_values[f"F8949_P1_R{i}_acquired"] = ("VARIOUS", "text")
        if d.date_sold:
            field_values[f"F8949_P1_R{i}_sold"] = (
                d.date_sold.strftime("%m/%d/%y"), "text"
            )
        elif d.date_sold_various:
            field_values[f"F8949_P1_R{i}_sold"] = ("VARIOUS", "text")
        field_values[f"F8949_P1_R{i}_proceeds"] = (str(d.sales_price), "currency")
        field_values[f"F8949_P1_R{i}_cost"] = (
            str(d.cost_basis + d.expenses_of_sale), "currency"
        )
        field_values[f"F8949_P1_R{i}_gain"] = (str(gain_loss), "currency")

        st_total_proceeds += d.sales_price
        st_total_cost += d.cost_basis + d.expenses_of_sale
        st_total_gain += gain_loss

    if st_disps:
        field_values["F8949_P1_TOT_proceeds"] = (str(st_total_proceeds), "currency")
        field_values["F8949_P1_TOT_cost"] = (str(st_total_cost), "currency")
        field_values["F8949_P1_TOT_gain"] = (str(st_total_gain), "currency")

    # Part II — Long-term (Box D = basis reported to IRS)
    if lt_disps:
        field_values["F8949_P2_D"] = ("true", "boolean")

    lt_total_proceeds = ZERO
    lt_total_cost = ZERO
    lt_total_gain = ZERO

    for i, d in enumerate(lt_disps[:11], start=1):
        gain_loss = d.sales_price - d.cost_basis - d.expenses_of_sale
        field_values[f"F8949_P2_R{i}_desc"] = (
            d.description[:30] if d.description else "", "text"
        )
        if d.date_acquired:
            field_values[f"F8949_P2_R{i}_acquired"] = (
                d.date_acquired.strftime("%m/%d/%y"), "text"
            )
        elif d.date_acquired_various:
            field_values[f"F8949_P2_R{i}_acquired"] = ("VARIOUS", "text")
        if d.date_sold:
            field_values[f"F8949_P2_R{i}_sold"] = (
                d.date_sold.strftime("%m/%d/%y"), "text"
            )
        elif d.date_sold_various:
            field_values[f"F8949_P2_R{i}_sold"] = ("VARIOUS", "text")
        field_values[f"F8949_P2_R{i}_proceeds"] = (str(d.sales_price), "currency")
        field_values[f"F8949_P2_R{i}_cost"] = (
            str(d.cost_basis + d.expenses_of_sale), "currency"
        )
        field_values[f"F8949_P2_R{i}_gain"] = (str(gain_loss), "currency")

        lt_total_proceeds += d.sales_price
        lt_total_cost += d.cost_basis + d.expenses_of_sale
        lt_total_gain += gain_loss

    if lt_disps:
        field_values["F8949_P2_TOT_proceeds"] = (str(lt_total_proceeds), "currency")
        field_values["F8949_P2_TOT_cost"] = (str(lt_total_cost), "currency")
        field_values["F8949_P2_TOT_gain"] = (str(lt_total_gain), "currency")

    return render(
        form_id="f8949",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


# ---------------------------------------------------------------------------
# GA-600S AcroForm rendering (migrated from coordinate overlay)
# ---------------------------------------------------------------------------

_GA600S_TEMPLATE = Path(__file__).resolve().parent.parent.parent / "pdf_templates" / "ga600s_2025_acroform.pdf"


def render_ga600s_overlay(tax_return, screen_mode: bool = False) -> bytes:
    """
    Render Georgia Form 600S using AcroForm text overlay.

    Uses the same fill_form() pipeline as federal AcroForm forms.
    The template PDF has AcroForm widgets injected by the AcroForm Creator tool.

    Args:
        tax_return: The STATE TaxReturn instance (form_code="GA-600S").

    Returns:
        PDF bytes for the complete GA-600S.
    """
    from apps.returns.models import FormFieldValue, Shareholder

    entity = tax_return.tax_year.entity
    year = tax_return.tax_year.year

    # --- Build header data ---
    header_data: dict[str, str] = {
        "ein": entity.ein or "",
        "entity_name": entity.legal_name or entity.name or "",
        "address_street": entity.address_line1 or "",
        "address_city": entity.city or "",
        "address_state": entity.state or "GA",
        "address_zip": entity.zip_code or "",
        "phone": entity.phone or "",
        "naics_code": entity.naics_code or "",
        "type_of_business": entity.business_activity or "",
        "state_incorporated": entity.state_incorporated or "",
        # Tax period dates
        "income_tax_begin": f"01/01/{year}",
        "income_tax_end": f"12/31/{year}",
        "nw_tax_begin": f"01/01/{year + 1}",
        "nw_tax_end": f"12/31/{year + 1}",
    }
    if entity.date_incorporated:
        header_data["date_incorporated"] = entity.date_incorporated.strftime("%m/%d/%Y")

    # Continuation headers on pages 2 and 3
    header_data["p2_name"] = header_data["entity_name"]
    header_data["p2_fein"] = header_data["ein"]
    header_data["p3_name"] = header_data["entity_name"]
    header_data["p3_fein"] = header_data["ein"]

    # Shareholder count from federal return
    federal = tax_return.federal_return
    if federal:
        sh_count = Shareholder.objects.filter(
            tax_return=federal, is_active=True
        ).count()
        if sh_count:
            header_data["total_shareholders"] = str(sh_count)

    # PTET election checkbox
    fvs = FormFieldValue.objects.filter(
        tax_return=tax_return,
    ).select_related("form_line")

    field_values: dict[str, tuple[str, str]] = {}
    for fv in fvs:
        ln = fv.form_line.line_number
        field_values[ln] = (fv.value or "", fv.form_line.field_type)

    # PTET checkbox
    ptet_val = field_values.get("GA_PTET", ("", ""))[0]
    if ptet_val and ptet_val.lower() in ("true", "1", "yes"):
        header_data["ptet_election"] = "X"

    # Extension checkbox
    if tax_return.federal_return and tax_return.federal_return.extension_filed:
        header_data["extension_checkbox"] = "X"

    # --- Load AcroForm field map ---
    ga_field_map, ga_header_map = _get_field_maps("fga600s", 2025)

    # --- Fill via AcroForm pipeline ---
    if not _GA600S_TEMPLATE.exists():
        raise FileNotFoundError(
            f"GA-600S template not found at {_GA600S_TEMPLATE}. "
            f"Place the AcroForm GA-600S PDF at server/pdf_templates/ga600s_2025_acroform.pdf"
        )

    return _acroform_fill(
        template_path=_GA600S_TEMPLATE,
        field_values=field_values,
        field_map=ga_field_map,
        header_data=header_data,
        header_map=ga_header_map,
        screen_mode=screen_mode,
    )


# ---------------------------------------------------------------------------
# Depreciation Schedule rendering (standalone report)
# ---------------------------------------------------------------------------


def render_depreciation_schedule(tax_return, screen_mode: bool = False) -> bytes:
    """
    Render a printable depreciation schedule report in landscape orientation.

    Groups assets by flow_destination (Page 1 / Form 8825 / Schedule F),
    shows a table with columns: Description, Date Acquired, Cost Basis, Method,
    Life, Prior Depreciation, Bonus, Section 179, Current Depreciation, Total.
    Includes totals per group and a summary section.

    Returns:
        PDF file content as bytes (landscape letter).
    """
    from apps.returns.models import DepreciationAsset

    entity = tax_return.tax_year.entity
    entity_name = entity.legal_name or entity.name
    year = tax_return.tax_year.year

    assets = DepreciationAsset.objects.filter(
        tax_return=tax_return,
    ).order_by("flow_to", "group_label", "description")

    if not assets.exists():
        # Return a single blank page
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(792, 612))  # landscape
        c.showPage()
        c.save()
        buf.seek(0)
        return buf.getvalue()

    # Group assets by flow_destination
    flow_labels = {
        "page1": "Page 1",
        "8825": "Form 8825",
        "sched_f": "Schedule F",
    }
    groups: dict[str, list] = {}
    for a in assets:
        key = a.flow_to or "page1"
        groups.setdefault(key, []).append(a)

    PAGE_W, PAGE_H = 792, 612  # landscape letter
    LEFT = 36
    TOP = PAGE_H - 36
    RIGHT = PAGE_W - 36
    USABLE = RIGHT - LEFT

    # Column positions (x offsets from LEFT)
    # Description(150), DateAcq(55), Cost(70), Method(55), Life(30), Prior(70), Bonus(60), 179(60), Current(70), Total(70)
    COL_WIDTHS = [150, 55, 70, 55, 30, 70, 60, 60, 70, 70]
    COL_HEADERS = ["Description", "Date Acq", "Cost Basis", "Method", "Life", "Prior Depr", "Bonus", "Sec 179", "Curr Depr", "Total Depr"]

    col_x = []
    x = LEFT
    for w in COL_WIDTHS:
        col_x.append(x)
        x += w

    HEADER_FONT = "Helvetica-Bold"
    BODY_FONT = "Courier-Bold"
    TITLE_SIZE = 12
    COL_HEADER_SIZE = 7
    DATA_SIZE = 8
    ROW_H = 12

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    c.setFillColorRGB(*_data_color(screen_mode))

    def _fmt(val, is_currency=True):
        """Format a Decimal as whole dollars with commas."""
        if val is None:
            return ""
        d = Decimal(str(val))
        if d == 0:
            return ""
        if d < 0:
            return f"({abs(d):,.0f})"
        return f"{d:,.0f}"

    def _method_display(a):
        """Format method as MACRS 200DB HY 5yr style."""
        if a.is_amortization:
            code = a.amort_code or "197"
            months = a.amort_months or 180
            return f"S/L {code} {months}mo"
        method = a.method or ""
        conv = a.convention or "HY"
        life = a.life
        if life is None:
            return method
        life_str = f"{int(life)}yr" if life == int(life) else f"{life}yr"
        if method == "NONE":
            return "LAND"
        return f"{method} {conv} {life_str}"

    for flow_key, group_assets in groups.items():
        flow_label = flow_labels.get(flow_key, flow_key)
        y = TOP

        # Page title
        c.setFont(HEADER_FONT, TITLE_SIZE)
        c.drawCentredString(PAGE_W / 2, y, "DEPRECIATION SCHEDULE")
        y -= ROW_H + 2
        c.setFont("Helvetica", 9)
        c.drawCentredString(PAGE_W / 2, y, f"{entity_name} \u2014 {year} Tax Return")
        y -= ROW_H
        c.drawCentredString(PAGE_W / 2, y, f"Flow: {flow_label}")
        y -= ROW_H + 8

        # Column headers
        c.setFont(HEADER_FONT, COL_HEADER_SIZE)
        for i, hdr in enumerate(COL_HEADERS):
            if i >= 5:  # numeric columns right-aligned
                c.drawRightString(col_x[i] + COL_WIDTHS[i] - 2, y, hdr)
            else:
                c.drawString(col_x[i] + 2, y, hdr)
        y -= 2

        # Header underline
        c.setLineWidth(0.5)
        c.line(LEFT, y, RIGHT, y)
        y -= ROW_H

        # Totals accumulators
        t_cost = ZERO
        t_prior = ZERO
        t_bonus = ZERO
        t_179 = ZERO
        t_current = ZERO
        t_total = ZERO

        # Data rows
        c.setFont(BODY_FONT, DATA_SIZE)
        for a in group_assets:
            if y < 80:  # need space for totals + summary
                c.showPage()
                c.setPageSize((PAGE_W, PAGE_H))
                y = TOP
                # Re-draw column headers on new page
                c.setFont(HEADER_FONT, COL_HEADER_SIZE)
                for i, hdr in enumerate(COL_HEADERS):
                    if i >= 5:
                        c.drawRightString(col_x[i] + COL_WIDTHS[i] - 2, y, hdr)
                    else:
                        c.drawString(col_x[i] + 2, y, hdr)
                y -= 2
                c.line(LEFT, y, RIGHT, y)
                y -= ROW_H
                c.setFont(BODY_FONT, DATA_SIZE)

            is_disposed = a.date_sold is not None
            prefix = "*" if is_disposed else ""

            # Description
            desc = f"{prefix}{a.description or ''}"[:22]
            c.drawString(col_x[0] + 2, y, desc)

            # Date Acquired
            if a.date_acquired:
                c.drawString(col_x[1] + 2, y, a.date_acquired.strftime("%m/%Y"))

            # Cost Basis
            c.drawRightString(col_x[2] + COL_WIDTHS[2] - 2, y, _fmt(a.cost_basis))

            # Method
            c.drawString(col_x[3] + 2, y, _method_display(a)[:8])

            # Life
            if a.life is not None:
                life_str = str(int(a.life)) if a.life == int(a.life) else str(a.life)
                c.drawRightString(col_x[4] + COL_WIDTHS[4] - 2, y, life_str)

            # Prior Depreciation
            c.drawRightString(col_x[5] + COL_WIDTHS[5] - 2, y, _fmt(a.prior_depreciation))

            # Bonus
            c.drawRightString(col_x[6] + COL_WIDTHS[6] - 2, y, _fmt(a.bonus_amount))

            # Section 179
            c.drawRightString(col_x[7] + COL_WIDTHS[7] - 2, y, _fmt(a.sec_179_elected))

            # Current Depreciation
            c.drawRightString(col_x[8] + COL_WIDTHS[8] - 2, y, _fmt(a.current_depreciation))

            # Total Depreciation
            total_depr = (
                (a.prior_depreciation or ZERO)
                + (a.current_depreciation or ZERO)
                + (a.bonus_amount or ZERO)
                + (a.sec_179_elected or ZERO)
            )
            c.drawRightString(col_x[9] + COL_WIDTHS[9] - 2, y, _fmt(total_depr))

            # Accumulate totals
            t_cost += a.cost_basis or ZERO
            t_prior += a.prior_depreciation or ZERO
            t_bonus += a.bonus_amount or ZERO
            t_179 += a.sec_179_elected or ZERO
            t_current += a.current_depreciation or ZERO
            t_total += total_depr

            y -= ROW_H

        # Totals row
        c.setLineWidth(0.5)
        c.line(LEFT, y + ROW_H - 2, RIGHT, y + ROW_H - 2)
        c.setFont(HEADER_FONT, DATA_SIZE)
        c.drawString(col_x[0] + 2, y, "TOTALS")
        c.drawRightString(col_x[2] + COL_WIDTHS[2] - 2, y, _fmt(t_cost))
        c.drawRightString(col_x[5] + COL_WIDTHS[5] - 2, y, _fmt(t_prior))
        c.drawRightString(col_x[6] + COL_WIDTHS[6] - 2, y, _fmt(t_bonus))
        c.drawRightString(col_x[7] + COL_WIDTHS[7] - 2, y, _fmt(t_179))
        c.drawRightString(col_x[8] + COL_WIDTHS[8] - 2, y, _fmt(t_current))
        c.drawRightString(col_x[9] + COL_WIDTHS[9] - 2, y, _fmt(t_total))
        y -= ROW_H + 4
        c.line(LEFT, y + ROW_H - 2, RIGHT, y + ROW_H - 2)
        y -= ROW_H

        # Summary section
        c.setFont(BODY_FONT, DATA_SIZE)
        summary_label_x = LEFT + 20
        summary_val_x = LEFT + 280
        regular = t_current
        total_all = t_179 + t_bonus + regular

        summary_items = [
            ("Section 179 Expense:", t_179),
            ("Bonus Depreciation:", t_bonus),
            ("Regular MACRS Depreciation:", regular),
            ("Total Depreciation:", total_all),
        ]

        # AMT adjustment total
        amt_adj = ZERO
        for a in group_assets:
            fed_total = (a.prior_depreciation or ZERO) + (a.current_depreciation or ZERO)
            amt_total = (a.amt_prior_depreciation or ZERO) + (a.amt_current_depreciation or ZERO)
            amt_adj += amt_total - fed_total
        summary_items.append(("AMT Adjustment:", amt_adj))

        # GA bonus disallowed total
        ga_disallowed = sum(
            (a.state_bonus_disallowed or ZERO) for a in group_assets
        )
        summary_items.append(("GA Bonus Disallowed:", ga_disallowed))

        for label, val in summary_items:
            c.drawString(summary_label_x, y, label)
            c.drawRightString(summary_val_x, y, f"$ {_fmt(val) or '0'}")
            y -= ROW_H

        # Mark disposed assets footnote
        has_disposed = any(a.date_sold is not None for a in group_assets)
        if has_disposed:
            y -= ROW_H * 0.5
            c.setFont("Helvetica", 7)
            c.drawString(LEFT + 2, y, "* Disposed assets")

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.getvalue()


def render_amt_depreciation_schedule(tax_return, screen_mode: bool = False) -> bytes:
    """
    Render an AMT depreciation schedule report in landscape orientation.

    Shows AMT-specific columns: AMT Method, AMT Life, AMT Prior, AMT Current,
    AMT Adjustment (regular current - AMT current).
    """
    from apps.returns.models import DepreciationAsset

    entity = tax_return.tax_year.entity
    entity_name = entity.legal_name or entity.name
    year = tax_return.tax_year.year

    assets = DepreciationAsset.objects.filter(
        tax_return=tax_return,
    ).order_by("flow_to", "group_label", "description")

    if not assets.exists():
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(792, 612))
        c.showPage()
        c.save()
        buf.seek(0)
        return buf.getvalue()

    flow_labels = {
        "page1": "Page 1",
        "8825": "Form 8825",
        "sched_f": "Schedule F",
    }
    groups: dict[str, list] = {}
    for a in assets:
        key = a.flow_to or "page1"
        groups.setdefault(key, []).append(a)

    PAGE_W, PAGE_H = 792, 612
    LEFT = 36
    TOP = PAGE_H - 36
    RIGHT = PAGE_W - 36

    # Columns: Description(160), DateAcq(55), Cost(70), AMT Method(60), AMT Life(35),
    #          AMT Prior(75), AMT Current(75), Reg Current(75), AMT Adj(75)
    COL_WIDTHS = [160, 55, 70, 60, 35, 75, 75, 75, 75]
    COL_HEADERS = [
        "Description", "Date Acq", "Cost Basis", "AMT Method", "Life",
        "AMT Prior", "AMT Current", "Reg Current", "AMT Adj",
    ]

    col_x = []
    x = LEFT
    for w in COL_WIDTHS:
        col_x.append(x)
        x += w

    HEADER_FONT = "Helvetica-Bold"
    BODY_FONT = "Courier-Bold"
    TITLE_SIZE = 12
    COL_HEADER_SIZE = 7
    DATA_SIZE = 8
    ROW_H = 12

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    c.setFillColorRGB(*_data_color(screen_mode))

    def _fmt(val):
        if val is None:
            return ""
        d = Decimal(str(val))
        if d == 0:
            return ""
        if d < 0:
            return f"({abs(d):,.0f})"
        return f"{d:,.0f}"

    def _amt_method_display(a):
        if a.is_amortization:
            code = a.amort_code or "197"
            months = a.amort_months or 180
            return f"S/L {code}"
        method = a.method or ""
        amt_method = a.amt_method or ("150DB" if method == "200DB" else method)
        conv = a.convention or "HY"
        return f"{amt_method} {conv}"

    for flow_key, group_assets in groups.items():
        flow_label = flow_labels.get(flow_key, flow_key)
        y = TOP

        c.setFont(HEADER_FONT, TITLE_SIZE)
        c.drawCentredString(PAGE_W / 2, y, "AMT DEPRECIATION SCHEDULE")
        y -= ROW_H + 2
        c.setFont("Helvetica", 9)
        c.drawCentredString(PAGE_W / 2, y, f"{entity_name} \u2014 {year} Tax Return")
        y -= ROW_H
        c.drawCentredString(PAGE_W / 2, y, f"Flow: {flow_label}")
        y -= ROW_H + 8

        c.setFont(HEADER_FONT, COL_HEADER_SIZE)
        for i, hdr in enumerate(COL_HEADERS):
            if i >= 5:
                c.drawRightString(col_x[i] + COL_WIDTHS[i] - 2, y, hdr)
            else:
                c.drawString(col_x[i] + 2, y, hdr)
        y -= 2
        c.setLineWidth(0.5)
        c.line(LEFT, y, RIGHT, y)
        y -= ROW_H

        t_cost = ZERO
        t_amt_prior = ZERO
        t_amt_current = ZERO
        t_reg_current = ZERO
        t_amt_adj = ZERO

        c.setFont(BODY_FONT, DATA_SIZE)
        for a in group_assets:
            if y < 80:
                c.showPage()
                c.setPageSize((PAGE_W, PAGE_H))
                y = TOP
                c.setFont(HEADER_FONT, COL_HEADER_SIZE)
                for i, hdr in enumerate(COL_HEADERS):
                    if i >= 5:
                        c.drawRightString(col_x[i] + COL_WIDTHS[i] - 2, y, hdr)
                    else:
                        c.drawString(col_x[i] + 2, y, hdr)
                y -= 2
                c.line(LEFT, y, RIGHT, y)
                y -= ROW_H
                c.setFont(BODY_FONT, DATA_SIZE)

            is_disposed = a.date_sold is not None
            prefix = "*" if is_disposed else ""
            desc = f"{prefix}{a.description or ''}"[:24]
            c.drawString(col_x[0] + 2, y, desc)

            if a.date_acquired:
                c.drawString(col_x[1] + 2, y, a.date_acquired.strftime("%m/%Y"))

            c.drawRightString(col_x[2] + COL_WIDTHS[2] - 2, y, _fmt(a.cost_basis))
            c.drawString(col_x[3] + 2, y, _amt_method_display(a)[:9])

            amt_life = a.amt_life or a.life
            if amt_life is not None:
                life_str = str(int(amt_life)) if amt_life == int(amt_life) else str(amt_life)
                c.drawRightString(col_x[4] + COL_WIDTHS[4] - 2, y, life_str)

            amt_prior = a.amt_prior_depreciation or ZERO
            amt_current = a.amt_current_depreciation or ZERO
            reg_current = a.current_depreciation or ZERO
            amt_adj = reg_current - amt_current

            c.drawRightString(col_x[5] + COL_WIDTHS[5] - 2, y, _fmt(amt_prior))
            c.drawRightString(col_x[6] + COL_WIDTHS[6] - 2, y, _fmt(amt_current))
            c.drawRightString(col_x[7] + COL_WIDTHS[7] - 2, y, _fmt(reg_current))
            c.drawRightString(col_x[8] + COL_WIDTHS[8] - 2, y, _fmt(amt_adj))

            t_cost += a.cost_basis or ZERO
            t_amt_prior += amt_prior
            t_amt_current += amt_current
            t_reg_current += reg_current
            t_amt_adj += amt_adj

            y -= ROW_H

        # Totals row
        c.setLineWidth(0.5)
        c.line(LEFT, y + ROW_H - 2, RIGHT, y + ROW_H - 2)
        c.setFont(HEADER_FONT, DATA_SIZE)
        c.drawString(col_x[0] + 2, y, "TOTALS")
        c.drawRightString(col_x[2] + COL_WIDTHS[2] - 2, y, _fmt(t_cost))
        c.drawRightString(col_x[5] + COL_WIDTHS[5] - 2, y, _fmt(t_amt_prior))
        c.drawRightString(col_x[6] + COL_WIDTHS[6] - 2, y, _fmt(t_amt_current))
        c.drawRightString(col_x[7] + COL_WIDTHS[7] - 2, y, _fmt(t_reg_current))
        c.drawRightString(col_x[8] + COL_WIDTHS[8] - 2, y, _fmt(t_amt_adj))
        y -= ROW_H + 4
        c.line(LEFT, y + ROW_H - 2, RIGHT, y + ROW_H - 2)
        y -= ROW_H

        # Summary
        c.setFont(BODY_FONT, DATA_SIZE)
        lx = LEFT + 20
        vx = LEFT + 280
        for label, val in [
            ("Grand Total AMT Current:", t_amt_current),
            ("Grand Total Regular Current:", t_reg_current),
            ("Total AMT Adjustment (K15a):", t_amt_adj),
        ]:
            c.drawString(lx, y, label)
            c.drawRightString(vx, y, f"$ {_fmt(val) or '0'}")
            y -= ROW_H

        has_disposed = any(a.date_sold is not None for a in group_assets)
        if has_disposed:
            y -= ROW_H * 0.5
            c.setFont("Helvetica", 7)
            c.drawString(LEFT + 2, y, "* Disposed assets")

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Complete Return rendering (all forms combined)
# ---------------------------------------------------------------------------


# Valid package names for render_complete_return
PRINT_PACKAGES = {
    "client": "Client Copy",
    "filing": "Filing Copy",
    "extension": "Extension Package",
    "state": "State Only",
    "k1s": "K-1 Package",
    "invoice": "Invoice Only",
    "letter": "Letter Only",
}


def _render_me_statement(
    year: int,
    meals_50_fv,
    meals_dot_fv,
    entertainment_fv,
    screen_mode: bool = False,
) -> bytes | None:
    """Render a custom Meals & Entertainment statement page.

    Uses direct ReportLab drawing (not the generic statement renderer)
    to avoid the auto-total summing bug.
    """
    from decimal import Decimal as D

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFillColorRGB(*_data_color(screen_mode))
    PAGE_W, PAGE_H = letter
    LM = 1.0 * 72  # 1 inch
    RM = PAGE_W - 1.0 * 72
    y = PAGE_H - 1.0 * 72
    LH = 14  # line height

    def _fmt(val: Decimal) -> str:
        if val < 0:
            return f"({abs(val):,.0f})"
        return f"{val:,.0f}"

    # Title
    c.setFont("Helvetica-Bold", 12)
    c.drawString(LM, y, f"Form 1120-S ({year}) — Meals and Entertainment Statement")
    y -= LH * 1.5
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LM, y, "IRC Sec. 274 Limitation")
    y -= LH * 1.5
    c.setLineWidth(0.5)
    c.line(LM, y, RM, y)
    y -= LH * 1.2

    total_ded = D("0")
    total_nonded = D("0")

    # --- Meals (50% deductible) ---
    if meals_50_fv:
        amt = D(meals_50_fv.value.replace(",", ""))
        ded = (amt * D("0.50")).quantize(D("1"))
        nonded = amt - ded
        total_ded += ded
        total_nonded += nonded

        c.setFont("Helvetica-Bold", 10)
        c.drawString(LM, y, "Meals (50% deductible):")
        y -= LH
        c.setFont("Courier-Bold", 10)
        c.drawString(LM + 18, y, "Total meals expense:")
        c.drawRightString(RM, y, _fmt(amt))
        y -= LH
        c.drawString(LM + 18, y, "Allowable deduction (50%):")
        c.drawRightString(RM, y, _fmt(ded))
        y -= LH
        c.drawString(LM + 18, y, "Non-deductible portion:")
        c.drawRightString(RM, y, _fmt(nonded))
        y -= LH * 1.5

    # --- DOT Meals (80% deductible) ---
    if meals_dot_fv:
        amt = D(meals_dot_fv.value.replace(",", ""))
        ded = (amt * D("0.80")).quantize(D("1"))
        nonded = amt - ded
        total_ded += ded
        total_nonded += nonded

        c.setFont("Helvetica-Bold", 10)
        c.drawString(LM, y, "DOT Meals (80% deductible):")
        y -= LH
        c.setFont("Courier-Bold", 10)
        c.drawString(LM + 18, y, "Total DOT meals expense:")
        c.drawRightString(RM, y, _fmt(amt))
        y -= LH
        c.drawString(LM + 18, y, "Allowable deduction (80%):")
        c.drawRightString(RM, y, _fmt(ded))
        y -= LH
        c.drawString(LM + 18, y, "Non-deductible portion:")
        c.drawRightString(RM, y, _fmt(nonded))
        y -= LH * 1.5

    # --- Entertainment (0% deductible) ---
    if entertainment_fv:
        amt = D(entertainment_fv.value.replace(",", ""))
        total_nonded += amt

        c.setFont("Helvetica-Bold", 10)
        c.drawString(LM, y, "Entertainment (0% deductible):")
        y -= LH
        c.setFont("Courier-Bold", 10)
        c.drawString(LM + 18, y, "Total entertainment expense:")
        c.drawRightString(RM, y, _fmt(amt))
        y -= LH
        c.drawString(LM + 18, y, "Non-deductible portion:")
        c.drawRightString(RM, y, _fmt(amt))
        y -= LH * 1.5

    # --- SUMMARY ---
    c.setLineWidth(0.5)
    c.line(LM, y, RM, y)
    y -= LH * 1.2

    c.setFont("Helvetica-Bold", 10)
    c.drawString(LM, y, "SUMMARY")
    y -= LH * 1.2

    c.setFont("Courier-Bold", 10)
    c.drawString(LM + 18, y, "Total deductible meals:")
    c.drawRightString(RM, y, _fmt(total_ded))
    y -= LH
    c.drawString(LM + 18, y, "Total non-deductible expenses:")
    c.drawRightString(RM, y, _fmt(total_nonded))
    y -= LH * 1.2

    c.setFont("Courier-Bold", 9)
    c.drawString(LM + 36, y, "Reported on Schedule K, Line 16c")
    y -= LH
    c.drawString(LM + 36, y, "Reported on Schedule M-1, Line 3")
    y -= LH
    c.drawString(LM + 36, y, "Reported on Schedule M-2, Line 5")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def render_complete_return(
    tax_return,
    package: str | None = None,
    return_page_map: bool = False,
    screen_mode: bool = False,
) -> bytes | tuple[bytes, list[dict]]:
    """
    Render forms for a return as one continuous PDF.

    Args:
        tax_return: A TaxReturn model instance.
        package: Optional package name to select which forms to include.
        return_page_map: If True, return (pdf_bytes, page_map) tuple
            where page_map is a list of {"form": str, "page": int} dicts.

    Returns:
        PDF bytes, or (pdf_bytes, page_map) if return_page_map=True.
    """
    import logging
    from apps.returns.models import FormFieldValue, RentalProperty, Shareholder

    _screen_mode_ctx.set(screen_mode)
    logger = logging.getLogger(__name__)
    writer = PdfWriter()
    page_map: list[dict] = []  # tracks form name for each page

    # Pages to skip: {form_name_prefix: set of page indices (0-based)}
    # Page index 1 = second page of the source PDF (instructions-only pages)
    SKIP_PAGES: dict[str, set[int]] = {
        "Form 8879-S": {1},      # page 2 is IRS instructions only
        "Form 1125-A": {1, 2},   # pages 2-3 are IRS instructions
    }

    def _append(pdf_bytes: bytes, form_name: str = "Unknown") -> None:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)
        skip = SKIP_PAGES.get(form_name, set())
        for p, page in enumerate(reader.pages):
            if p in skip:
                continue
            writer.add_page(page)
            actual_pages = num_pages - len(skip)
            if actual_pages > 1:
                # Renumber pages after skipping
                visible_idx = sum(1 for i in range(p) if i not in skip) + 1
                page_map.append({"form": f"{form_name} (p.{visible_idx})", "page": len(page_map) + 1})
            else:
                page_map.append({"form": form_name, "page": len(page_map) + 1})

    def _result(pdf_bytes: bytes):
        if return_page_map:
            return pdf_bytes, page_map
        return pdf_bytes

    # --- Form display names ---
    form_code = tax_return.form_definition.code
    _FORM_NAMES = {
        "1120-S": "Form 1120-S",
        "1065": "Form 1065",
        "1120": "Form 1120",
    }
    main_form_name = _FORM_NAMES.get(form_code, f"Form {form_code}")

    # --- Single-form packages ---
    if package == "invoice":
        result = render_invoice(tax_return)
        return _result(result) if not return_page_map else (result, [{"form": "Invoice", "page": 1}])

    if package == "letter":
        result = render_letter(tax_return)
        return _result(result) if not return_page_map else (result, [{"form": "Letter", "page": 1}])

    if package == "extension":
        result = render_7004(tax_return)
        return _result(result) if not return_page_map else (result, [{"form": "Form 7004", "page": 1}])

    if package == "state":
        for sr in tax_return.state_returns.all():
            if sr.form_definition.code == "GA-600S":
                _append(render_ga600s_overlay(sr), "GA Form 600S")
            else:
                _append(render_tax_return(sr), sr.form_definition.code)
        output = io.BytesIO()
        writer.write(output)
        return _result(output.getvalue())

    if package == "k1s":
        result = render_all_k1s(tax_return)
        if return_page_map:
            reader = PdfReader(io.BytesIO(result))
            pm = [{"form": "Schedule K-1", "page": i + 1} for i in range(len(reader.pages))]
            return result, pm
        return result

    # --- Multi-form packages: "client", "filing", or None (all) ---
    include_letter = package in ("client", None)
    include_invoice = package in ("client", None)

    # 0a. Letter (client copy and all-forms only)
    if include_letter:
        try:
            _append(render_letter(tax_return), "Letter")
        except Exception as e:
            logger.warning("render_complete: letter failed: %s", e)

    # 0b. Invoice (client copy and all-forms only)
    if include_invoice:
        try:
            _append(render_invoice(tax_return), "Invoice")
        except Exception as e:
            logger.warning("render_complete: invoice failed: %s", e)

    # 1. Main return (e.g. 1120-S pages 1-5)
    try:
        _append(render_tax_return(tax_return), main_form_name)
    except Exception as e:
        logger.warning("render_complete: main form failed: %s", e)

    # 1b. Form 8879-S (e-file signature auth — Client Copy and Filing Copy)
    if package in ("client", "filing", None):
        try:
            _append(render_8879s(tax_return), "Form 8879-S")
        except Exception as e:
            logger.warning("render_complete: 8879-S failed: %s", e)

    # 2. Form 1125-A (COGS) — only if Schedule A has non-zero data
    try:
        has_cogs = FormFieldValue.objects.filter(
            tax_return=tax_return,
            form_line__section__code="sched_a",
        ).exclude(value__in=["", "0", "0.00"]).exists()
        if has_cogs:
            _append(render_1125a(tax_return), "Form 1125-A")
    except Exception as e:
        logger.warning("render_complete: 1125-A failed: %s", e)

    # 2b. Form 1125-E (Officer Compensation) — only if officers exist
    try:
        from apps.returns.models import Officer
        if Officer.objects.filter(tax_return=tax_return).exists():
            _append(render_1125e(tax_return), "Form 1125-E")
    except Exception as e:
        logger.warning("render_complete: 1125-E failed: %s", e)

    # 3. Form 8825 (Rental Real Estate) — only if rental properties exist
    try:
        if RentalProperty.objects.filter(tax_return=tax_return).exists():
            _append(render_8825(tax_return), "Form 8825")
    except Exception as e:
        logger.warning("render_complete: 8825 failed: %s", e)

    # 3b. Form 4562 (Depreciation) — only if depreciation assets exist
    try:
        from apps.returns.models import DepreciationAsset
        if DepreciationAsset.objects.filter(tax_return=tax_return).exists():
            _append(render_4562(tax_return), "Form 4562")
    except Exception as e:
        logger.warning("render_complete: 4562 failed: %s", e)

    # 3c. Form 4797 (Sales of Business Property) — only if disposed assets exist
    try:
        if DepreciationAsset.objects.filter(
            tax_return=tax_return, date_sold__isnull=False,
        ).exists():
            _append(render_4797(tax_return), "Form 4797")
    except Exception as e:
        logger.warning("render_complete: 4797 failed: %s", e)

    # 3c2. Schedule D / Form 8949 — only if capital dispositions exist
    try:
        from apps.returns.models import Disposition
        if Disposition.objects.filter(
            tax_return=tax_return, is_4797=False,
        ).exists():
            _append(render_8949(tax_return), "Form 8949")
            _append(render_schedule_d(tax_return), "Schedule D")
    except Exception as e:
        logger.warning("render_complete: Schedule D / 8949 failed: %s", e)

    # 3e. Depreciation Schedule (if depreciation assets exist)
    has_assets = DepreciationAsset.objects.filter(tax_return=tax_return).exists()
    try:
        if has_assets:
            _append(render_depreciation_schedule(tax_return), "Depreciation Schedule")
    except Exception as e:
        logger.warning("render_complete: depreciation schedule failed: %s", e)

    # 3f. AMT Depreciation Schedule
    try:
        if has_assets:
            _append(render_amt_depreciation_schedule(tax_return), "AMT Depreciation Schedule")
    except Exception as e:
        logger.warning("render_complete: AMT depreciation schedule failed: %s", e)

    # 3d. Meals and Entertainment Statement — if meals data exists
    try:
        meals_50 = FormFieldValue.objects.filter(
            tax_return=tax_return, form_line__line_number="D_MEALS_50",
        ).exclude(value__in=["", "0"]).first()
        meals_dot = FormFieldValue.objects.filter(
            tax_return=tax_return, form_line__line_number="D_MEALS_DOT",
        ).exclude(value__in=["", "0"]).first()
        entertainment = FormFieldValue.objects.filter(
            tax_return=tax_return, form_line__line_number="D_ENTERTAINMENT",
        ).exclude(value__in=["", "0"]).first()
        if meals_50 or meals_dot or entertainment:
            from decimal import Decimal as D
            year = tax_return.tax_year.year
            stmt_bytes = _render_me_statement(
                year, meals_50, meals_dot, entertainment,
            )
            if stmt_bytes:
                _append(stmt_bytes, "M&E Statement")
    except Exception as e:
        logger.warning("render_complete: meals statement failed: %s", e)

    # 4-6: Shareholder-level forms (1120-S only)
    if form_code == "1120-S":
        shareholders = Shareholder.objects.filter(
            tax_return=tax_return, is_active=True,
        ).order_by("sort_order", "name")

        if shareholders.exists():
            # 4. All K-1s
            try:
                _append(render_all_k1s(tax_return), "Schedule K-1")
            except Exception as e:
                logger.warning("render_complete: K-1s failed: %s", e)

            # 5. All 7203s
            try:
                _append(render_all_7203s(tax_return), "Form 7203")
            except Exception as e:
                logger.warning("render_complete: 7203s failed: %s", e)

            # 6. Form 7206 per shareholder with health insurance
            for sh in shareholders:
                if sh.health_insurance_premium and sh.health_insurance_premium > 0:
                    try:
                        _append(render_7206(tax_return, sh), f"Form 7206 ({sh.name})")
                    except Exception as e:
                        logger.warning("render_complete: 7206 for %s failed: %s", sh.name, e)

    # 7. Form 7004 (Extension) — only if extension was filed
    if tax_return.extension_filed:
        try:
            _append(render_7004(tax_return), "Form 7004")
        except Exception as e:
            logger.warning("render_complete: 7004 failed: %s", e)

    # 8. State returns
    for sr in tax_return.state_returns.all():
        try:
            if sr.form_definition.code == "GA-600S":
                _append(render_ga600s_overlay(sr), "GA Form 600S")
            else:
                _append(render_tax_return(sr), sr.form_definition.code)
        except Exception as e:
            logger.warning("render_complete: state %s failed: %s", sr.form_definition.code, e)

    output = io.BytesIO()
    writer.write(output)
    return _result(output.getvalue())
