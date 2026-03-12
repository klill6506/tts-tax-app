"""
Invoice PDF generator.

Renders a professional single-page invoice:
- Firm header (name, address, phone)
- Client code + date
- Client/entity address block
- Federal and state forms lists
- Fee summary with amount due

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
LEFT_MARGIN = 0.75 * inch
RIGHT_MARGIN = 0.75 * inch
USABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

# Fonts
HEADER_FONT = "Helvetica-Bold"
BODY_FONT = "Helvetica"
FIRM_NAME_SIZE = 14
HEADER_SIZE = 11
BODY_SIZE = 10
SMALL_SIZE = 9
INDENT = 20  # indent for form list items

LINE_HEIGHT = 14


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
        addr_parts = []
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
        "client_code": client.name,
        "entity_name": entity.legal_name or entity.name,
        "address": entity.address_line1 or "",
        "city_state_zip": csz,
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


def _format_currency(value: str) -> str:
    """Format a value string as whole-dollar currency (no dollar sign, no decimals)."""
    if not value:
        return "0"
    clean = value.replace(",", "").replace("$", "").strip()
    try:
        d = Decimal(clean)
        if d < 0:
            return f"({abs(d):,.0f})"
        return f"{d:,.0f}"
    except InvalidOperation:
        return "0"


def _to_decimal(value: str) -> Decimal:
    """Parse string to Decimal, default 0."""
    if not value:
        return Decimal("0")
    clean = value.replace(",", "").replace("$", "").strip()
    try:
        return Decimal(clean)
    except InvalidOperation:
        return Decimal("0")


def _get_forms_list(tax_return) -> tuple[list[str], list[str]]:
    """Build federal and state forms lists based on what exists."""
    from apps.returns.models import FormFieldValue, RentalProperty, Shareholder

    federal_forms = []
    state_forms = []

    form_code = tax_return.form_definition.code

    # Always include main form
    if form_code == "1120-S":
        federal_forms.append("Form 1120S U.S. Income Tax Return for an S Corporation")
    elif form_code == "1065":
        federal_forms.append("Form 1065 U.S. Return of Partnership Income")
    elif form_code == "1120":
        federal_forms.append("Form 1120 U.S. Corporation Income Tax Return")

    # K-1s if shareholders exist
    if form_code == "1120-S":
        sh_count = Shareholder.objects.filter(
            tax_return=tax_return, is_active=True
        ).count()
        if sh_count > 0:
            federal_forms.append(f"Schedule K-1 Shareholder's Share ({sh_count})")

    # Form 8879
    federal_forms.append("Form 8879-CORP IRS e-file Signature Authorization")

    # 7203 if shareholders exist
    if form_code == "1120-S":
        sh_count = Shareholder.objects.filter(
            tax_return=tax_return, is_active=True
        ).count()
        if sh_count > 0:
            federal_forms.append(f"Form 7203 S Corporation Shareholder Basis ({sh_count})")

    # 1125-A if COGS data
    has_cogs = FormFieldValue.objects.filter(
        tax_return=tax_return,
        form_line__section__code="sched_a",
    ).exclude(value__in=["", "0", "0.00"]).exists()
    if has_cogs:
        federal_forms.append("Form 1125-A Cost of Goods Sold")

    # 8825 if rental properties
    if RentalProperty.objects.filter(tax_return=tax_return).exists():
        federal_forms.append("Form 8825 Rental Real Estate Income and Expenses")

    # Depreciation placeholder
    federal_forms.append("Depreciation Schedules")

    # State forms
    for sr in tax_return.state_returns.all():
        sc = sr.form_definition.code
        if sc == "GA-600S":
            state_forms.append("Form 600S Georgia S Corporation Tax Return")
            # Check for state balance due
            ga_balance = _get_field_value(tax_return, "LTR_GA_BALANCE")
            if _to_decimal(ga_balance) > 0:
                state_forms.append("Form PV CORP Georgia Payment Voucher")
            state_forms.append("GA-8453 S Georgia e-file Signature Authorization")
            state_forms.append("Georgia Depreciation Schedules")

    return federal_forms, state_forms


def render_invoice(tax_return) -> bytes:
    """
    Render a single-page invoice PDF for a tax return.

    Layout: firm header, client info, forms lists, fee summary.
    """
    firm_info = _get_firm_info(tax_return)
    client_info = _get_client_info(tax_return)
    federal_forms, state_forms = _get_forms_list(tax_return)

    # Fee data from admin fields
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

    today_str = date.today().strftime("%m/%d/%Y")
    right_x = PAGE_WIDTH - RIGHT_MARGIN

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    y = PAGE_HEIGHT - 0.75 * inch

    # --- Firm name (bold, larger) ---
    if firm_info["firm_name"]:
        c.setFont(HEADER_FONT, FIRM_NAME_SIZE)
        c.drawString(LEFT_MARGIN, y, firm_info["firm_name"])
        y -= LINE_HEIGHT + 2

    # --- Firm address ---
    c.setFont(BODY_FONT, BODY_SIZE)
    if firm_info["firm_address"]:
        c.drawString(LEFT_MARGIN, y, firm_info["firm_address"])
        y -= LINE_HEIGHT

    # --- Firm city, state, zip ---
    if firm_info["firm_city_state_zip"]:
        c.drawString(LEFT_MARGIN, y, firm_info["firm_city_state_zip"])
        y -= LINE_HEIGHT

    # --- Firm phone ---
    if firm_info["firm_phone"]:
        c.drawString(LEFT_MARGIN, y, firm_info["firm_phone"])
        y -= LINE_HEIGHT

    # --- Blank space ---
    y -= LINE_HEIGHT

    # --- Client code (left-aligned) ---
    c.setFont(BODY_FONT, BODY_SIZE)
    c.drawString(LEFT_MARGIN, y, f"Client {client_info['client_code']}")
    y -= LINE_HEIGHT

    # --- Current date (left-aligned) ---
    c.drawString(LEFT_MARGIN, y, today_str)
    y -= LINE_HEIGHT

    # --- Blank space ---
    y -= LINE_HEIGHT

    # --- Client/entity name (bold) ---
    c.setFont(HEADER_FONT, BODY_SIZE)
    c.drawString(LEFT_MARGIN, y, client_info["entity_name"])
    y -= LINE_HEIGHT

    # --- Client address ---
    c.setFont(BODY_FONT, BODY_SIZE)
    if client_info["address"]:
        c.drawString(LEFT_MARGIN, y, client_info["address"])
        y -= LINE_HEIGHT

    # --- Client city, state, zip ---
    if client_info["city_state_zip"]:
        c.drawString(LEFT_MARGIN, y, client_info["city_state_zip"])
        y -= LINE_HEIGHT

    # --- Blank space ---
    y -= LINE_HEIGHT

    # --- FEDERAL FORMS header ---
    if federal_forms:
        c.setFont(HEADER_FONT, HEADER_SIZE)
        c.drawString(LEFT_MARGIN, y, "FEDERAL FORMS")
        y -= LINE_HEIGHT

        # List of federal forms (indented)
        c.setFont(BODY_FONT, SMALL_SIZE)
        for form_name in federal_forms:
            c.drawString(LEFT_MARGIN + INDENT, y, form_name)
            y -= LINE_HEIGHT

    # --- Blank space ---
    y -= LINE_HEIGHT * 0.5

    # --- GEORGIA FORMS header (only if state forms exist) ---
    if state_forms:
        c.setFont(HEADER_FONT, HEADER_SIZE)
        c.drawString(LEFT_MARGIN, y, "GEORGIA FORMS")
        y -= LINE_HEIGHT

        # List of state forms (indented)
        c.setFont(BODY_FONT, SMALL_SIZE)
        for form_name in state_forms:
            c.drawString(LEFT_MARGIN + INDENT, y, form_name)
            y -= LINE_HEIGHT

        # Blank space after state forms
        y -= LINE_HEIGHT * 0.5

    # --- Blank space ---
    y -= LINE_HEIGHT * 0.5

    # --- FEE SUMMARY header ---
    c.setFont(HEADER_FONT, HEADER_SIZE)
    c.drawString(LEFT_MARGIN, y, "FEE SUMMARY")
    y -= LINE_HEIGHT + 2

    # --- Preparation Fee ---
    c.setFont(BODY_FONT, BODY_SIZE)
    c.drawString(LEFT_MARGIN + INDENT, y, "Preparation Fee")
    c.drawRightString(right_x, y, _format_currency(fee_data.get("prep_fee", "")))
    y -= LINE_HEIGHT

    # --- Optional Fee 2 ---
    if fee_data.get("fee_2") and _to_decimal(fee_data["fee_2"]) != 0:
        desc = fee_data.get("fee_2_desc", "Additional Fee")
        c.drawString(LEFT_MARGIN + INDENT, y, desc)
        c.drawRightString(right_x, y, _format_currency(fee_data["fee_2"]))
        y -= LINE_HEIGHT

    # --- Optional Fee 3 ---
    if fee_data.get("fee_3") and _to_decimal(fee_data["fee_3"]) != 0:
        desc = fee_data.get("fee_3_desc", "Additional Fee")
        c.drawString(LEFT_MARGIN + INDENT, y, desc)
        c.drawRightString(right_x, y, _format_currency(fee_data["fee_3"]))
        y -= LINE_HEIGHT

    # --- Memo (if present) ---
    if fee_data.get("memo"):
        y -= 2
        c.setFont(BODY_FONT, SMALL_SIZE)
        c.drawString(LEFT_MARGIN + INDENT, y, f"Memo: {fee_data['memo']}")
        y -= LINE_HEIGHT

    # --- Thin separator line ---
    y -= 4
    c.setLineWidth(0.5)
    c.line(right_x - 120, y, right_x, y)
    y -= LINE_HEIGHT

    # --- Amount Due (bold) ---
    c.setFont(HEADER_FONT, BODY_SIZE)
    c.drawString(LEFT_MARGIN + INDENT, y, "Amount Due")
    c.drawRightString(right_x, y, _format_currency(fee_data.get("total", "")))

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
