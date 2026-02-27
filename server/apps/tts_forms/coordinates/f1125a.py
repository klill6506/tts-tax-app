"""
Field coordinate mappings for Form 1125-A -- Cost of Goods Sold (2025).

Coordinates are in PDF points (1 point = 1/72 inch).
Origin (0, 0) is the bottom-left corner of the page.
Page size: ~612 x 792 points.

Single-page form. Attached to Form 1120, 1120-S, or 1065.
Lines 1-8 are the COGS computation.
Lines 9a-9c are inventory method questions (checkboxes).

Coordinates calibrated via pdfplumber extraction from the official 2025 PDF.
"""

from .f1120s import FieldCoord

# ---------------------------------------------------------------------------
# Header fields
# ---------------------------------------------------------------------------
HEADER_FIELDS: dict[str, FieldCoord] = {
    # Entity name (top left, below form title)
    "entity_name": FieldCoord(
        page=0, x=36, y=693, width=420, alignment="left", font_size=10
    ),
    # EIN (top right)
    "ein": FieldCoord(
        page=0, x=465, y=693, width=110, alignment="left", font_size=10
    ),
}

# ---------------------------------------------------------------------------
# Form fields -- amounts are right-aligned in the right column
# The right-side line numbers are at x=491; amount column ~x=500 to x=576
# Lines are spaced 12 points apart, starting at y=680.5 for line 1
# ---------------------------------------------------------------------------
FIELD_MAP: dict[str, FieldCoord] = {
    # Line 1: Inventory at beginning of year
    "1": FieldCoord(page=0, x=500, y=679, width=72, alignment="right", font_size=9),
    # Line 2: Purchases
    "2": FieldCoord(page=0, x=500, y=667, width=72, alignment="right", font_size=9),
    # Line 3: Cost of labor
    "3": FieldCoord(page=0, x=500, y=655, width=72, alignment="right", font_size=9),
    # Line 4: Additional section 263A costs (attach schedule)
    "4": FieldCoord(page=0, x=500, y=643, width=72, alignment="right", font_size=9),
    # Line 5: Other costs (attach schedule)
    "5": FieldCoord(page=0, x=500, y=631, width=72, alignment="right", font_size=9),
    # Line 6: Total (add lines 1 through 5)
    "6": FieldCoord(page=0, x=500, y=619, width=72, alignment="right", font_size=9),
    # Line 7: Inventory at end of year
    "7": FieldCoord(page=0, x=500, y=607, width=72, alignment="right", font_size=9),
    # Line 8: Cost of goods sold (line 6 minus line 7)
    "8": FieldCoord(page=0, x=500, y=583, width=72, alignment="right", font_size=9),

    # Line 9a: Inventory valuation method checkboxes
    # Cost
    "9a_cost": FieldCoord(
        page=0, x=79, y=559, width=10, alignment="left", font_size=9
    ),
    # Lower of cost or market
    "9a_lcm": FieldCoord(
        page=0, x=79, y=547, width=10, alignment="left", font_size=9
    ),
    # Other (attach explanation)
    "9a_other": FieldCoord(
        page=0, x=79, y=535, width=10, alignment="left", font_size=9
    ),

    # Line 9b: Subnormal goods writedown checkbox
    "9b_yes": FieldCoord(
        page=0, x=362, y=475, width=10, alignment="left", font_size=9
    ),
    "9b_no": FieldCoord(
        page=0, x=408, y=475, width=10, alignment="left", font_size=9
    ),

    # Line 9c: LIFO adopted this year checkbox
    "9c_yes": FieldCoord(
        page=0, x=388, y=463, width=10, alignment="left", font_size=9
    ),
    "9c_no": FieldCoord(
        page=0, x=434, y=463, width=10, alignment="left", font_size=9
    ),
}
