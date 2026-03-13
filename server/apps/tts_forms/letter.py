"""
Client Letter PDF generator.

Renders a premium professional client transmittal letter with:
- Bold outer border + gray shaded band frame (Lacerte-style)
- Centered letterhead (firm name, address, phone — all caps, bold)
- Left-aligned body (date, client address, paragraphs, closing)

Usage:
    from apps.tts_forms.letter import render_letter
    pdf_bytes = render_letter(tax_return)
"""

import io
from datetime import date
from decimal import Decimal, InvalidOperation

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter as LETTER_SIZE
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = LETTER_SIZE

# Frame dimensions — bold outer border + gray band + white inner
OUTER_MARGIN = 0.5 * inch       # distance from page edge to outer black border
BAND_WIDTH = 18                  # ~0.25 inch gray band width (points)
INNER_INSET = 0.5 * inch        # padding from inner border to content

# Content area (inside the gray band + padding)
LEFT_MARGIN = OUTER_MARGIN + BAND_WIDTH + INNER_INSET
RIGHT_MARGIN = OUTER_MARGIN + BAND_WIDTH + INNER_INSET
TOP_MARGIN = OUTER_MARGIN + BAND_WIDTH + INNER_INSET
BOTTOM_MARGIN = OUTER_MARGIN + BAND_WIDTH + INNER_INSET
USABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

# Fonts
HEADER_FONT = "Helvetica-Bold"
BODY_FONT = "Helvetica"

# Sizes
FIRM_NAME_SIZE = 16
FIRM_DETAIL_SIZE = 12
BODY_SIZE = 11
SMALL_SIZE = 9
BODY_LEADING = 15  # line height for body text

# Gray band color
BAND_COLOR = colors.Color(0.82, 0.82, 0.82)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_field_value(tax_return, line_number: str) -> str:
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


def _fmt_amount(value: str) -> str:
    """Format as whole dollars: 1,234 or (1,234)."""
    d = _to_decimal(value)
    if d < 0:
        return f"({abs(d):,.0f})"
    return f"{abs(d):,.0f}"


def _wrap_text(text: str, c: canvas.Canvas, font: str, size: float, max_width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
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


def _draw_frame(c: canvas.Canvas):
    """Draw the Lacerte-style decorative frame: bold outer border + gray band."""
    c.saveState()

    # Gray filled rectangle (outer border area)
    c.setFillColor(BAND_COLOR)
    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    c.rect(
        OUTER_MARGIN, OUTER_MARGIN,
        PAGE_WIDTH - 2 * OUTER_MARGIN,
        PAGE_HEIGHT - 2 * OUTER_MARGIN,
        fill=1, stroke=1,
    )

    # White inner rectangle (content area)
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(
        OUTER_MARGIN + BAND_WIDTH, OUTER_MARGIN + BAND_WIDTH,
        PAGE_WIDTH - 2 * OUTER_MARGIN - 2 * BAND_WIDTH,
        PAGE_HEIGHT - 2 * OUTER_MARGIN - 2 * BAND_WIDTH,
        fill=1, stroke=1,
    )

    # Bold outer border on top (drawn last so it's crisp)
    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    c.rect(
        OUTER_MARGIN, OUTER_MARGIN,
        PAGE_WIDTH - 2 * OUTER_MARGIN,
        PAGE_HEIGHT - 2 * OUTER_MARGIN,
        fill=0, stroke=1,
    )

    c.restoreState()


# ---------------------------------------------------------------------------
# LetterWriter
# ---------------------------------------------------------------------------

class LetterWriter:
    """Stateful writer that tracks y position and handles page breaks."""

    def __init__(self, c: canvas.Canvas):
        self.c = c
        self.y = PAGE_HEIGHT - TOP_MARGIN

    def _check_page(self, needed: float = BODY_LEADING * 2):
        if self.y < BOTTOM_MARGIN + needed:
            self.c.showPage()
            _draw_frame(self.c)
            self.c.setFillColor(colors.black)
            self.y = PAGE_HEIGHT - TOP_MARGIN

    def skip(self, lines: float = 1):
        self.y -= BODY_LEADING * lines
        self._check_page()

    def write(self, text: str, font: str = BODY_FONT, size: float = BODY_SIZE, indent: float = 0):
        self._check_page()
        self.c.setFont(font, size)
        self.c.drawString(LEFT_MARGIN + indent, self.y, text)
        self.y -= BODY_LEADING

    def write_centered(self, text: str, font: str = BODY_FONT, size: float = BODY_SIZE):
        self._check_page()
        self.c.setFont(font, size)
        self.c.drawCentredString(PAGE_WIDTH / 2, self.y, text)
        self.y -= BODY_LEADING

    def write_right(self, text: str, font: str = BODY_FONT, size: float = BODY_SIZE):
        self._check_page()
        self.c.setFont(font, size)
        self.c.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, self.y, text)
        self.y -= BODY_LEADING

    def write_wrapped(self, text: str, font: str = BODY_FONT, size: float = BODY_SIZE, indent: float = 0):
        max_w = USABLE_WIDTH - indent
        lines = _wrap_text(text, self.c, font, size, max_w)
        for line in lines:
            self._check_page()
            self.c.setFont(font, size)
            self.c.drawString(LEFT_MARGIN + indent, self.y, line)
            self.y -= BODY_LEADING


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------

def render_letter(tax_return) -> bytes:
    """Render a client transmittal letter PDF."""
    entity = tax_return.tax_year.entity
    year = tax_return.tax_year.year
    form_code = tax_return.form_definition.code
    today_str = date.today().strftime("%B %d, %Y")

    # Firm info from PreparerInfo
    firm_name = ""
    firm_address = ""
    firm_csz = ""
    firm_phone = ""
    preparer_name = ""
    try:
        prep = tax_return.preparer_info
        firm_name = (prep.firm_name or "").upper()
        firm_address = (prep.firm_address or "").upper()
        csz_parts = [p.upper() for p in [prep.firm_city, prep.firm_state] if p]
        csz = ", ".join(csz_parts)
        if prep.firm_zip:
            csz += f" {prep.firm_zip}"
        firm_csz = csz
        firm_phone = prep.firm_phone or ""
        preparer_name = prep.preparer_name or ""
    except Exception:
        pass

    # Entity info
    entity_name = (entity.legal_name or entity.name or "").upper()
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

    has_state = tax_return.state_returns.exists()

    # Form name for letter text
    form_name_map = {
        "1120-S": "S Corporation Income Tax",
        "1065": "Partnership",
        "1120": "Corporation Income Tax",
    }
    form_name = form_name_map.get(form_code, "Income Tax")

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER_SIZE)

    # Draw the decorative frame first (background layer)
    _draw_frame(c)

    # Explicitly reset fill color to black for text drawing
    c.setFillColor(colors.black)

    w = LetterWriter(c)

    # -----------------------------------------------------------------------
    # Centered Letterhead — ALL CAPS, BOLD
    # -----------------------------------------------------------------------
    if firm_name:
        w.write_centered(firm_name, HEADER_FONT, FIRM_NAME_SIZE)
    if firm_address:
        w.write_centered(firm_address, HEADER_FONT, FIRM_DETAIL_SIZE)
    if firm_csz:
        w.write_centered(firm_csz, HEADER_FONT, FIRM_DETAIL_SIZE)
    if firm_phone:
        w.write_centered(firm_phone, HEADER_FONT, FIRM_DETAIL_SIZE)

    w.skip(2)

    # -----------------------------------------------------------------------
    # Date (right-aligned)
    # -----------------------------------------------------------------------
    w.write_right(today_str)
    w.skip(1)

    # -----------------------------------------------------------------------
    # Client address block
    # -----------------------------------------------------------------------
    w.write(entity_name)
    if entity_addr:
        w.write(entity_addr)
    if entity_csz:
        w.write(entity_csz)

    w.skip(1)

    # -----------------------------------------------------------------------
    # Salutation
    # -----------------------------------------------------------------------
    w.write("Dear Client:")
    w.skip(0.5)

    # -----------------------------------------------------------------------
    # Federal paragraph
    # -----------------------------------------------------------------------
    is_electronic = filing_method and filing_method.lower() in ("e-file", "electronic")
    fed_bal = _to_decimal(fed_balance)

    if is_electronic:
        fed_text = (
            f"Your {year} Federal {form_name} return will be electronically filed "
            f"with the Internal Revenue Service upon receipt of a signed "
            f"Form 8879-CORP, E-file Authorization for Corporations."
        )
    else:
        fed_text = (
            f"Enclosed is your {year} Federal {form_name} return. "
            f"Please sign the return and mail it to the Internal Revenue Service "
            f"at the address shown on the return."
        )

    if fed_bal == 0:
        fed_text += " No tax is payable with the filing of this return."
    elif fed_bal > 0:
        fed_text += (
            f" There is a balance of ${_fmt_amount(fed_balance)} payable by "
            f"{fed_due_date or 'the due date shown on the return'}."
        )

    w.write_wrapped(fed_text)
    w.skip(0.5)

    # -----------------------------------------------------------------------
    # EFTPS paragraph (only if federal balance > 0)
    # -----------------------------------------------------------------------
    if fed_bal > 0:
        w.write_wrapped(
            "The payment(s) due must be electronically deposited through the "
            "Electronic Federal Tax Payment System (EFTPS). To enroll in EFTPS, "
            "visit www.eftps.gov or call 1-800-555-4477. Allow 5 to 7 business "
            "days to receive your PIN."
        )
        w.skip(0.5)

    # -----------------------------------------------------------------------
    # Georgia paragraph (only if state return exists)
    # -----------------------------------------------------------------------
    if has_state:
        ga_bal = _to_decimal(ga_balance)
        is_state_electronic = st_filing and st_filing.lower() in ("e-file", "electronic")

        if is_state_electronic:
            ga_text = (
                f"Your {year} Georgia {form_name} return will be electronically "
                f"filed with the State of Georgia upon receipt of a "
                f"signed GA-8453 S."
            )
        else:
            ga_text = (
                f"Enclosed is your {year} Georgia {form_name} return. "
                f"Please sign and mail to the Georgia Department of Revenue."
            )

        if ga_bal == 0:
            ga_text += " No tax is payable with the filing of this return."
        elif ga_bal > 0:
            ga_text += (
                f" There is a balance of ${_fmt_amount(ga_balance)} payable by "
                f"{ga_due_date or 'the due date shown on the return'}."
            )

        w.write_wrapped(ga_text)

        if ga_bal > 0:
            w.skip(0.5)
            w.write_wrapped(
                "Make the check payable to Georgia Department of Revenue. "
                "Mail the payment with Form PV CORP to:"
            )
            w.skip(0.5)
            w.write("Georgia Department of Revenue", indent=36)
            w.write("Processing Center", indent=36)
            w.write("P.O. Box 740318", indent=36)
            w.write("Atlanta, GA 30374-0318", indent=36)

        w.skip(0.5)

    # -----------------------------------------------------------------------
    # K-1 paragraph (always for 1120-S)
    # -----------------------------------------------------------------------
    if form_code == "1120-S":
        w.write_wrapped(
            f"You must distribute a copy of the {year} Schedule K-1 to each "
            f"shareholder. Be sure to give each shareholder a copy of the "
            f"Shareholder's Instructions for Schedule K-1 (Form 1120S)."
        )
        w.skip(0.5)

    # -----------------------------------------------------------------------
    # Estimated tax table
    # -----------------------------------------------------------------------
    if est_taxes:
        w.write_wrapped(
            f"The following estimated tax payments are due for tax year {year + 1}:"
        )
        w.skip(0.5)

        col1_x = LEFT_MARGIN + 36
        col2_x = LEFT_MARGIN + 200
        w.c.setFont(HEADER_FONT, SMALL_SIZE)
        w.c.drawString(col1_x, w.y, "Due Date")
        w.c.drawRightString(col2_x + 80, w.y, "Federal")
        w.y -= BODY_LEADING

        # Separator line
        w.c.setLineWidth(0.25)
        w.c.line(col1_x, w.y + BODY_LEADING * 0.4, col2_x + 80, w.y + BODY_LEADING * 0.4)

        total_est = Decimal("0")
        w.c.setFont(BODY_FONT, SMALL_SIZE)
        for dt, amt in est_taxes:
            w.c.drawString(col1_x, w.y, dt or "")
            w.c.drawRightString(col2_x + 80, w.y, _fmt_amount(amt))
            total_est += _to_decimal(amt)
            w.y -= BODY_LEADING

        # Total line
        w.c.setLineWidth(0.5)
        w.c.line(col2_x + 10, w.y + BODY_LEADING * 0.4, col2_x + 80, w.y + BODY_LEADING * 0.4)
        w.c.setFont(HEADER_FONT, SMALL_SIZE)
        w.c.drawString(col1_x, w.y, "Total")
        w.c.drawRightString(col2_x + 80, w.y, _fmt_amount(str(total_est)))
        w.y -= BODY_LEADING

        w.skip(0.5)

    # -----------------------------------------------------------------------
    # Custom note
    # -----------------------------------------------------------------------
    if custom_note:
        w.write_wrapped(custom_note)
        w.skip(0.5)

    # -----------------------------------------------------------------------
    # Closing
    # -----------------------------------------------------------------------
    w.write_wrapped("Please call if you have any questions.")
    w.skip(1.5)
    w.write("Sincerely,")
    w.skip(2)
    if preparer_name:
        w.write(preparer_name)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
