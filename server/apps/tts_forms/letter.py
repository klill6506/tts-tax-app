"""
Client Letter PDF generator.

Renders a professional client transmittal letter matching the Lacerte format.
Uses LTR_* fields from the Admin tab.

Usage:
    from apps.tts_forms.letter import render_letter
    pdf_bytes = render_letter(tax_return)
"""

import io
from datetime import date
from decimal import Decimal, InvalidOperation

from reportlab.lib.pagesizes import letter as LETTER_SIZE
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = LETTER_SIZE
LEFT_MARGIN = 1.0 * inch
RIGHT_MARGIN = 1.0 * inch
TOP_MARGIN = 0.75 * inch
BOTTOM_MARGIN = 0.75 * inch
USABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

HEADER_FONT = "Helvetica-Bold"
BODY_FONT = "Helvetica"
HEADER_SIZE = 12
BODY_SIZE = 10
SMALL_SIZE = 9
LINE_HEIGHT = 14


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
    if not value:
        return Decimal("0")
    clean = value.replace(",", "").replace("$", "").strip()
    try:
        return Decimal(clean)
    except InvalidOperation:
        return Decimal("0")


def _fmt_currency(value: str) -> str:
    d = _to_decimal(value)
    if d < 0:
        return f"(${abs(d):,.2f})"
    return f"${d:,.2f}"


def _wrap_text(text: str, c: canvas.Canvas, font: str, size: float, max_width: float) -> list[str]:
    """Word-wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if c.stringWidth(test, font, size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


class LetterWriter:
    """Stateful writer that tracks y position and handles page breaks."""

    def __init__(self, c: canvas.Canvas):
        self.c = c
        self.y = PAGE_HEIGHT - TOP_MARGIN

    def _check_page(self, needed: float = LINE_HEIGHT * 2):
        if self.y < BOTTOM_MARGIN + needed:
            self.c.showPage()
            self.y = PAGE_HEIGHT - TOP_MARGIN

    def skip(self, lines: float = 1):
        self.y -= LINE_HEIGHT * lines
        self._check_page()

    def write(self, text: str, font: str = BODY_FONT, size: float = BODY_SIZE, indent: float = 0):
        self._check_page()
        self.c.setFont(font, size)
        self.c.drawString(LEFT_MARGIN + indent, self.y, text)
        self.y -= LINE_HEIGHT

    def write_wrapped(self, text: str, font: str = BODY_FONT, size: float = BODY_SIZE, indent: float = 0):
        max_w = USABLE_WIDTH - indent
        lines = _wrap_text(text, self.c, font, size, max_w)
        for line in lines:
            self._check_page()
            self.c.setFont(font, size)
            self.c.drawString(LEFT_MARGIN + indent, self.y, line)
            self.y -= LINE_HEIGHT

    def write_right(self, text: str, font: str = BODY_FONT, size: float = BODY_SIZE):
        self._check_page()
        self.c.setFont(font, size)
        self.c.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, self.y, text)
        self.y -= LINE_HEIGHT

    def draw_line(self):
        self._check_page()
        self.c.setLineWidth(0.5)
        self.c.line(LEFT_MARGIN, self.y, PAGE_WIDTH - RIGHT_MARGIN, self.y)
        self.y -= LINE_HEIGHT * 0.5


def render_letter(tax_return) -> bytes:
    """Render a client transmittal letter PDF."""
    entity = tax_return.tax_year.entity
    year = tax_return.tax_year.year
    form_code = tax_return.form_definition.code
    today_str = date.today().strftime("%B %d, %Y")

    # Firm info
    firm_name = ""
    firm_address = ""
    firm_csz = ""
    firm_phone = ""
    preparer_name = ""
    try:
        prep = tax_return.preparer_info
        firm_name = prep.firm_name or ""
        firm_address = prep.firm_address or ""
        csz = ", ".join(p for p in [prep.firm_city, prep.firm_state] if p)
        if prep.firm_zip:
            csz += f" {prep.firm_zip}"
        firm_csz = csz
        firm_phone = prep.firm_phone or ""
        preparer_name = prep.preparer_name or ""
    except Exception:
        pass

    # Entity info
    entity_name = entity.legal_name or entity.name
    entity_addr = entity.address_line1 or ""
    entity_csz = ", ".join(p for p in [entity.city, entity.state] if p)
    if entity.zip_code:
        entity_csz += f" {entity.zip_code}"

    # LTR fields
    filing_method = _get_field_value(tax_return, "LTR_FILING_METHOD")
    st_filing = _get_field_value(tax_return, "LTR_ST_FILING")
    fed_balance = _get_field_value(tax_return, "LTR_FED_BALANCE")
    fed_due_date = _get_field_value(tax_return, "LTR_FED_DUE_DATE")
    ga_balance = _get_field_value(tax_return, "LTR_GA_BALANCE")
    ga_due_date = _get_field_value(tax_return, "LTR_GA_DUE_DATE")
    custom_note = _get_field_value(tax_return, "LTR_CUSTOM_NOTE")

    # Estimated tax payments
    est_taxes = []
    for i in range(1, 5):
        amt = _get_field_value(tax_return, f"LTR_EST_TAX_{i}")
        dt = _get_field_value(tax_return, f"LTR_EST_DATE_{i}")
        if _to_decimal(amt) > 0:
            est_taxes.append((dt, amt))

    # Check for state return
    has_state = tax_return.state_returns.exists()

    # Form name for letter
    form_name_map = {
        "1120-S": "S Corporation Income Tax",
        "1065": "Partnership",
        "1120": "Corporation Income Tax",
    }
    form_name = form_name_map.get(form_code, "Income Tax")

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER_SIZE)
    w = LetterWriter(c)

    # --- Firm Header ---
    if firm_name:
        w.write(firm_name, HEADER_FONT, HEADER_SIZE)
    if firm_address:
        w.write(firm_address, BODY_FONT, BODY_SIZE)
    if firm_csz:
        w.write(firm_csz, BODY_FONT, BODY_SIZE)
    if firm_phone:
        w.write(f"Phone: {firm_phone}", BODY_FONT, BODY_SIZE)

    w.skip(1.5)

    # --- Date ---
    w.write(today_str)
    w.skip(1)

    # --- Client address block ---
    w.write(entity_name)
    if entity_addr:
        w.write(entity_addr)
    if entity_csz:
        w.write(entity_csz)

    w.skip(1)

    # --- Salutation ---
    w.write("Dear Client:")
    w.skip(0.5)

    # --- Federal paragraph ---
    is_electronic = filing_method and filing_method.lower() in ("e-file", "electronic")
    fed_bal = _to_decimal(fed_balance)

    if is_electronic:
        w.write_wrapped(
            f"Your {year} Federal {form_name} return will be electronically filed "
            f"with the Internal Revenue Service upon receipt of a signed "
            f"Form 8879-CORP, IRS e-file Signature Authorization."
        )
    else:
        w.write_wrapped(
            f"Enclosed is your {year} Federal {form_name} return. "
            f"Please sign the return and mail it to the Internal Revenue Service "
            f"at the address shown on the return."
        )

    w.skip(0.5)

    if fed_bal == 0:
        w.write_wrapped("No tax is payable with the filing of this return.")
    elif fed_bal > 0:
        w.write_wrapped(
            f"There is a balance of {_fmt_currency(fed_balance)} payable by "
            f"{fed_due_date or 'the due date shown on the return'}."
        )

    w.skip(0.5)

    # --- EFTPS paragraph (only if federal balance > 0) ---
    if fed_bal > 0:
        w.write_wrapped(
            "The payment(s) due must be electronically deposited through the "
            "Electronic Federal Tax Payment System (EFTPS). To enroll in EFTPS, "
            "visit www.eftps.gov or call 1-800-555-4477. Allow 5 to 7 business "
            "days to receive your PIN."
        )
        w.skip(0.5)

    # --- Georgia paragraph (only if state return exists) ---
    if has_state:
        ga_bal = _to_decimal(ga_balance)
        is_state_electronic = st_filing and st_filing.lower() in ("e-file", "electronic")

        if is_state_electronic:
            w.write_wrapped(
                f"Your {year} Georgia {form_name} return will be electronically "
                f"filed with the Georgia Department of Revenue upon receipt of a "
                f"signed GA-8453 S, Georgia Individual Income Tax Declaration for "
                f"Electronic Filing."
            )
        else:
            w.write_wrapped(
                f"Enclosed is your {year} Georgia {form_name} return. "
                f"Please sign and mail to the Georgia Department of Revenue."
            )

        w.skip(0.5)

        if ga_bal == 0:
            w.write_wrapped(
                "No tax is payable with the filing of your Georgia return."
            )
        elif ga_bal > 0:
            w.write_wrapped(
                f"There is a balance of {_fmt_currency(ga_balance)} payable by "
                f"{ga_due_date or 'the due date shown on the return'}. "
                f"Make the check payable to Georgia Department of Revenue. "
                f"Mail the payment with Form PV CORP to:"
            )
            w.skip(0.5)
            w.write("Georgia Department of Revenue", indent=36)
            w.write("Processing Center", indent=36)
            w.write("P.O. Box 740318", indent=36)
            w.write("Atlanta, GA 30374-0318", indent=36)

        w.skip(0.5)

    # --- Estimated tax table ---
    if est_taxes:
        w.write_wrapped(
            f"The following estimated tax payments are due for tax year {year + 1}:"
        )
        w.skip(0.5)

        # Table header
        col1_x = LEFT_MARGIN + 36
        col2_x = LEFT_MARGIN + 200
        w.c.setFont(HEADER_FONT, SMALL_SIZE)
        w.c.drawString(col1_x, w.y, "Due Date")
        w.c.drawRightString(col2_x + 80, w.y, "Federal")
        w.y -= LINE_HEIGHT

        # Separator
        w.c.setLineWidth(0.25)
        w.c.line(col1_x, w.y + LINE_HEIGHT * 0.4, col2_x + 80, w.y + LINE_HEIGHT * 0.4)

        # Rows
        total_est = Decimal("0")
        w.c.setFont(BODY_FONT, SMALL_SIZE)
        for dt, amt in est_taxes:
            w.c.drawString(col1_x, w.y, dt or "")
            w.c.drawRightString(col2_x + 80, w.y, _fmt_currency(amt))
            total_est += _to_decimal(amt)
            w.y -= LINE_HEIGHT

        # Total
        w.c.setLineWidth(0.5)
        w.c.line(col2_x + 10, w.y + LINE_HEIGHT * 0.4, col2_x + 80, w.y + LINE_HEIGHT * 0.4)
        w.c.setFont(HEADER_FONT, SMALL_SIZE)
        w.c.drawString(col1_x, w.y, "Total")
        w.c.drawRightString(col2_x + 80, w.y, _fmt_currency(str(total_est)))
        w.y -= LINE_HEIGHT

        w.skip(0.5)

    # --- Custom note ---
    if custom_note:
        w.write_wrapped(custom_note)
        w.skip(0.5)

    # --- K-1 reminder (1120-S only) ---
    if form_code == "1120-S":
        w.write_wrapped(
            f"You must distribute a copy of the {year} Schedule K-1 to each "
            f"shareholder of the corporation. Each shareholder should use the "
            f"information reported on their K-1 to complete their individual "
            f"income tax return."
        )
        w.skip(0.5)

    # --- Closing ---
    w.write_wrapped("Please call if you have any questions.")
    w.skip(1.5)
    w.write("Sincerely,")
    w.skip(2)
    if preparer_name:
        w.write(preparer_name)
    if firm_name:
        w.write(firm_name)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
