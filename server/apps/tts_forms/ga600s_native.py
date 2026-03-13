"""
Georgia Form 600S — Native PDF Generator.

Generates a complete GA-600S from scratch using ReportLab Tables and
drawing primitives. BLACK AND WHITE only — no color on printed forms.

Professional tax software (Lacerte, Drake) generates its own renditions
of state forms. This follows that same approach.

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
from reportlab.platypus import Table, TableStyle

PAGE_WIDTH, PAGE_HEIGHT = letter  # 612 x 792

# Margins — 0.75 inch on left/right, 0.5 inch top/bottom
MARGIN_L = 0.75 * inch
MARGIN_R = 0.75 * inch
MARGIN_T = 0.5 * inch
MARGIN_B = 0.5 * inch

CL = MARGIN_L                    # content left
CR = PAGE_WIDTH - MARGIN_R       # content right
CW = CR - CL                     # content width

# Fonts
F_BOLD = "Helvetica-Bold"
F_REG = "Helvetica"

# Row heights
ROW_H = 14       # standard schedule row
HDR_ROW_H = 18   # entity info rows (taller for label+value)

ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _d(val: str) -> Decimal:
    if not val:
        return ZERO
    clean = val.replace(",", "").replace("$", "").replace("(", "-").replace(")", "").strip()
    try:
        return Decimal(clean)
    except InvalidOperation:
        return ZERO


def _fc(val: str) -> str:
    """Format as whole-dollar currency: 1,234 or (1,234). Empty if zero."""
    d = _d(val)
    if d == 0:
        return ""
    if d < 0:
        return f"({abs(d):,.0f})"
    return f"{d:,.0f}"


def _fp(val: str) -> str:
    """Format percentage field."""
    d = _d(val)
    if d == 0:
        return ""
    if d == 1:
        return "1.000000"
    return str(d)


def _get_field_values(tax_return) -> dict[str, str]:
    from apps.returns.models import FormFieldValue
    result = {}
    for fv in FormFieldValue.objects.filter(
        tax_return=tax_return
    ).select_related("form_line"):
        result[fv.form_line.line_number] = fv.value or ""
    return result


def _get_entity_data(tax_return) -> dict[str, str]:
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
# Drawing helpers
# ---------------------------------------------------------------------------

def _draw_title_bar(c: canvas.Canvas, y: float, year: int, page: int) -> float:
    """Draw the black title bar at top. Returns new y."""
    bar_h = 44
    top = y
    c.setFillColor(colors.black)
    c.rect(CL, top - bar_h, CW, bar_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(F_BOLD, 14)
    c.drawString(CL + 8, top - 16, "Georgia Form 600S")
    c.setFont(F_REG, 9)
    c.drawString(CL + 8, top - 28,
                 "S Corporation Tax Return — Georgia Department of Revenue")
    c.setFont(F_REG, 8)
    c.drawString(CL + 8, top - 40, f"Tax Year {year}")
    c.setFont(F_REG, 7)
    c.drawRightString(CR - 8, top - 14, "(Rev. 08/13/24)")
    c.setFont(F_BOLD, 8)
    c.drawRightString(CR - 8, top - 28, f"Page {page}")
    c.setFillColor(colors.black)
    return top - bar_h - 4


def _draw_continuation_header(c: canvas.Canvas, y: float, name: str, ein: str, page: int) -> float:
    """Draw page header on continuation pages."""
    c.setFont(F_REG, 8)
    c.drawString(CL, y, f"Georgia Form 600S — Page {page}")
    c.drawRightString(CR, y, f"FEIN: {ein}")
    y -= 12
    c.setFont(F_BOLD, 9)
    c.drawString(CL, y, name)
    y -= 3
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.75)
    c.line(CL, y, CR, y)
    return y - 8


def _draw_section_header(c: canvas.Canvas, y: float, title: str) -> float:
    """Draw a black bar with white text section header. Returns new y."""
    h = 15
    c.setFillColor(colors.black)
    c.rect(CL, y - h, CW, h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(F_BOLD, 9)
    c.drawString(CL + 4, y - 11, title)
    c.setFillColor(colors.black)
    return y - h


def _draw_schedule_rows(c: canvas.Canvas, y: float, rows, fv: dict,
                        amt_col_w: float = 100) -> float:
    """Draw schedule line rows with grid. Returns new y.

    rows: list of (line_num, label, fv_key, is_total, fmt_func)
    fmt_func defaults to _fc (currency).
    """
    amt_x = CR - amt_col_w
    num_w = 24

    for row in rows:
        if len(row) == 4:
            num, label, key, is_total = row
            fmt = _fc
        else:
            num, label, key, is_total, fmt = row

        # Horizontal line above row
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.25)
        c.line(CL, y, CR, y)

        # Vertical separator before amount column
        c.line(amt_x, y, amt_x, y - ROW_H)

        # Line number
        font = F_BOLD if is_total else F_REG
        c.setFont(font, 8)
        c.drawString(CL + 2, y - 10, num)

        # Label
        c.setFont(font, 8)
        c.drawString(CL + num_w, y - 10, label)

        # Amount
        val = fv.get(key, "") if key else ""
        formatted = fmt(val) if val else ""
        if formatted:
            c.setFont(F_BOLD, 9)
            c.drawRightString(CR - 4, y - 10, formatted)

        y -= ROW_H

    # Bottom border
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.25)
    c.line(CL, y, CR, y)

    # Left and right borders for the section
    top_y = y + len(rows) * ROW_H
    c.line(CL, top_y, CL, y)
    c.line(CR, top_y, CR, y)

    return y


def _draw_3col_section(c: canvas.Canvas, y: float, rows, fv: dict) -> float:
    """Draw Schedule 4 style 3-column section. Returns new y."""
    col_a_x = CR - 270
    col_b_x = CR - 180
    col_c_x = CR - 90
    num_w = 24

    # Column header row
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.line(CL, y, CR, y)
    for cx in [col_a_x, col_b_x, col_c_x]:
        c.line(cx, y, cx, y - ROW_H)
    c.setFont(F_BOLD, 7)
    c.drawCentredString(col_a_x + 45, y - 10, "A. Income Tax")
    c.drawCentredString(col_b_x + 45, y - 10, "B. Net Worth Tax")
    c.drawCentredString(col_c_x + 45, y - 10, "C. Total")
    c.line(CL, y - ROW_H, CR, y - ROW_H)
    c.line(CL, y, CL, y - ROW_H)
    c.line(CR, y, CR, y - ROW_H)
    y -= ROW_H

    total_lines = {"5", "6", "10", "11"}
    top_y = y

    for num, label, prefix in rows:
        is_total = num in total_lines
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.25)
        c.line(CL, y, CR, y)
        for cx in [col_a_x, col_b_x, col_c_x]:
            c.line(cx, y, cx, y - ROW_H)

        font = F_BOLD if is_total else F_REG
        c.setFont(font, 7.5)

        # Truncate label to fit
        max_lw = col_a_x - CL - num_w - 6
        lbl = label
        while c.stringWidth(lbl, font, 7.5) > max_lw and len(lbl) > 3:
            lbl = lbl[:-1]

        c.drawString(CL + 2, y - 10, num)
        c.drawString(CL + num_w, y - 10, lbl)

        # Column values
        c.setFont(F_BOLD, 8)
        for val_suffix, cx in [("a", col_a_x), ("b", col_b_x), ("c", col_c_x)]:
            val = fv.get(f"{prefix}{val_suffix}", "")
            fmt = _fc(val)
            if fmt:
                c.drawRightString(cx + 86, y - 10, fmt)

        y -= ROW_H

    # Borders
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.25)
    c.line(CL, y, CR, y)
    c.line(CL, top_y, CL, y)
    c.line(CR, top_y, CR, y)

    return y


def _draw_entity_table(c: canvas.Canvas, y: float, data: dict) -> float:
    """Draw entity info as a bordered grid table. Returns new y."""
    # Build the table data — each row is (label, value, label, value, ...)
    # We'll draw it manually as a grid for precise control.

    row_h = 22  # each entity row height (label + value)
    label_offset = 8   # y offset for label within row
    value_offset = 17  # y offset for value within row

    rows_data = [
        # Row 1: 2 columns
        [("A. Federal EIN", data["ein"], 0.30),
         ("B. Corporation Name", data["entity_name"], 1.0)],
        # Row 2: 2 columns
        [("C. GA Withholding Acct #", "", 0.30),
         ("D. Business Street Address", data["address"], 1.0)],
        # Row 3: 4 columns
        [("E. GA Sales Tax Reg #", "", 0.30),
         ("F. City", data["city"], 0.55),
         ("G. State", data["state"], 0.70),
         ("H. ZIP", data["zip"], 1.0)],
        # Row 4: 5 columns
        [("J. NAICS Code", data["naics"], 0.16),
         ("K. Date Incorp.", data["inc_date"], 0.32),
         ("L. State Incorp.", data["inc_state"], 0.46),
         ("M. Date Admitted GA", "", 0.64),
         ("N. Type of Business", data["business_type"], 1.0)],
        # Row 5: 3 columns
        [("O. Records Location", f"{data['city']}, {data['state']}", 0.40),
         ("P. Telephone", data["phone"], 0.65),
         ("Q. Total Shareholders", data["total_shareholders"], 1.0)],
    ]

    num_rows = len(rows_data)
    table_h = num_rows * row_h
    table_top = y
    table_bot = y - table_h

    # Draw outer border
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.75)
    c.rect(CL, table_bot, CW, table_h, fill=0, stroke=1)

    # Draw each row
    for ri, cols in enumerate(rows_data):
        row_top = table_top - ri * row_h
        row_bot = row_top - row_h

        # Horizontal line between rows (not on first row — outer border handles it)
        if ri > 0:
            c.setLineWidth(0.25)
            c.line(CL, row_top, CR, row_top)

        prev_end = 0.0
        for ci, (label, value, end_frac) in enumerate(cols):
            x_start = CL + CW * prev_end
            x_end = CL + CW * end_frac

            # Vertical separator (not on first column)
            if ci > 0:
                c.setLineWidth(0.25)
                c.line(x_start, row_top, x_start, row_bot)

            # Label (small, regular)
            c.setFont(F_REG, 7)
            c.setFillColor(colors.Color(0.3, 0.3, 0.3))
            c.drawString(x_start + 3, row_top - label_offset, label)

            # Value (larger, bold, black)
            c.setFillColor(colors.black)
            if value:
                c.setFont(F_BOLD, 10)
                # Clip value to cell width
                max_w = (x_end - x_start) - 6
                v = value
                while c.stringWidth(v, F_BOLD, 10) > max_w and len(v) > 1:
                    v = v[:-1]
                c.drawString(x_start + 3, row_top - value_offset, v)

            prev_end = end_frac

    return table_bot - 6


def _draw_checkbox_row(c: canvas.Canvas, y: float, fv: dict) -> float:
    """Draw return type checkboxes. Returns new y."""
    c.setFont(F_REG, 8)
    items = [("Original Return", True), ("Amended", False), ("Final", False)]
    x = CL + 4
    for label, checked in items:
        box = "[X]" if checked else "[  ]"
        c.drawString(x, y, f"{box}  {label}")
        x += 110

    y -= 13
    ptet = fv.get("GA_PTET", "")
    ptet_on = ptet.lower() in ("true", "1", "yes") if ptet else False
    box = "[X]" if ptet_on else "[  ]"
    c.drawString(CL + 4, y, f"{box}  S Corporation elects to pay tax at entity level (PTET)")
    return y - 16


def _draw_date_boxes(c: canvas.Canvas, y: float, year: int) -> float:
    """Draw the income tax / net worth tax period boxes."""
    box_h = 32
    mid = CL + CW / 2

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    # Two boxes side by side
    c.rect(CL, y - box_h, CW / 2, box_h, fill=0, stroke=1)
    c.rect(mid, y - box_h, CW / 2, box_h, fill=0, stroke=1)

    # Left box
    c.setFont(F_BOLD, 8)
    c.drawString(CL + 4, y - 11, f"{year} Income Tax Return")
    c.setFont(F_REG, 8)
    c.drawString(CL + 4, y - 24, f"Beginning: 01/01/{year}    Ending: 12/31/{year}")

    # Right box
    c.setFont(F_BOLD, 8)
    c.drawString(mid + 4, y - 11, f"{year + 1} Net Worth Tax Return")
    c.setFont(F_REG, 8)
    c.drawString(mid + 4, y - 24, f"Beginning: 01/01/{year + 1}    Ending: 12/31/{year + 1}")

    return y - box_h - 4


def _draw_page_number(c: canvas.Canvas, page: int):
    """Draw page number at bottom center."""
    c.setFont(F_REG, 7)
    c.drawCentredString(PAGE_WIDTH / 2, MARGIN_B - 8, f"Page {page}")


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
    name = data["entity_name"]
    ein = data["ein"]

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFillColor(colors.black)

    # ===== PAGE 1 =====
    page = 1
    y = PAGE_HEIGHT - MARGIN_T
    y = _draw_title_bar(c, y, year, page)
    y = _draw_date_boxes(c, y, year)
    y = _draw_checkbox_row(c, y, fv)
    y = _draw_entity_table(c, y, data)

    # Schedule 1
    y = _draw_section_header(c, y, "Schedule 1 — Computation of GA Taxable Income and Tax")
    y = _draw_schedule_rows(c, y, [
        ("1", "Georgia Net Income (from Schedule 5, Line 7)", "S1_1", False),
        ("2", "Additional Georgia Taxable Income", "S1_2", False),
        ("3", "Total Income (Add Lines 1 and 2)", "S1_3", True),
        ("4", "Georgia Net Operating Loss Deduction", "S1_4", False),
        ("5", "Passive Loss/Capital Loss Deduction", "S1_5", False),
        ("6", "Total Georgia Taxable Income (Line 3 less Lines 4 and 5)", "S1_6", True),
        ("7", "Income Tax (5.39% x Line 6) — PTET only", "S1_7", True),
    ], fv)

    y -= 6

    # Schedule 2
    y = _draw_section_header(c, y, "Schedule 2 — Computation of Georgia Taxable Net Income (PTET)")
    ptet = fv.get("GA_PTET", "")
    ptet_on = ptet.lower() in ("true", "1", "yes") if ptet else False
    if not ptet_on:
        c.setFont(F_REG, 8)
        c.drawString(CL + 28, y - 11,
                     "N/A — PTET not elected. Most S Corporations do not owe Georgia income tax.")
        y -= ROW_H + 2
    else:
        y = _draw_schedule_rows(c, y, [
            ("1", "Georgia Net Income (from Schedule 5, Line 7)", "S2_1", False),
            ("2", "Georgia Net Operating Loss Deduction", "S2_2", False),
            ("3", "Georgia Taxable Net Income (Line 1 less Line 2)", "S2_3", True),
            ("4", "Tax at entity level (5.39% x Line 3)", "S2_4", True),
        ], fv)

    _draw_page_number(c, page)

    # ===== PAGE 2 =====
    c.showPage()
    c.setFillColor(colors.black)
    page = 2
    y = PAGE_HEIGHT - MARGIN_T
    y = _draw_continuation_header(c, y, name, ein, page)

    # Schedule 3
    y = _draw_section_header(c, y, "Schedule 3 — Computation of Net Worth Tax")
    y = _draw_schedule_rows(c, y, [
        ("1", "Total Capital Stock Issued", "S3_1", False),
        ("2", "Paid-in or Capital Surplus", "S3_2", False),
        ("3", "Total Retained Earnings", "S3_3", False),
        ("4", "Net Worth (Total of Lines 1, 2, and 3)", "S3_4", True),
        ("5", "Ratio (GA and Domestic: 1.000000; Foreign from Sch 9)", "S3_5", False, _fp),
        ("6", "Net Worth Taxable by Georgia (Line 4 x Line 5)", "S3_6", True),
        ("7", "Net Worth Tax (from table in instructions)", "S3_7", True),
    ], fv)

    y -= 6

    # Schedule 4
    y = _draw_section_header(c, y, "Schedule 4 — Computation of Tax Due or Overpayment")
    y = _draw_3col_section(c, y, [
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
        ("11", "Credit to next year est. tax", "S4_11"),
    ], fv)

    y -= 6

    # Schedule 5
    y = _draw_section_header(c, y, "Schedule 5 — Computation of Georgia Net Income")
    y = _draw_schedule_rows(c, y, [
        ("1", "Total Income for GA purposes (Schedule 6, Line 11)", "S5_1", False),
        ("2", "Income allocated everywhere (Attach Schedule)", "S5_2", False),
        ("3", "Business Income subject to apportionment (Line 1 less Line 2)", "S5_3", True),
        ("4", "Georgia Ratio (default 1.000000)", "S5_4", False, _fp),
        ("5", "Net business income apportioned to Georgia (Line 3 x Line 4)", "S5_5", True),
        ("6", "Net income allocated to Georgia (Attach Schedule)", "S5_6", False),
        ("7", "Georgia Net Income (Add Line 5 and Line 6)", "S5_7", True),
    ], fv)

    _draw_page_number(c, page)

    # ===== PAGE 3 =====
    c.showPage()
    c.setFillColor(colors.black)
    page = 3
    y = PAGE_HEIGHT - MARGIN_T
    y = _draw_continuation_header(c, y, name, ein, page)

    # Schedule 6
    y = _draw_section_header(c, y, "Schedule 6 — Computation of Total Income for GA Purposes")
    y = _draw_schedule_rows(c, y, [
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
    ], fv)

    y -= 6

    # Schedule 7
    y = _draw_section_header(c, y, "Schedule 7 — Additions to Federal Taxable Income")
    y = _draw_schedule_rows(c, y, [
        ("1", "State and municipal bond interest (other than Georgia)", "S7_1", False),
        ("2", "Net income or net profits taxes imposed by other jurisdictions", "S7_2", False),
        ("3", "Expense attributable to tax exempt income", "S7_3", False),
        ("4", "Reserved", "", False),
        ("5", "Intangible expenses and related interest costs", "S7_5", False),
        ("6", "Captive REIT expenses and costs", "S7_6", False),
        ("7", "Other Additions (Attach Schedule)", "S7_7", False),
        ("8", "TOTAL (Enter on Schedule 6, Line 8)", "S7_8", True),
    ], fv)

    y -= 6

    # Schedule 8
    y = _draw_section_header(c, y, "Schedule 8 — Subtractions from Federal Taxable Income")
    y = _draw_schedule_rows(c, y, [
        ("1", "Interest on obligations of United States", "S8_1", False),
        ("2", "Exception to intangible expenses (Attach IT-Addback)", "S8_2", False),
        ("3", "Exception to captive REIT expenses (Attach IT-REIT)", "S8_3", False),
        ("4", "Other Subtractions (Attach Schedule)", "S8_4", False),
        ("5", "TOTAL (Enter on Schedule 6, Line 10)", "S8_5", True),
    ], fv)

    y -= 12

    # Signature block
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.75)
    c.line(CL, y, CR, y)
    y -= 12
    c.setFont(F_BOLD, 9)
    c.drawString(CL + 4, y, "Declaration")
    y -= 12
    c.setFont(F_REG, 7)
    decl = (
        "Under penalties of perjury, I declare that I have examined this return, "
        "including accompanying schedules and statements, and to the best of my "
        "knowledge and belief, it is true, correct, and complete."
    )
    words = decl.split()
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        if c.stringWidth(test, F_REG, 7) > CW - 8:
            c.drawString(CL + 4, y, line)
            y -= 10
            line = word
        else:
            line = test
    if line:
        c.drawString(CL + 4, y, line)
        y -= 14

    # Signature lines
    for fields, frac_list in [
        ([("Signature of Officer", 0.55), ("Date", 0.25), ("Title", 0.20)], None),
        ([("Preparer's Signature", 0.40), ("Date", 0.15), ("PTIN", 0.20), ("Firm's EIN", 0.25)], None),
    ]:
        x = CL
        for label, frac in fields:
            w = CW * frac - 10
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.5)
            c.line(x, y, x + w, y)
            c.setFont(F_REG, 6)
            c.drawString(x, y - 8, label)
            x += w + 10
        y -= 20

    _draw_page_number(c, page)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
