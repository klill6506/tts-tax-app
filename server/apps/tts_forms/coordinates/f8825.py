"""
Field coordinate mappings for Form 8825 -- Rental Real Estate Income and Expenses (2025).

Coordinates are in PDF points (1 point = 1/72 inch).
Origin (0, 0) is the bottom-left corner of the page.
Page size: ~612 x 792 points.

Two-page form. Each page has 4 property columns (A/B/C/D).
Lines 2a-19: per-property income and expenses.
Lines 20-22: summary totals (single amount column on the right).

Coordinates calibrated via pdfplumber extraction from the official 2025 PDF.
"""

from .f1120s import FieldCoord

# ---------------------------------------------------------------------------
# Header fields (appear on page 0 only)
# ---------------------------------------------------------------------------
HEADER_FIELDS: dict[str, FieldCoord] = {
    # Entity name (top left, below form title)
    "entity_name": FieldCoord(
        page=0, x=36, y=693, width=410, alignment="left", font_size=10
    ),
    # EIN (top right)
    "ein": FieldCoord(
        page=0, x=458, y=693, width=118, alignment="left", font_size=10
    ),
}


# ---------------------------------------------------------------------------
# Property description fields (Line 1 area)
#
# Each property has an address field and ancillary fields
# (type code, fair rental days, personal use days).
#
# Properties A-D addresses at y ~ 604/580/556/532 on page 0.
# On page 1 (continuation), the Y positions shift.
# ---------------------------------------------------------------------------

# Address field for each property slot, indexed by (page, slot)
# slot 0=A, 1=B, 2=C, 3=D
# Page 0: addresses
_PROP_ADDR_Y_P0 = [602, 578, 554, 530]
# Page 1: addresses
_PROP_ADDR_Y_P1 = [662, 638, 614, 590]

PROPERTY_FIELDS: dict[str, FieldCoord] = {}
for _slot_idx, _letter in enumerate("ABCD"):
    # Page 0 property addresses
    PROPERTY_FIELDS[f"p0_{_letter}_addr"] = FieldCoord(
        page=0, x=56, y=_PROP_ADDR_Y_P0[_slot_idx],
        width=170, alignment="left", font_size=8,
    )
    PROPERTY_FIELDS[f"p0_{_letter}_type"] = FieldCoord(
        page=0, x=238, y=_PROP_ADDR_Y_P0[_slot_idx],
        width=25, alignment="center", font_size=8,
    )
    PROPERTY_FIELDS[f"p0_{_letter}_fair_days"] = FieldCoord(
        page=0, x=405, y=_PROP_ADDR_Y_P0[_slot_idx],
        width=40, alignment="center", font_size=8,
    )
    PROPERTY_FIELDS[f"p0_{_letter}_personal_days"] = FieldCoord(
        page=0, x=520, y=_PROP_ADDR_Y_P0[_slot_idx],
        width=40, alignment="center", font_size=8,
    )
    # Page 1 property addresses
    PROPERTY_FIELDS[f"p1_{_letter}_addr"] = FieldCoord(
        page=1, x=56, y=_PROP_ADDR_Y_P1[_slot_idx],
        width=170, alignment="left", font_size=8,
    )
    PROPERTY_FIELDS[f"p1_{_letter}_type"] = FieldCoord(
        page=1, x=238, y=_PROP_ADDR_Y_P1[_slot_idx],
        width=25, alignment="center", font_size=8,
    )
    PROPERTY_FIELDS[f"p1_{_letter}_fair_days"] = FieldCoord(
        page=1, x=405, y=_PROP_ADDR_Y_P1[_slot_idx],
        width=40, alignment="center", font_size=8,
    )
    PROPERTY_FIELDS[f"p1_{_letter}_personal_days"] = FieldCoord(
        page=1, x=520, y=_PROP_ADDR_Y_P1[_slot_idx],
        width=40, alignment="center", font_size=8,
    )

# ---------------------------------------------------------------------------
# Per-property amount columns
#
# There are 4 columns: A, B, C, D. Amount right-edges (approximate):
#   A: x=354, B: x=426, C: x=498, D: x=570
# Column widths: ~70 points
#
# Lines 2a-19 have amounts in each column.
# Y positions (page 0):
#   2a=488  2b=476  2c=452
#   3=428   4=416   5=404   6=392   7=380
#   8=368   9=356   10=344  11=332  12=320
#   13=308  14=296  17=260
#   18=249  19=225
# Lines 15-16 are "reserved for future use".
# ---------------------------------------------------------------------------

# Column right-edge X positions (for right-aligned amounts)
_COL_X: dict[str, int] = {"A": 354, "B": 426, "C": 498, "D": 570}
_COL_WIDTH = 70

# Y positions for each line (page 0)
_LINE_Y_P0: dict[str, int] = {
    "2a": 488, "2b": 476, "2c": 452,
    "3": 428, "4": 416, "5": 404, "6": 392, "7": 380,
    "8": 368, "9": 356, "10": 344, "11": 332, "12": 320,
    "13": 308, "14": 296, "17": 260,
    "18": 249, "19": 225,
}

# Y positions for each line (page 1) — shifted up by ~60pt
_LINE_Y_P1: dict[str, int] = {
    "2a": 548, "2b": 536, "2c": 512,
    "3": 488, "4": 476, "5": 464, "6": 452, "7": 440,
    "8": 428, "9": 416, "10": 404, "11": 392, "12": 380,
    "13": 368, "14": 356, "17": 320,
    "18": 309, "19": 285,
}

# Build per-property FIELD_MAP keyed as "p{page}_{col}_{line}"
# e.g., "p0_A_2a", "p0_B_3", "p1_C_14"
FIELD_MAP: dict[str, FieldCoord] = {}

for _page_idx, _line_y in [(0, _LINE_Y_P0), (1, _LINE_Y_P1)]:
    for _col_letter, _col_right_x in _COL_X.items():
        for _line, _y in _line_y.items():
            _key = f"p{_page_idx}_{_col_letter}_{_line}"
            FIELD_MAP[_key] = FieldCoord(
                page=_page_idx,
                x=_col_right_x - _COL_WIDTH,
                y=_y,
                width=_COL_WIDTH,
                alignment="right",
                font_size=8,
            )

# ---------------------------------------------------------------------------
# Summary fields (lines 20-22) — single right column, page 0
# These are totals across all properties, right-aligned.
# Right edge at ~x=570, width=72
# ---------------------------------------------------------------------------
SUMMARY_FIELDS: dict[str, FieldCoord] = {
    # Line 20a: Total rental real estate income
    "20a": FieldCoord(page=0, x=505, y=200, width=70, alignment="right", font_size=9),
    # Line 20b: Total rental real estate expenses
    "20b": FieldCoord(page=0, x=505, y=188, width=70, alignment="right", font_size=9),
    # Line 21: Net income or (loss) from rental real estate
    "21": FieldCoord(page=0, x=505, y=164, width=70, alignment="right", font_size=9),
    # Line 22a: Net income from 8825 included on Sched K (see instructions)
    "22a": FieldCoord(page=0, x=505, y=140, width=70, alignment="right", font_size=9),
}

# Merge summary into FIELD_MAP for convenience
FIELD_MAP.update(SUMMARY_FIELDS)
