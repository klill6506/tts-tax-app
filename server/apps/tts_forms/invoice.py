"""
Invoice PDF generator.

Renders a professional single-page invoice matching the Lacerte format:
- Firm header (name, address, phone) — left-aligned
- Client code + date
- Client/entity address block with phone
- Federal and state forms lists (columnar)
- Fee summary with dollar amounts (dollars and cents for invoices)

Usage:
    from apps.tts_forms.invoice import render_invoice
    pdf_bytes = render_invoice(tax_return)
"""

import io
from datetime import date
from decimal import Decimal, InvalidOperation

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = letter  # 612 x 792
LEFT_MARGIN = 1.0 * inch
RIGHT_MARGIN = 1.0 * inch
RIGHT_X = PAGE_WIDTH - RIGHT_MARGIN
USABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

# Fonts
FIRM_NAME_FONT = "Helvetica-Bold"
HEADER_FONT = "Helvetica-Bold"
BODY_FONT = "Helvetica"
FIRM_NAME_SIZE = 14
BODY_SIZE = 10
FORM_SIZE = 10
SECTION_HEADER_SIZE = 10

LINE_HEIGHT = 14
SECTION_GAP = LINE_HEIGHT * 1.2  # space between sections

# Column positions for forms list
FORM_NUM_X = LEFT_MARGIN
FORM_DESC_X = LEFT_MARGIN + 100  # align descriptions

# Fee summary layout
FEE_LABEL_X = LEFT_MARGIN
FEE_AMOUNT_X = RIGHT_X


def _get_firm_info(tax_return) -> dict[str, str]:
    """Extract firm header info from PreparerInfo."""
    info = {
        "firm_name": "",
        "firm_address": "",
        "firm_city_state_zip": "",
        "firm_phone": "",
        "preparer_name": "",
    }
    try:
        prep = tax_return.preparer_info
        info["firm_name"] = prep.firm_name or ""
        if prep.firm_address:
            info["firm_address"] = prep.firm_address
        csz = ", ".join(p for p in [prep.firm_city, prep.firm_state] if p)
        if prep.firm_zip:
            csz += f" {prep.firm_zip}"
        info["firm_city_state_zip"] = csz
        if prep.firm_phone:
            info["firm_phone"] = prep.firm_phone
        if prep.preparer_name:
            info["preparer_name"] = prep.preparer_name
    except Exception:
        pass
    return info


def _get_client_info(tax_return) -> dict[str, str]:
    """Extract client/entity info."""
    entity = tax_return.tax_year.entity
    client = entity.client
    csz = ", ".join(p for p in [entity.city, entity.state] if p)
    if entity.zip_code:
        csz += f" {entity.zip_code}"
    return {
        "client_code": (client.name or "").upper(),
        "entity_name": (entity.legal_name or entity.name or "").upper(),
        "address": entity.address_line1 or "",
        "city_state_zip": csz,
        "phone": entity.phone or "",
        "ein": entity.ein or "",
    }


def _get_field_value(tax_return, line_number: str) -> str:
    """Get a single FormFieldValue by line_number."""
    from apps.returns.models import FormFieldValue

    try:
        fv = FormFieldValue.objects.filter(
            tax_return=tax_return,
            form_line__line_number=line_number,
        ).first()
        return fv.value if fv else ""
    except Exception:
        return ""


def _to_decimal(value: str) -> Decimal:
    """Parse string to Decimal, default 0."""
    if not value:
        return Decimal("0")
    clean = value.replace(",", "").replace("$", "").strip()
    try:
        return Decimal(clean)
    except InvalidOperation:
        return Decimal("0")


def _format_fee(value: str) -> str:
    """Format as dollars and cents with $ sign for invoice fee lines."""
    d = _to_decimal(value)
    if d < 0:
        return f"$ ({abs(d):,.2f})"
    return f"$ {d:,.2f}"


def _get_forms_list(tax_return) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Build federal and state forms lists as (form_number, description) tuples."""
    from apps.returns.models import (
        DepreciationAsset,
        FormFieldValue,
        RentalProperty,
        Shareholder,
    )

    federal: list[tuple[str, str]] = []
    state: list[tuple[str, str]] = []

    form_code = tax_return.form_definition.code
    year = tax_return.tax_year.year

    # Main form
    if form_code == "1120-S":
        federal.append(("Form 1120S", f"{year} U.S. S Corporation Income Tax Return"))
    elif form_code == "1065":
        federal.append(("Form 1065", f"{year} U.S. Return of Partnership Income"))
    elif form_code == "1120":
        federal.append(("Form 1120", f"{year} U.S. Corporation Income Tax Return"))

    # K-1s
    if form_code == "1120-S":
        sh_count = Shareholder.objects.filter(
            tax_return=tax_return, is_active=True
        ).count()
        if sh_count > 0:
            federal.append(("Schedule K-1", "Shareholder's Income, Deductions, Credits, etc."))

    # 7203
    if form_code == "1120-S":
        sh_count = Shareholder.objects.filter(
            tax_return=tax_return, is_active=True
        ).count()
        if sh_count > 0:
            federal.append(("Form 7203", "S Corporation Shareholder Basis Limitation"))

    # 1125-A (COGS)
    has_cogs = FormFieldValue.objects.filter(
        tax_return=tax_return,
        form_line__section__code="sched_a",
    ).exclude(value__in=["", "0", "0.00"]).exists()
    if has_cogs:
        federal.append(("Form 1125-A", "Cost of Goods Sold"))

    # 1125-E (Officer Compensation)
    from apps.returns.models import Officer
    if Officer.objects.filter(tax_return=tax_return).exists():
        federal.append(("Form 1125-E", "Compensation of Officers"))

    # 8825 (Rental)
    if RentalProperty.objects.filter(tax_return=tax_return).exists():
        federal.append(("Form 8825", "Rental Real Estate Income and Expenses"))

    # 4562 (Depreciation)
    if DepreciationAsset.objects.filter(tax_return=tax_return).exists():
        federal.append(("Form 4562", "Depreciation and Amortization"))

    # 4797 (Dispositions)
    if DepreciationAsset.objects.filter(
        tax_return=tax_return, date_sold__isnull=False
    ).exists():
        federal.append(("Form 4797", "Sales of Business Property"))

    # 8879
    if form_code == "1120-S":
        federal.append(("Form 8879-CORP", "E-file Authorization for Corporations"))
    else:
        federal.append(("Form 8879-CORP", "E-file Authorization for Corporations"))

    # State forms
    for sr in tax_return.state_returns.all():
        sc = sr.form_definition.code
        if sc == "GA-600S":
            state.append(("Form 600S", f"{year} Georgia S Corporation Tax Return"))
            state.append(("8453S", "Georgia Declaration for Electronic Filing"))

    return federal, state


def render_invoice(tax_return) -> bytes:
    """Render a single-page invoice PDF for a tax return."""
    firm = _get_firm_info(tax_return)
    client = _get_client_info(tax_return)
    federal_forms, state_forms = _get_forms_list(tax_return)

    # Fee data
    fee_data = {
        "prep_fee": _get_field_value(tax_return, "INV_PREP_FEE"),
        "fee_2_desc": _get_field_value(tax_return, "INV_FEE_2_DESC"),
        "fee_2": _get_field_value(tax_return, "INV_FEE_2"),
        "fee_3_desc": _get_field_value(tax_return, "INV_FEE_3_DESC"),
        "fee_3": _get_field_value(tax_return, "INV_FEE_3"),
        "memo": _get_field_value(tax_return, "INV_MEMO"),
        "total": _get_field_value(tax_return, "INV_TOTAL"),
    }

    # Compute total if not stored
    if not fee_data["total"]:
        total = (
            _to_decimal(fee_data["prep_fee"])
            + _to_decimal(fee_data["fee_2"])
            + _to_decimal(fee_data["fee_3"])
        )
        fee_data["total"] = str(total)

    today_str = date.today().strftime("%B %d, %Y")  # "March 11, 2026"

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    y = PAGE_HEIGHT - 1.0 * inch

    # --- Firm name (bold, larger) ---
    if firm["firm_name"]:
        c.setFont(FIRM_NAME_FONT, FIRM_NAME_SIZE)
        c.drawString(LEFT_MARGIN, y, firm["firm_name"])
        y -= LINE_HEIGHT + 2

    # Firm address lines
    c.setFont(BODY_FONT, BODY_SIZE)
    if firm["firm_address"]:
        c.drawString(LEFT_MARGIN, y, firm["firm_address"])
        y -= LINE_HEIGHT
    if firm["firm_city_state_zip"]:
        c.drawString(LEFT_MARGIN, y, firm["firm_city_state_zip"])
        y -= LINE_HEIGHT
    if firm["firm_phone"]:
        c.drawString(LEFT_MARGIN, y, firm["firm_phone"])
        y -= LINE_HEIGHT

    # Blank line
    y -= SECTION_GAP

    # --- Client code + date ---
    c.setFont(BODY_FONT, BODY_SIZE)
    c.drawString(LEFT_MARGIN, y, f"Client {client['client_code']}")
    y -= LINE_HEIGHT
    c.drawString(LEFT_MARGIN, y, today_str)
    y -= LINE_HEIGHT

    # Blank line
    y -= SECTION_GAP

    # --- Client/entity address block ---
    c.setFont(BODY_FONT, BODY_SIZE)
    c.drawString(LEFT_MARGIN, y, client["entity_name"])
    y -= LINE_HEIGHT
    if client["address"]:
        c.drawString(LEFT_MARGIN, y, client["address"])
        y -= LINE_HEIGHT
    if client["city_state_zip"]:
        c.drawString(LEFT_MARGIN, y, client["city_state_zip"])
        y -= LINE_HEIGHT
    if client["phone"]:
        c.drawString(LEFT_MARGIN, y, client["phone"])
        y -= LINE_HEIGHT

    # Blank line
    y -= SECTION_GAP

    # --- FEDERAL FORMS ---
    if federal_forms:
        c.setFont(HEADER_FONT, SECTION_HEADER_SIZE)
        c.drawString(LEFT_MARGIN, y, "FEDERAL FORMS")
        y -= LINE_HEIGHT + 2

        c.setFont(BODY_FONT, FORM_SIZE)
        for form_num, form_desc in federal_forms:
            c.drawString(FORM_NUM_X, y, form_num)
            c.drawString(FORM_DESC_X, y, form_desc)
            y -= LINE_HEIGHT

    # Blank line
    y -= SECTION_GAP * 0.5

    # --- GEORGIA FORMS ---
    if state_forms:
        c.setFont(HEADER_FONT, SECTION_HEADER_SIZE)
        c.drawString(LEFT_MARGIN, y, "GEORGIA FORMS")
        y -= LINE_HEIGHT + 2

        c.setFont(BODY_FONT, FORM_SIZE)
        for form_num, form_desc in state_forms:
            c.drawString(FORM_NUM_X, y, form_num)
            c.drawString(FORM_DESC_X, y, form_desc)
            y -= LINE_HEIGHT

        y -= SECTION_GAP * 0.5

    # Blank line
    y -= SECTION_GAP * 0.5

    # --- FEE SUMMARY ---
    c.setFont(HEADER_FONT, SECTION_HEADER_SIZE)
    c.drawString(LEFT_MARGIN, y, "FEE SUMMARY")
    y -= LINE_HEIGHT + 4

    # Preparation Fee
    c.setFont(BODY_FONT, BODY_SIZE)
    c.drawString(FEE_LABEL_X, y, "Preparation Fee")
    c.drawRightString(FEE_AMOUNT_X, y, _format_fee(fee_data["prep_fee"]))
    y -= LINE_HEIGHT

    # Optional Fee 2
    if fee_data.get("fee_2") and _to_decimal(fee_data["fee_2"]) != 0:
        desc = fee_data.get("fee_2_desc") or "Additional Fee"
        c.drawString(FEE_LABEL_X, y, desc)
        c.drawRightString(FEE_AMOUNT_X, y, _format_fee(fee_data["fee_2"]))
        y -= LINE_HEIGHT

    # Optional Fee 3
    if fee_data.get("fee_3") and _to_decimal(fee_data["fee_3"]) != 0:
        desc = fee_data.get("fee_3_desc") or "Additional Fee"
        c.drawString(FEE_LABEL_X, y, desc)
        c.drawRightString(FEE_AMOUNT_X, y, _format_fee(fee_data["fee_3"]))
        y -= LINE_HEIGHT

    # Thin separator line
    y -= 6
    c.setLineWidth(0.5)
    c.line(FEE_AMOUNT_X - 120, y + 4, FEE_AMOUNT_X, y + 4)
    y -= LINE_HEIGHT * 0.5

    # Amount Due (bold)
    c.setFont(HEADER_FONT, BODY_SIZE)
    c.drawString(FEE_LABEL_X, y, "Amount Due")
    c.drawRightString(FEE_AMOUNT_X, y, _format_fee(fee_data["total"]))

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
