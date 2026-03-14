"""
Reusable form drawing primitives for ReportLab canvas.

These functions draw common tax form elements (section headers, label/value
rows, grids, checkboxes, etc.) onto a ReportLab canvas.  All output is
BLACK AND WHITE — no color on printed tax forms.

Usage:
    from apps.tts_forms.form_primitives import (
        draw_section_header,
        draw_label_value_row,
        draw_grid_table,
        draw_entity_info_grid,
        draw_checkbox,
        draw_page_header,
        draw_money_field,
    )
"""

from reportlab.lib import colors
from reportlab.pdfgen import canvas as canvas_mod


# ---------------------------------------------------------------------------
# Section header — black bar with white text
# ---------------------------------------------------------------------------

def draw_section_header(
    c: canvas_mod.Canvas,
    x: float,
    y: float,
    width: float,
    text: str,
    height: float = 18,
) -> None:
    """Black background bar with white text — used for schedule headers."""
    c.saveState()
    c.setFillColor(colors.black)
    c.rect(x, y - height, width, height, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 6, y - height + 5, text)
    c.restoreState()


# ---------------------------------------------------------------------------
# Numbered line row
# ---------------------------------------------------------------------------

def draw_label_value_row(
    c: canvas_mod.Canvas,
    x: float,
    y: float,
    width: float,
    line_num: str,
    description: str,
    amount=None,
    label_font_size: float = 8,
    value_font_size: float = 10,
    row_height: float = 16,
) -> None:
    """One numbered line: [line#] [description] ............. [amount]"""
    c.saveState()
    # Line number
    c.setFont("Helvetica-Bold", label_font_size)
    c.drawString(x, y, str(line_num))
    # Description
    c.setFont("Helvetica", label_font_size)
    c.drawString(x + 20, y, description)
    # Amount (right-aligned, bold)
    if amount is not None:
        c.setFont("Helvetica-Bold", value_font_size)
        formatted = f"({abs(amount):,.0f})" if amount < 0 else f"{amount:,.0f}"
        c.drawRightString(x + width - 10, y, formatted)
    # Bottom line
    c.setStrokeColor(colors.Color(0.7, 0.7, 0.7))
    c.setLineWidth(0.25)
    c.line(x, y - 4, x + width, y - 4)
    c.restoreState()


# ---------------------------------------------------------------------------
# Grid table with header row and data rows
# ---------------------------------------------------------------------------

def draw_grid_table(
    c: canvas_mod.Canvas,
    x: float,
    y: float,
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[float],
    row_height: float = 14,
) -> None:
    """Draws a table with header row and data rows, with grid lines."""
    c.saveState()
    total_width = sum(col_widths)

    # Header row (bold, light gray background)
    c.setFillColor(colors.Color(0.9, 0.9, 0.9))
    c.rect(x, y - row_height, total_width, row_height, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 7)
    cx = x
    for i, header in enumerate(headers):
        c.drawString(cx + 2, y - row_height + 4, header)
        cx += col_widths[i]

    # Data rows
    c.setFont("Helvetica", 8)
    for row_idx, row in enumerate(rows):
        ry = y - (row_idx + 2) * row_height
        cx = x
        for col_idx, cell in enumerate(row):
            c.drawString(cx + 2, ry + 4, str(cell))
            cx += col_widths[col_idx]
        # Row border
        c.rect(x, ry, total_width, row_height, fill=0, stroke=1)

    c.restoreState()


# ---------------------------------------------------------------------------
# Entity identification grid
# ---------------------------------------------------------------------------

def draw_entity_info_grid(
    c: canvas_mod.Canvas,
    x: float,
    y: float,
    width: float,
    fields: list[list[tuple[str, str, float]]],
) -> float:
    """Draw the entity identification grid (EIN, name, address, etc.).

    Args:
        fields: list of rows, each row = list of (label, value, col_width) tuples.

    Returns:
        The y position after the grid.
    """
    c.saveState()
    row_height = 28
    current_y = y

    for row in fields:
        cx = x
        for label, value, col_width in row:
            # Cell border
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.5)
            c.rect(cx, current_y - row_height, col_width, row_height)
            # Label (small, top of cell)
            c.setFont("Helvetica", 6)
            c.setFillColor(colors.black)
            c.drawString(cx + 3, current_y - 8, label)
            # Value (larger, bold, bottom of cell)
            if value:
                c.setFont("Helvetica-Bold", 9)
                c.drawString(cx + 3, current_y - row_height + 6, str(value))
            cx += col_width
        current_y -= row_height

    c.restoreState()
    return current_y


# ---------------------------------------------------------------------------
# Checkbox
# ---------------------------------------------------------------------------

def draw_checkbox(
    c: canvas_mod.Canvas,
    x: float,
    y: float,
    label: str,
    checked: bool = False,
    size: float = 8,
) -> None:
    """Draws a checkbox with label."""
    c.saveState()
    c.rect(x, y, size, size)
    if checked:
        c.setFont("Helvetica-Bold", size)
        c.drawString(x + 1, y + 1, "X")
    c.setFont("Helvetica", 8)
    c.drawString(x + size + 4, y + 1, label)
    c.restoreState()


# ---------------------------------------------------------------------------
# Page header / title bar
# ---------------------------------------------------------------------------

def draw_page_header(
    c: canvas_mod.Canvas,
    x: float,
    y: float,
    width: float,
    form_name: str,
    rev_date: str,
    page_num: int,
    subtitle: str | None = None,
    subtitle2: str | None = None,
) -> float:
    """Form title bar at top of page. Returns y position below the bar."""
    c.saveState()
    bar_height = 36 if subtitle2 else (28 if subtitle else 20)
    # Black bar
    c.setFillColor(colors.black)
    c.rect(x, y - bar_height, width, bar_height, fill=1, stroke=0)
    # White text
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x + 8, y - 16, form_name)
    c.setFont("Helvetica", 8)
    c.drawRightString(x + width - 8, y - 12, f"({rev_date})")
    c.drawRightString(x + width - 8, y - bar_height + 6, f"Page {page_num}")
    if subtitle:
        c.setFont("Helvetica", 9)
        c.drawString(x + 8, y - 28, subtitle)
    if subtitle2:
        c.drawString(x + 8, y - 38, subtitle2)
    c.restoreState()
    return y - bar_height


# ---------------------------------------------------------------------------
# Money field
# ---------------------------------------------------------------------------

def draw_money_field(
    c: canvas_mod.Canvas,
    x: float,
    y: float,
    width: float,
    amount,
    font_size: float = 10,
) -> None:
    """Right-aligned currency value, negative in parentheses, whole dollars."""
    c.saveState()
    c.setFont("Helvetica-Bold", font_size)
    if amount is None or amount == 0:
        text = ""
    elif amount < 0:
        text = f"({abs(amount):,.0f})"
    else:
        text = f"{amount:,.0f}"
    c.drawRightString(x + width - 4, y, text)
    c.restoreState()
