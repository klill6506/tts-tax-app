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

from .coordinates.f1065 import FIELD_MAP as F1065_FIELD_MAP
from .coordinates.f1065 import HEADER_FIELDS as F1065_HEADER_FIELDS
from .coordinates.f1120 import FIELD_MAP as F1120_FIELD_MAP
from .coordinates.f1120 import HEADER_FIELDS as F1120_HEADER_FIELDS
from .coordinates.f1120s import FIELD_MAP as F1120S_FIELD_MAP
from .coordinates.f1120s import HEADER_FIELDS as F1120S_HEADER_FIELDS
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
from .coordinates.fga600s import FIELD_MAP as FGA600S_FIELD_MAP
from .coordinates.fga600s import HEADER_FIELDS as FGA600S_HEADER_FIELDS
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
    "f1065": F1065_FIELD_MAP,
    "f1120": F1120_FIELD_MAP,
    "f1120sk1": F1120SK1_FIELD_MAP,
    "f7206": F7206_FIELD_MAP,
    "f1125a": F1125A_FIELD_MAP,
    "f8825": F8825_FIELD_MAP,
    "f7203": F7203_FIELD_MAP,
    "f7004": F7004_FIELD_MAP,
    "fga600s": FGA600S_FIELD_MAP,
}

HEADER_REGISTRY: dict[str, dict[str, FieldCoord]] = {
    "f1120s": F1120S_HEADER_FIELDS,
    "f1065": F1065_HEADER_FIELDS,
    "f1120": F1120_HEADER_FIELDS,
    "f1120sk1": F1120SK1_HEADER,
    "f7206": F7206_HEADER_FIELDS,
    "f1125a": F1125A_HEADER_FIELDS,
    "f8825": F8825_HEADER_FIELDS,
    "f7203": F7203_HEADER_FIELDS,
    "f7004": F7004_HEADER_FIELDS,
    "fga600s": FGA600S_HEADER_FIELDS,
}

# Form code → 2-digit IRS extension code for Form 7004 Line 1
EXTENSION_FORM_CODES: dict[str, str] = {
    "1120-S": "25",
    "1065": "09",
    "1120": "12",
}

# Font settings
DEFAULT_FONT = "Courier"
DEFAULT_FONT_SIZE = 10


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


def _expand_yes_no(field_values: dict[str, tuple[str, str]]) -> None:
    """Expand Schedule B boolean fields into _yes / _no coordinate keys.

    The coordinate map uses suffixed keys (e.g. B3_yes, B3_no) so the "X"
    lands in the correct column.  This mutates *field_values* in place:

    - B3 = ("true", "boolean")  → B3_yes = ("X", "text")
    - B3 = ("false", "boolean") → B3_no  = ("X", "text")

    Non-boolean B-lines (like B8 currency) are left unchanged.
    """
    to_expand = [
        (k, v) for k, v in field_values.items()
        if k.startswith("B") and v[1] == "boolean"
    ]
    for key, (value, _ftype) in to_expand:
        del field_values[key]
        if value.lower() in ("true", "yes", "1", "x"):
            field_values[f"{key}_yes"] = ("X", "text")
        else:
            field_values[f"{key}_no"] = ("X", "text")


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

    # Read template PDF and strip fillable form field widgets (purple backgrounds)
    template_reader = _flatten_template(PdfReader(str(template_path)))
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
        "1065": "f1065",
        "1120": "f1120",
        "GA-600S": "fga600s",
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
    _expand_yes_no(field_values)

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

    # Tax year dates (used by 1065, 1120, K-1 — not rendered on 1120-S)
    if tax_return.tax_year_start:
        header["tax_year_begin"] = tax_return.tax_year_start.strftime("%m/%d/%Y")
    else:
        header["tax_year_begin"] = f"01/01/{tax_year.year}"
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

    # Product or service
    if tax_return.product_or_service:
        header["product_or_service"] = tax_return.product_or_service

    # Business activity code
    if tax_return.business_activity_code:
        header["business_activity_code"] = tax_return.business_activity_code

    # Total assets — pull from balance sheet L15d (end-of-year total assets)
    from apps.returns.models import FormFieldValue as _FFV

    try:
        l15d = _FFV.objects.filter(
            tax_return=tax_return, form_line__line_number="L15d"
        ).first()
        if l15d and l15d.value:
            header["total_assets"] = _format_currency(l15d.value)
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

    return header


# ---------------------------------------------------------------------------
# Schedule K-1 rendering
# ---------------------------------------------------------------------------

# Maps Schedule K line_number → K-1 Part III field key(s)
# For simple lines, maps to a single amount field.
# For coded lines (16), maps to code+amount pair.
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
    "K9": "9",
    "K10": "10",
    "K11": "11",
    "K12a": "12",
}

# K16 sub-items: (Schedule K line, K-1 code letter, code_field, amount_field)
K16_ITEMS = [
    ("K16a", "A", "16_code_1", "16_amt_1"),
    ("K16b", "B", "16_code_2", "16_amt_2"),
    ("K16c", "C", "16_code_3", "16_amt_3"),
    ("K16d", "D", "16_code_4", "16_amt_4"),
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

    header_data = {
        "corp_ein": entity.ein or "",
        "corp_name": entity.legal_name or entity.name,
        "corp_address": entity.address_line1 or "",
        "corp_city_state_zip": city_state_zip,
        "tax_year_begin": f"01/01/{year}",
        "tax_year_end": f"12/31/{year}",
        "sh_ssn": shareholder.ssn or "",
        "sh_name": shareholder.name,
        "sh_address": shareholder.address_line1 or "",
        "sh_city_state_zip": sh_city_state_zip,
        "sh_ownership_pct": f"{shareholder.ownership_percentage}",
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
        if ln.startswith("K"):
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
        share = (amount * ownership_pct).quantize(Decimal("0.01"))
        field_values[k1_line] = (str(share), "currency")

    # K16 sub-items (code+amount pairs)
    for k_line, code_letter, code_field, amt_field in K16_ITEMS:
        if k_line == "K16d":
            # Distributions: use per-shareholder amount, not pro rata
            amount = shareholder.distributions
        else:
            raw = k_values.get(k_line, "")
            if not raw:
                continue
            try:
                amount = (Decimal(raw) * ownership_pct).quantize(Decimal("0.01"))
            except InvalidOperation:
                continue
        if amount == 0:
            continue
        field_values[code_field] = (code_letter, "text")
        field_values[amt_field] = (str(amount), "currency")

    # Line 17 code AC: health insurance (if applicable)
    if shareholder.health_insurance_premium and shareholder.health_insurance_premium > 0:
        field_values["17_code_1"] = ("AC", "text")
        field_values["17_amt_1"] = (str(shareholder.health_insurance_premium), "currency")

    return render(
        form_id="f1120sk1",
        tax_year=tax_year_applicable,
        field_values=field_values,
        header_data=header_data,
    )


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
        if ln.startswith("A") and len(ln) >= 2:
            # Map A1 -> 1, A2 -> 2, etc.
            form_line = ln[1:]
            if form_line.isdigit() and fv.value:
                field_values[form_line] = (fv.value, "currency")

    return render(
        form_id="f1125a",
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
    field_values: dict[str, tuple[str, str]] = {}
    columns = "ABCD"
    total_income = Decimal("0")
    total_expenses = Decimal("0")

    for idx, prop in enumerate(properties[:8]):  # max 8 properties (2 pages)
        page_idx = idx // 4
        col = columns[idx % 4]
        prefix = f"p{page_idx}_{col}"

        # Property description fields
        addr_key = f"{prefix}_addr"
        if addr_key in F8825_PROPERTY_FIELDS:
            field_values[addr_key] = (prop.description, "text")
        type_key = f"{prefix}_type"
        if type_key in F8825_PROPERTY_FIELDS:
            field_values[type_key] = (prop.property_type, "text")
        days_key = f"{prefix}_fair_days"
        if days_key in F8825_PROPERTY_FIELDS:
            field_values[days_key] = (str(prop.fair_rental_days), "text")
        pdays_key = f"{prefix}_personal_days"
        if pdays_key in F8825_PROPERTY_FIELDS:
            field_values[pdays_key] = (str(prop.personal_use_days), "text")

        # Expense lines
        for model_field, line_num in _RENTAL_EXPENSE_LINES:
            amount = getattr(prop, model_field, Decimal("0"))
            if amount and amount != 0:
                key = f"{prefix}_{line_num}"
                field_values[key] = (str(amount), "currency")

        # Computed lines
        prop_total_exp = prop.total_expenses
        prop_income = prop.rents_received
        prop_net = prop.net_rent

        # Line 2c: total rental income (same as 2a for us, 2b is usually 0)
        if prop_income != 0:
            field_values[f"{prefix}_2c"] = (str(prop_income), "currency")

        # Line 18: total expenses
        if prop_total_exp != 0:
            field_values[f"{prefix}_18"] = (str(prop_total_exp), "currency")

        # Line 19: net income (loss) per property
        if prop_net != 0:
            field_values[f"{prefix}_19"] = (str(prop_net), "currency")

        total_income += prop_income
        total_expenses += prop_total_exp

    # Summary lines (totals across all properties)
    total_net = total_income - total_expenses
    if total_income != 0:
        field_values["20a"] = (str(total_income), "currency")
    if total_expenses != 0:
        field_values["20b"] = (str(total_expenses), "currency")
    if total_net != 0:
        field_values["21"] = (str(total_net), "currency")

    # Merge property description fields into the coordinate map
    # so _create_overlay can find them
    combined_map = dict(F8825_FIELD_MAP)
    combined_map.update(F8825_PROPERTY_FIELDS)

    template_path = _get_template_path("f8825", tax_year_applicable)
    if not template_path.exists():
        raise FileNotFoundError(
            f"IRS PDF template not found at {template_path}. "
            f"Run scripts/update_irs_forms.py to download."
        )

    header_map = HEADER_REGISTRY.get("f8825")
    template_reader = _flatten_template(PdfReader(str(template_path)))
    page_count = len(template_reader.pages)

    overlay_buf = _create_overlay(
        field_values=field_values,
        field_map=combined_map,
        header_data=header_data,
        header_map=header_map,
        page_count=page_count,
    )
    overlay_reader = PdfReader(overlay_buf)

    writer = PdfWriter()
    for i in range(page_count):
        template_page = template_reader.pages[i]
        if i < len(overlay_reader.pages):
            overlay_page = overlay_reader.pages[i]
            template_page.merge_page(overlay_page)
        writer.add_page(template_page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


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
    city_state_zip = ", ".join(p for p in [entity.city, entity.state] if p)
    if entity.zip_code:
        city_state_zip += f" {entity.zip_code}"

    header_data = {
        "entity_name": entity.legal_name or entity.name,
        "ein": entity.ein or "",
        "address_street": entity.address_line1 or "",
        "address_city_state_zip": city_state_zip,
    }

    # Build field values
    field_values: dict[str, tuple[str, str]] = {
        "1": (ext_code, "text"),
    }

    # Line 5a: tax year dates
    if tax_return.tax_year_start:
        begin = tax_return.tax_year_start
    else:
        from datetime import date
        begin = date(year, 1, 1)

    if tax_return.tax_year_end:
        end = tax_return.tax_year_end
    else:
        from datetime import date
        end = date(year, 12, 31)

    field_values["5a_year"] = (str(begin.year), "text")
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
