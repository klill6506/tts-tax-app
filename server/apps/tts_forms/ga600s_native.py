"""
Georgia Form 600S — Native PDF Generator.

Generates a complete GA-600S from scratch using ReportLab, matching the
official form's content and layout. This replaces the old coordinate overlay
approach — the DOR's PDF is flat (no AcroForm) and low quality.

Professional tax software (Lacerte, Drake) generates its own renditions of
state forms rather than overlaying on government PDFs. This follows that
same approach.

Usage:
    from apps.tts_forms.ga600s_native import render_ga600s_native
    pdf_bytes = render_ga600s_native(tax_return)
"""

import io
from decimal import Decimal, InvalidOperation

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = letter  # 612 x 792

# Margins
MARGIN_LEFT = 0.6 * inch
MARGIN_RIGHT = 0.6 * inch
MARGIN_TOP = 0.5 * inch
MARGIN_BOTTOM = 0.5 * inch

CONTENT_LEFT = MARGIN_LEFT
CONTENT_RIGHT = PAGE_WIDTH - MARGIN_RIGHT
CONTENT_WIDTH = CONTENT_RIGHT - CONTENT_LEFT

# Fonts
TITLE_FONT = "Helvetica-Bold"
LABEL_FONT = "Helvetica"
VALUE_FONT = "Helvetica-Bold"
SMALL_FONT = "Helvetica"

TITLE_SIZE = 12
SECTION_HEADER_SIZE = 9
LABEL_SIZE = 8
VALUE_SIZE = 9
SMALL_SIZE = 7
HEADER_LABEL_SIZE = 7.5
HEADER_VALUE_SIZE = 9

# Line spacing
ROW_HEIGHT = 13
SECTION_GAP = 6

# Colors
HEADER_BG = colors.Color(0.15, 0.22, 0.35)   # Dark navy for form title
SECTION_BG = colors.Color(0.90, 0.92, 0.95)   # Light blue-gray for section headers
LINE_COLOR = colors.Color(0.70, 0.70, 0.70)   # Light gray grid lines
DIVIDER_COLOR = colors.Color(0.40, 0.40, 0.40)

ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _d(val: str) -> Decimal:
    """Parse string to Decimal, default 0."""
    if not val:
        return ZERO
    clean = val.replace(",", "").replace("$", "").replace("(", "-").replace(")", "").strip()
    try:
        return Decimal(clean)
    except InvalidOperation:
        return ZERO


def _fmt_currency(val: str) -> str:
    """Format as whole-dollar currency: 1,234 or (1,234)."""
    d = _d(val)
    if d == 0:
        return ""
    if d < 0:
        return f"({abs(d):,.0f})"
    return f"{d:,.0f}"


def _fmt_pct(val: str) -> str:
    """Format percentage: 1.000000 or 100%."""
    d = _d(val)
    if d == 0:
        return ""
    if d == 1:
        return "1.000000"
    return str(d)


def _get_field_values(tax_return) -> dict[str, str]:
    """Load all FormFieldValues for a state return into a dict."""
    from apps.returns.models import FormFieldValue

    result = {}
    for fv in FormFieldValue.objects.filter(
        tax_return=tax_return
    ).select_related("form_line"):
        result[fv.form_line.line_number] = fv.value or ""
    return result


def _get_entity_data(tax_return) -> dict[str, str]:
    """Extract entity/header data from the state return and its federal parent."""
    entity = tax_return.tax_year.entity
    year = tax_return.tax_year.year

    data = {
        "entity_name": entity.legal_name or entity.name or "",
        "ein": entity.ein or "",
        "address": entity.address_line1 or "",
        "city": entity.city or "",
        "state": entity.state or "GA",
        "zip": entity.zip_code or "",
        "phone": entity.phone or "",
        "naics": entity.naics_code or "",
        "business_type": entity.business_activity or "",
        "inc_date": "",
        "inc_state": entity.state_incorporated or "",
        "year": str(year),
    }

    if entity.date_incorporated:
        data["inc_date"] = entity.date_incorporated.strftime("%m/%d/%Y")

    # Shareholder count from the federal return
    federal = tax_return.federal_return
    if federal:
        from apps.returns.models import Shareholder
        sh_count = Shareholder.objects.filter(
            tax_return=federal, is_active=True
        ).count()
        data["total_shareholders"] = str(sh_count) if sh_count else ""
    else:
        data["total_shareholders"] = ""

    return data


# ---------------------------------------------------------------------------
# GA600S Renderer
# ---------------------------------------------------------------------------

class GA600SRenderer:
    """Stateful renderer that draws the GA-600S form page by page."""

    def __init__(self):
        self.buf = io.BytesIO()
        self.c = canvas.Canvas(self.buf, pagesize=letter)
        self.y = PAGE_HEIGHT - MARGIN_TOP
        self.page_num = 0

    def _new_page(self, entity_name: str = "", ein: str = ""):
        """Start a new page with optional continuation header."""
        if self.page_num > 0:
            self.c.showPage()
        self.page_num += 1
        self.y = PAGE_HEIGHT - MARGIN_TOP
        self.c.setFillColor(colors.black)

        if self.page_num > 1 and (entity_name or ein):
            self._draw_continuation_header(entity_name, ein)

    def _draw_continuation_header(self, entity_name: str, ein: str):
        """Draw name + FEIN header on continuation pages."""
        self.c.setFont(LABEL_FONT, 8)
        self.c.setFillColor(colors.Color(0.4, 0.4, 0.4))
        self.c.drawString(CONTENT_LEFT, self.y, f"Georgia Form 600S — Page {self.page_num}")
        self.c.drawRightString(CONTENT_RIGHT, self.y, f"FEIN: {ein}")
        self.y -= 12
        self.c.setFont(VALUE_FONT, 9)
        self.c.setFillColor(colors.black)
        self.c.drawString(CONTENT_LEFT, self.y, entity_name)
        self.y -= 14
        # Thin separator
        self.c.setStrokeColor(DIVIDER_COLOR)
        self.c.setLineWidth(0.75)
        self.c.line(CONTENT_LEFT, self.y, CONTENT_RIGHT, self.y)
        self.y -= 8

    def _check_space(self, needed: float, entity_name: str = "", ein: str = ""):
        """Start new page if not enough vertical space."""
        if self.y - needed < MARGIN_BOTTOM:
            self._new_page(entity_name, ein)

    # -- Drawing primitives --

    def draw_form_title(self, year: int):
        """Draw the main form title bar."""
        bar_h = 48
        self.c.setFillColor(HEADER_BG)
        self.c.rect(CONTENT_LEFT, self.y - bar_h, CONTENT_WIDTH, bar_h, fill=1, stroke=0)

        # Title text (white)
        self.c.setFillColor(colors.white)
        self.c.setFont(TITLE_FONT, 14)
        self.c.drawString(CONTENT_LEFT + 8, self.y - 16, "Georgia Form 600S")
        self.c.setFont(LABEL_FONT, 9)
        self.c.drawString(CONTENT_LEFT + 8, self.y - 30,
                          "S Corporation Tax Return — Georgia Department of Revenue")
        self.c.setFont(SMALL_FONT, 8)
        self.c.drawString(CONTENT_LEFT + 8, self.y - 42, f"Tax Year {year}")

        # Right side
        self.c.setFont(SMALL_FONT, 7)
        self.c.drawRightString(CONTENT_RIGHT - 8, self.y - 16, "(Rev. 08/13/24)")
        self.c.drawRightString(CONTENT_RIGHT - 8, self.y - 30, f"Page {self.page_num}")

        self.c.setFillColor(colors.black)
        self.y -= bar_h + 6

    def draw_tax_period_block(self, year: int):
        """Draw the income tax / net worth tax period block."""
        block_h = 36
        self.c.setStrokeColor(LINE_COLOR)
        self.c.setLineWidth(0.5)
        self.c.rect(CONTENT_LEFT, self.y - block_h, CONTENT_WIDTH, block_h, fill=0, stroke=1)

        mid_x = CONTENT_LEFT + CONTENT_WIDTH / 2
        self.c.line(mid_x, self.y, mid_x, self.y - block_h)

        # Left: Income Tax Return period
        self.c.setFont(LABEL_FONT, HEADER_LABEL_SIZE)
        self.c.drawString(CONTENT_LEFT + 4, self.y - 10,
                          f"{year} Income Tax Return")
        self.c.setFont(VALUE_FONT, HEADER_VALUE_SIZE)
        self.c.drawString(CONTENT_LEFT + 4, self.y - 22,
                          f"Beginning: 01/01/{year}    Ending: 12/31/{year}")

        # Right: Net Worth Tax Return period
        self.c.setFont(LABEL_FONT, HEADER_LABEL_SIZE)
        self.c.drawString(mid_x + 4, self.y - 10,
                          f"{year + 1} Net Worth Tax Return")
        self.c.setFont(VALUE_FONT, HEADER_VALUE_SIZE)
        self.c.drawString(mid_x + 4, self.y - 22,
                          f"Beginning: 01/01/{year + 1}    Ending: 12/31/{year + 1}")

        self.y -= block_h + 4

    def draw_checkbox_row(self, fv: dict):
        """Draw the return type checkboxes row."""
        self.c.setFont(LABEL_FONT, HEADER_LABEL_SIZE)
        x = CONTENT_LEFT + 4
        items = [
            ("Original Return", True),
            ("Amended", False),
            ("Final", False),
        ]
        for label, checked in items:
            marker = "[X]" if checked else "[ ]"
            self.c.drawString(x, self.y, f"{marker} {label}")
            x += 100

        # PTET checkbox
        ptet = fv.get("GA_PTET", "")
        ptet_checked = ptet.lower() in ("true", "1", "yes") if ptet else False
        marker = "[X]" if ptet_checked else "[ ]"
        self.c.drawString(CONTENT_LEFT + 4, self.y - 12,
                          f"{marker} S Corporation elects to pay tax at entity level (PTET)")
        self.y -= 28

    def draw_entity_header(self, data: dict):
        """Draw the entity identification block (fields A-P)."""
        block_start = self.y

        # Row 1: EIN + Name
        self._draw_header_field_pair(
            "A. Federal EIN", data["ein"],
            "B. Corporation Name", data["entity_name"],
            split=0.30,
        )

        # Row 2: GA Withholding + Address
        self._draw_header_field_pair(
            "C. GA Withholding Acct #", "",
            "D. Business Street Address", data["address"],
            split=0.30,
        )

        # Row 3: Sales Tax + City, State, ZIP
        self.c.setFont(LABEL_FONT, HEADER_LABEL_SIZE)
        self.c.drawString(CONTENT_LEFT + 4, self.y - 8, "E. GA Sales Tax Reg #")
        col2_x = CONTENT_LEFT + CONTENT_WIDTH * 0.30
        col3_x = CONTENT_LEFT + CONTENT_WIDTH * 0.60
        col4_x = CONTENT_LEFT + CONTENT_WIDTH * 0.75

        self.c.drawString(col2_x, self.y - 8, "F. City")
        self.c.drawString(col3_x, self.y - 8, "G. State")
        self.c.drawString(col4_x, self.y - 8, "H. ZIP")

        self.c.setFont(VALUE_FONT, HEADER_VALUE_SIZE)
        self.c.drawString(col2_x, self.y - 18, data["city"])
        self.c.drawString(col3_x, self.y - 18, data["state"])
        self.c.drawString(col4_x, self.y - 18, data["zip"])
        self.y -= 24

        # Row 4: NAICS, Inc Date, Inc State, Admitted GA, Business Type
        fields = [
            ("J. NAICS Code", data["naics"], 0.00, 0.14),
            ("K. Date Incorp.", data["inc_date"], 0.14, 0.30),
            ("L. State Incorp.", data["inc_state"], 0.30, 0.44),
            ("M. Date Admitted GA", "", 0.44, 0.62),
            ("N. Type of Business", data["business_type"], 0.62, 1.0),
        ]
        for label, value, start, end in fields:
            x = CONTENT_LEFT + CONTENT_WIDTH * start + 4
            self.c.setFont(LABEL_FONT, HEADER_LABEL_SIZE)
            self.c.drawString(x, self.y - 8, label)
            if value:
                self.c.setFont(VALUE_FONT, HEADER_VALUE_SIZE)
                self.c.drawString(x, self.y - 18, value)
        self.y -= 24

        # Row 5: Records location + Phone + Shareholders
        self.c.setFont(LABEL_FONT, HEADER_LABEL_SIZE)
        self.c.drawString(CONTENT_LEFT + 4, self.y - 8,
                          "O. Records Location")
        self.c.setFont(VALUE_FONT, HEADER_VALUE_SIZE)
        loc = f"{data['city']}, {data['state']}"
        self.c.drawString(CONTENT_LEFT + 4, self.y - 18, loc)

        phone_x = CONTENT_LEFT + CONTENT_WIDTH * 0.40
        self.c.setFont(LABEL_FONT, HEADER_LABEL_SIZE)
        self.c.drawString(phone_x, self.y - 8, "P. Telephone")
        self.c.setFont(VALUE_FONT, HEADER_VALUE_SIZE)
        self.c.drawString(phone_x, self.y - 18, data["phone"])

        sh_x = CONTENT_LEFT + CONTENT_WIDTH * 0.65
        self.c.setFont(LABEL_FONT, HEADER_LABEL_SIZE)
        self.c.drawString(sh_x, self.y - 8, "Q. Total Shareholders")
        self.c.setFont(VALUE_FONT, HEADER_VALUE_SIZE)
        self.c.drawString(sh_x, self.y - 18, data["total_shareholders"])

        self.y -= 24

        # Box around entire entity block
        block_h = block_start - self.y
        self.c.setStrokeColor(LINE_COLOR)
        self.c.setLineWidth(0.5)
        self.c.rect(CONTENT_LEFT, self.y, CONTENT_WIDTH, block_h, fill=0, stroke=1)
        self.y -= 6

    def _draw_header_field_pair(self, label1, value1, label2, value2, split=0.5):
        """Draw two header fields side by side."""
        col1_x = CONTENT_LEFT + 4
        col2_x = CONTENT_LEFT + CONTENT_WIDTH * split

        self.c.setFont(LABEL_FONT, HEADER_LABEL_SIZE)
        self.c.drawString(col1_x, self.y - 8, label1)
        self.c.drawString(col2_x, self.y - 8, label2)

        self.c.setFont(VALUE_FONT, HEADER_VALUE_SIZE)
        if value1:
            self.c.drawString(col1_x, self.y - 18, value1)
        if value2:
            self.c.drawString(col2_x, self.y - 18, value2)

        self.y -= 24

    def draw_section_header(self, title: str):
        """Draw a section header bar with light background."""
        h = 14
        self.c.setFillColor(SECTION_BG)
        self.c.rect(CONTENT_LEFT, self.y - h, CONTENT_WIDTH, h, fill=1, stroke=0)
        self.c.setFillColor(colors.black)
        self.c.setFont(TITLE_FONT, SECTION_HEADER_SIZE)
        self.c.drawString(CONTENT_LEFT + 4, self.y - 10, title)
        self.y -= h + 2

    def draw_line_row(self, line_num: str, label: str, value: str, is_total: bool = False):
        """Draw a single form line: line number | label | amount."""
        amt_col_x = CONTENT_RIGHT - 100
        num_col_w = 28

        # Light grid line
        self.c.setStrokeColor(LINE_COLOR)
        self.c.setLineWidth(0.25)
        self.c.line(CONTENT_LEFT, self.y, CONTENT_RIGHT, self.y)

        # Line number
        self.c.setFont(VALUE_FONT if is_total else LABEL_FONT, LABEL_SIZE)
        self.c.drawString(CONTENT_LEFT + 2, self.y - 10, line_num)

        # Label
        font = VALUE_FONT if is_total else LABEL_FONT
        self.c.setFont(font, LABEL_SIZE)
        self.c.drawString(CONTENT_LEFT + num_col_w, self.y - 10, label)

        # Amount (right-aligned, bold)
        formatted = _fmt_currency(value)
        if formatted:
            self.c.setFont(VALUE_FONT, VALUE_SIZE)
            self.c.drawRightString(CONTENT_RIGHT - 4, self.y - 10, formatted)

        # Vertical separator before amount column
        self.c.setStrokeColor(LINE_COLOR)
        self.c.setLineWidth(0.25)
        self.c.line(amt_col_x, self.y, amt_col_x, self.y - ROW_HEIGHT)

        self.y -= ROW_HEIGHT

    def draw_3col_row(self, line_num: str, label: str, val_a: str, val_b: str, val_c: str,
                      is_total: bool = False):
        """Draw a 3-column row for Schedule 4 (Income Tax | Net Worth Tax | Total)."""
        col_a_x = CONTENT_RIGHT - 270
        col_b_x = CONTENT_RIGHT - 180
        col_c_x = CONTENT_RIGHT - 90
        num_col_w = 28

        # Grid line
        self.c.setStrokeColor(LINE_COLOR)
        self.c.setLineWidth(0.25)
        self.c.line(CONTENT_LEFT, self.y, CONTENT_RIGHT, self.y)

        # Line number
        font = VALUE_FONT if is_total else LABEL_FONT
        self.c.setFont(font, LABEL_SIZE)
        self.c.drawString(CONTENT_LEFT + 2, self.y - 10, line_num)

        # Label (truncated to fit)
        self.c.setFont(font, LABEL_SIZE - 0.5)
        max_label_w = col_a_x - CONTENT_LEFT - num_col_w - 4
        label_text = label
        while self.c.stringWidth(label_text, font, LABEL_SIZE - 0.5) > max_label_w and len(label_text) > 3:
            label_text = label_text[:-1]
        self.c.drawString(CONTENT_LEFT + num_col_w, self.y - 10, label_text)

        # Column values (right-aligned)
        self.c.setFont(VALUE_FONT, VALUE_SIZE - 0.5)
        for val, col_x in [(val_a, col_a_x), (val_b, col_b_x), (val_c, col_c_x)]:
            fmt = _fmt_currency(val)
            if fmt:
                self.c.drawRightString(col_x + 86, self.y - 10, fmt)

        # Vertical separators
        self.c.setStrokeColor(LINE_COLOR)
        self.c.setLineWidth(0.25)
        for col_x in [col_a_x, col_b_x, col_c_x]:
            self.c.line(col_x, self.y, col_x, self.y - ROW_HEIGHT)

        self.y -= ROW_HEIGHT

    def draw_3col_header(self):
        """Draw column headers for Schedule 4."""
        col_a_x = CONTENT_RIGHT - 270
        col_b_x = CONTENT_RIGHT - 180
        col_c_x = CONTENT_RIGHT - 90

        self.c.setFont(TITLE_FONT, 7)
        self.c.drawCentredString(col_a_x + 45, self.y - 10, "A. Income Tax")
        self.c.drawCentredString(col_b_x + 45, self.y - 10, "B. Net Worth Tax")
        self.c.drawCentredString(col_c_x + 45, self.y - 10, "C. Total")

        # Separators
        self.c.setStrokeColor(LINE_COLOR)
        self.c.setLineWidth(0.25)
        for col_x in [col_a_x, col_b_x, col_c_x]:
            self.c.line(col_x, self.y, col_x, self.y - ROW_HEIGHT)
        self.c.line(CONTENT_LEFT, self.y - ROW_HEIGHT, CONTENT_RIGHT, self.y - ROW_HEIGHT)

        self.y -= ROW_HEIGHT

    def draw_signature_block(self, entity_name: str):
        """Draw the signature/declaration block at the bottom."""
        self.y -= 8
        self.c.setStrokeColor(DIVIDER_COLOR)
        self.c.setLineWidth(0.75)
        self.c.line(CONTENT_LEFT, self.y, CONTENT_RIGHT, self.y)
        self.y -= 14

        self.c.setFont(TITLE_FONT, 9)
        self.c.drawString(CONTENT_LEFT + 4, self.y, "Declaration")
        self.y -= 12

        self.c.setFont(LABEL_FONT, 7)
        decl = (
            "Under penalties of perjury, I declare that I have examined this return, "
            "including accompanying schedules and statements, and to the best of my "
            "knowledge and belief, it is true, correct, and complete."
        )
        # Simple word wrap
        words = decl.split()
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if self.c.stringWidth(test, LABEL_FONT, 7) > CONTENT_WIDTH - 8:
                self.c.drawString(CONTENT_LEFT + 4, self.y, line)
                self.y -= 10
                line = word
            else:
                line = test
        if line:
            self.c.drawString(CONTENT_LEFT + 4, self.y, line)
            self.y -= 14

        # Signature lines
        sig_fields = [
            ("Signature of Officer", 0.55),
            ("Date", 0.25),
            ("Title", 0.20),
        ]
        x = CONTENT_LEFT
        for label, frac in sig_fields:
            w = CONTENT_WIDTH * frac - 10
            self.c.setStrokeColor(colors.black)
            self.c.setLineWidth(0.5)
            self.c.line(x, self.y, x + w, self.y)
            self.c.setFont(LABEL_FONT, 6)
            self.c.drawString(x, self.y - 8, label)
            x += w + 10
        self.y -= 20

        # Preparer block
        x = CONTENT_LEFT
        prep_fields = [
            ("Preparer's Signature", 0.40),
            ("Date", 0.15),
            ("PTIN", 0.20),
            ("Firm's EIN", 0.25),
        ]
        for label, frac in prep_fields:
            w = CONTENT_WIDTH * frac - 10
            self.c.setStrokeColor(colors.black)
            self.c.setLineWidth(0.5)
            self.c.line(x, self.y, x + w, self.y)
            self.c.setFont(LABEL_FONT, 6)
            self.c.drawString(x, self.y - 8, label)
            x += w + 10

    def finish(self) -> bytes:
        """Finalize and return PDF bytes."""
        self.c.showPage()
        self.c.save()
        self.buf.seek(0)
        return self.buf.getvalue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_ga600s_native(tax_return) -> bytes:
    """
    Render a complete Georgia Form 600S from scratch using ReportLab.

    Args:
        tax_return: The STATE TaxReturn instance (form_code="GA-600S").

    Returns:
        PDF bytes for the complete GA-600S form.
    """
    fv = _get_field_values(tax_return)
    data = _get_entity_data(tax_return)
    year = int(data["year"])
    entity_name = data["entity_name"]
    ein = data["ein"]

    r = GA600SRenderer()

    # ===== PAGE 1: Title + Entity Header + Schedule 1 + Schedule 2 =====
    r._new_page()
    r.draw_form_title(year)
    r.draw_tax_period_block(year)
    r.draw_checkbox_row(fv)
    r.draw_entity_header(data)

    # Schedule 1 — Computation of GA Taxable Income and Tax
    r.draw_section_header("Schedule 1 — Computation of GA Taxable Income and Tax")
    sched1_lines = [
        ("1", "Georgia Net Income (from Schedule 5, Line 7)", "S1_1", False),
        ("2", "Additional Georgia Taxable Income", "S1_2", False),
        ("3", "Total Income (Add Lines 1 and 2)", "S1_3", True),
        ("4", "Georgia Net Operating Loss Deduction", "S1_4", False),
        ("5", "Passive Loss/Capital Loss Deduction", "S1_5", False),
        ("6", "Total Georgia Taxable Income (Line 3 less Lines 4 and 5)", "S1_6", True),
        ("7", "Income Tax (5.39% x Line 6) — PTET only", "S1_7", True),
    ]
    for num, label, key, total in sched1_lines:
        r.draw_line_row(num, label, fv.get(key, ""), is_total=total)

    r.y -= SECTION_GAP

    # Schedule 2 — PTET Computation (if applicable)
    ptet = fv.get("GA_PTET", "")
    ptet_elected = ptet.lower() in ("true", "1", "yes") if ptet else False
    r.draw_section_header("Schedule 2 — Computation of Georgia Taxable Net Income (PTET)")
    if not ptet_elected:
        r.c.setFont(LABEL_FONT, LABEL_SIZE)
        r.c.drawString(CONTENT_LEFT + 30, r.y - 10,
                        "N/A — PTET not elected. Most S Corporations do not owe Georgia income tax.")
        r.y -= ROW_HEIGHT
    else:
        sched2_lines = [
            ("1", "Georgia Net Income (from Schedule 5, Line 7)", "S2_1", False),
            ("2", "Georgia Net Operating Loss Deduction", "S2_2", False),
            ("3", "Georgia Taxable Net Income (Line 1 less Line 2)", "S2_3", True),
            ("4", "Tax at entity level (5.39% x Line 3)", "S2_4", True),
        ]
        for num, label, key, total in sched2_lines:
            r.draw_line_row(num, label, fv.get(key, ""), is_total=total)

    # ===== PAGE 2: Schedule 3 + 4 + 5 =====
    r._new_page(entity_name, ein)

    # Schedule 3 — Net Worth Tax
    r.draw_section_header("Schedule 3 — Computation of Net Worth Tax")
    sched3_lines = [
        ("1", "Total Capital Stock Issued", "S3_1", False),
        ("2", "Paid-in or Capital Surplus", "S3_2", False),
        ("3", "Total Retained Earnings", "S3_3", False),
        ("4", "Net Worth (Total of Lines 1, 2, and 3)", "S3_4", True),
        ("5", "Ratio (GA and Domestic: 1.000000; Foreign from Sch 9)", "S3_5", False),
        ("6", "Net Worth Taxable by Georgia (Line 4 x Line 5)", "S3_6", True),
        ("7", "Net Worth Tax (from table in instructions)", "S3_7", True),
    ]
    for num, label, key, total in sched3_lines:
        val = fv.get(key, "")
        if key == "S3_5":
            val = _fmt_pct(val) if val else ""
            r.draw_line_row(num, label, val, is_total=total)
        else:
            r.draw_line_row(num, label, val, is_total=total)

    r.y -= SECTION_GAP

    # Schedule 4 — Tax Due or Overpayment (3-column layout)
    r.draw_section_header("Schedule 4 — Computation of Tax Due or Overpayment")
    r.draw_3col_header()

    sched4_rows = [
        ("1", "Total Tax", "S4_1"),
        ("2", "Estimated tax payments", "S4_2"),
        ("3", "Credits from Schedule 11", "S4_3"),
        ("4", "Withholding Credits", "S4_4"),
        ("5", "Balance of tax due", "S4_5"),
        ("6", "Amount of overpayment", "S4_6"),
        ("7", "Interest due", "S4_7"),
        ("8", "Form 600 UET penalty", "S4_8"),
        ("9", "Other penalty due", "S4_9"),
        ("10", "Amount Due", "S4_10"),
        ("11", "Credit to next year estimated tax", "S4_11"),
    ]
    total_lines = {"5", "6", "10", "11"}
    for num, label, prefix in sched4_rows:
        r.draw_3col_row(
            num, label,
            fv.get(f"{prefix}a", ""),
            fv.get(f"{prefix}b", ""),
            fv.get(f"{prefix}c", ""),
            is_total=(num in total_lines),
        )

    r.y -= SECTION_GAP

    # Schedule 5 — GA Net Income
    r.draw_section_header("Schedule 5 — Computation of Georgia Net Income")
    sched5_lines = [
        ("1", "Total Income for GA purposes (Schedule 6, Line 11)", "S5_1", False),
        ("2", "Income allocated everywhere (Attach Schedule)", "S5_2", False),
        ("3", "Business Income subject to apportionment (Line 1 less Line 2)", "S5_3", True),
        ("4", "Georgia Ratio (default 1.000000)", "S5_4", False),
        ("5", "Net business income apportioned to Georgia (Line 3 x Line 4)", "S5_5", True),
        ("6", "Net income allocated to Georgia (Attach Schedule)", "S5_6", False),
        ("7", "Georgia Net Income (Add Line 5 and Line 6)", "S5_7", True),
    ]
    for num, label, key, total in sched5_lines:
        val = fv.get(key, "")
        if key == "S5_4":
            val = _fmt_pct(val) if val else ""
            r.draw_line_row(num, label, val, is_total=total)
        else:
            r.draw_line_row(num, label, val, is_total=total)

    # ===== PAGE 3: Schedule 6 + 7 + 8 + Signature =====
    r._new_page(entity_name, ein)

    # Schedule 6 — Total Income for GA Purposes
    r.draw_section_header("Schedule 6 — Computation of Total Income for GA Purposes")
    sched6_lines = [
        ("1", "Ordinary income (loss) per Federal return", "S6_1", False),
        ("2", "Net income (loss) from rental real estate activities", "S6_2", False),
        ("3a", "Gross income from other rental activities", "S6_3a", False),
        ("3b", "Less: expenses from other rental activities", "S6_3b", False),
        ("3c", "Net business income from other rental activities", "S6_3c", True),
        ("4a", "Portfolio: Interest Income", "S6_4a", False),
        ("4b", "Portfolio: Dividend Income", "S6_4b", False),
        ("4c", "Portfolio: Royalty Income", "S6_4c", False),
        ("4d", "Portfolio: Net short-term capital gain (loss)", "S6_4d", False),
        ("4e", "Portfolio: Net long-term capital gain (loss)", "S6_4e", False),
        ("4f", "Portfolio: Other portfolio income (loss)", "S6_4f", False),
        ("5", "Net gain (loss) under section 1231", "S6_5", False),
        ("6", "Other Income (loss)", "S6_6", False),
        ("7", "Total Federal Income (Add Lines 1 through 6)", "S6_7", True),
        ("8", "Additions to Federal Income (Schedule 7)", "S6_8", False),
        ("9", "Total (Add Line 7 and Line 8)", "S6_9", True),
        ("10", "Subtractions from Federal Income (Schedule 8)", "S6_10", False),
        ("11", "Total Income for Georgia purposes (Line 9 less Line 10)", "S6_11", True),
    ]
    for num, label, key, total in sched6_lines:
        r.draw_line_row(num, label, fv.get(key, ""), is_total=total)

    r.y -= SECTION_GAP

    # Schedule 7 — Additions to Federal Taxable Income
    r._check_space(140, entity_name, ein)
    r.draw_section_header("Schedule 7 — Additions to Federal Taxable Income")
    sched7_lines = [
        ("1", "State and municipal bond interest (other than Georgia)", "S7_1", False),
        ("2", "Net income or net profits taxes imposed by other jurisdictions", "S7_2", False),
        ("3", "Expense attributable to tax exempt income", "S7_3", False),
        ("4", "Reserved", "", False),
        ("5", "Intangible expenses and related interest costs", "S7_5", False),
        ("6", "Captive REIT expenses and costs", "S7_6", False),
        ("7", "Other Additions (Attach Schedule)", "S7_7", False),
        ("8", "TOTAL (Enter on Schedule 6, Line 8)", "S7_8", True),
    ]
    for num, label, key, total in sched7_lines:
        r.draw_line_row(num, label, fv.get(key, "") if key else "", is_total=total)

    r.y -= SECTION_GAP

    # Schedule 8 — Subtractions from Federal Taxable Income
    r._check_space(100, entity_name, ein)
    r.draw_section_header("Schedule 8 — Subtractions from Federal Taxable Income")
    sched8_lines = [
        ("1", "Interest on obligations of United States", "S8_1", False),
        ("2", "Exception to intangible expenses (Attach IT-Addback)", "S8_2", False),
        ("3", "Exception to captive REIT expenses (Attach IT-REIT)", "S8_3", False),
        ("4", "Other Subtractions (Attach Schedule)", "S8_4", False),
        ("5", "TOTAL (Enter on Schedule 6, Line 10)", "S8_5", True),
    ]
    for num, label, key, total in sched8_lines:
        r.draw_line_row(num, label, fv.get(key, ""), is_total=total)

    # Signature block
    r.y -= SECTION_GAP * 2
    r._check_space(80, entity_name, ein)
    r.draw_signature_block(entity_name)

    return r.finish()
