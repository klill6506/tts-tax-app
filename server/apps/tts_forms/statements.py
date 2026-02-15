"""
IRS Supporting Statement page generator.

When a form line (e.g., Line 19 "Other deductions") needs detail beyond
a single total, the total goes on the IRS form and the breakdown prints
as a separate "Statement" page appended after the main form.

This is standard IRS filing practice — supporting statements are NOT
formatted to look like IRS pre-printed pages. They use a clean, consistent
header + table layout.

Usage:
    from apps.tts_forms.statements import render_statement_pages

    pages = [
        {
            "title": "Form 1120-S (2025) — Statement for Line 19",
            "subtitle": "Other deductions",
            "form_code": "1120-S",
            "items": [
                {"description": "Office supplies", "amount": "1,234"},
                {"description": "Professional fees", "amount": "5,678"},
            ],
        }
    ]
    pdf_bytes = render_statement_pages(pages)
"""

import io
from decimal import Decimal, InvalidOperation

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# Layout constants
PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT_MARGIN = 1.0 * inch
RIGHT_MARGIN = 1.0 * inch
TOP_MARGIN = 1.0 * inch
BOTTOM_MARGIN = 1.0 * inch
USABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

HEADER_FONT = "Helvetica-Bold"
BODY_FONT = "Courier"
HEADER_SIZE = 12
SUBHEADER_SIZE = 10
BODY_SIZE = 10
LINE_HEIGHT = 14

# Column layout
DESC_COL_X = LEFT_MARGIN
AMOUNT_COL_X = PAGE_WIDTH - RIGHT_MARGIN


def _format_amount(value: str) -> str:
    """Format an amount string for display."""
    if not value:
        return ""
    # Strip existing formatting
    clean = value.replace(",", "").replace("$", "").strip()
    try:
        d = Decimal(clean)
    except InvalidOperation:
        return value
    if d < 0:
        return f"({abs(d):,.2f})"
    return f"{d:,.2f}"


def render_statement_pages(pages: list[dict]) -> bytes | None:
    """
    Render one or more supporting statement pages.

    Args:
        pages: List of statement page dicts, each with:
            - title: Header text (e.g., "Form 1120-S (2025) — Statement for Line 19")
            - subtitle: Optional subheader (e.g., "Other deductions")
            - form_code: Form code for reference
            - items: List of dicts with "description" and "amount" keys.
                     Optional "category" key for grouping.

    Returns:
        PDF bytes, or None if no pages provided.
    """
    if not pages:
        return None

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    for page_def in pages:
        _draw_statement_page(c, page_def)

    c.save()
    buf.seek(0)
    return buf.getvalue()


def _draw_statement_page(c: canvas.Canvas, page_def: dict) -> None:
    """Draw a single statement page."""
    title = page_def.get("title", "Supporting Statement")
    subtitle = page_def.get("subtitle", "")
    items = page_def.get("items", [])

    y = PAGE_HEIGHT - TOP_MARGIN

    # --- Header ---
    c.setFont(HEADER_FONT, HEADER_SIZE)
    c.drawString(LEFT_MARGIN, y, title)
    y -= LINE_HEIGHT * 1.5

    if subtitle:
        c.setFont(HEADER_FONT, SUBHEADER_SIZE)
        c.drawString(LEFT_MARGIN, y, subtitle)
        y -= LINE_HEIGHT * 1.5

    # --- Separator line ---
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)
    y -= LINE_HEIGHT

    # --- Column headers ---
    c.setFont(HEADER_FONT, BODY_SIZE)
    c.drawString(DESC_COL_X, y, "Description")
    c.drawRightString(AMOUNT_COL_X, y, "Amount")
    y -= 4
    c.setLineWidth(0.25)
    c.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)
    y -= LINE_HEIGHT

    # --- Items ---
    c.setFont(BODY_FONT, BODY_SIZE)
    total = Decimal("0.00")

    for item in items:
        if y < BOTTOM_MARGIN + LINE_HEIGHT * 3:
            # Page break — continuation header
            c.showPage()
            y = PAGE_HEIGHT - TOP_MARGIN
            c.setFont(HEADER_FONT, SUBHEADER_SIZE)
            c.drawString(LEFT_MARGIN, y, f"{title} (continued)")
            y -= LINE_HEIGHT * 1.5
            c.setFont(HEADER_FONT, BODY_SIZE)
            c.drawString(DESC_COL_X, y, "Description")
            c.drawRightString(AMOUNT_COL_X, y, "Amount")
            y -= 4
            c.setLineWidth(0.25)
            c.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)
            y -= LINE_HEIGHT
            c.setFont(BODY_FONT, BODY_SIZE)

        desc = item.get("description", "")
        amount_str = item.get("amount", "")

        # Truncate long descriptions
        max_desc_width = USABLE_WIDTH - 120
        while c.stringWidth(desc, BODY_FONT, BODY_SIZE) > max_desc_width and len(desc) > 3:
            desc = desc[:-4] + "..."

        c.drawString(DESC_COL_X, y, desc)
        formatted = _format_amount(amount_str)
        c.drawRightString(AMOUNT_COL_X, y, formatted)

        # Accumulate total
        clean = amount_str.replace(",", "").replace("$", "").strip()
        try:
            total += Decimal(clean)
        except InvalidOperation:
            pass

        y -= LINE_HEIGHT

    # --- Total line ---
    y -= 4
    c.setLineWidth(0.5)
    c.line(AMOUNT_COL_X - 100, y, AMOUNT_COL_X, y)
    y -= LINE_HEIGHT

    c.setFont(HEADER_FONT, BODY_SIZE)
    c.drawString(DESC_COL_X, y, "Total")
    if total < 0:
        c.drawRightString(AMOUNT_COL_X, y, f"({abs(total):,.2f})")
    else:
        c.drawRightString(AMOUNT_COL_X, y, f"{total:,.2f}")

    c.showPage()
