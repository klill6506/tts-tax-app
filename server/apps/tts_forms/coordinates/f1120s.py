"""
Field coordinate mappings for IRS Form 1120-S (2025 official print version).

Coordinates are in PDF points (1 point = 1/72 inch).
Origin (0, 0) is the bottom-left corner of each page.
Standard US letter size: 612 x 792 points.

Each entry maps a form line_number to:
    (page, x, y, width, alignment, font_size)

- page:      0-indexed PDF page number
- x:         horizontal position (left edge of field)
- y:         vertical position (baseline of text)
- width:     field width in points (for right-alignment padding)
- alignment: "left", "right", or "center"
- font_size: override font size (default 10)

PDF page structure (official 2025 print version, 5 pages):
    Page 0: Main form — Header, Income (1a-6), Deductions (7-21), Tax (22-28)
    Page 1: Schedule B — Other Information (yes/no questions, no amount fields)
    Page 2: Schedule B continued (top) + Schedule K lines 1-16 (bottom)
    Page 3: Schedule K continued (17-18, top) + Schedule L balance sheet (bottom)
    Page 4: Schedule M-1 + Schedule M-2

Note: Schedule A (Cost of Goods Sold) is Form 1125-A, a separate attachment.
      It is NOT included in this 5-page form.

Coordinates calibrated via pdfplumber extraction from the official PDF.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldCoord:
    """Position of a single form field on a PDF page."""

    page: int
    x: float
    y: float
    width: float = 120.0
    alignment: str = "right"
    font_size: int = 10


# ---------------------------------------------------------------------------
# Page 0 — Header / Entity Information
# ---------------------------------------------------------------------------
HEADER_FIELDS: dict[str, FieldCoord] = {
    # Entity name — entry area between Name and Address labels
    "entity_name": FieldCoord(
        page=0, x=132, y=676, width=310, alignment="left"
    ),
    # Street address
    "address_street": FieldCoord(
        page=0, x=132, y=652, width=248, alignment="left"
    ),
    # City, state, ZIP
    "address_city_state_zip": FieldCoord(
        page=0, x=132, y=632, width=306, alignment="left"
    ),
    # D — Employer identification number
    "ein": FieldCoord(page=0, x=464, y=676, width=120, alignment="left"),
    # E — Date incorporated
    "date_incorporated": FieldCoord(
        page=0, x=464, y=652, width=120, alignment="left"
    ),
    # Tax year beginning / ending (in the header banner)
    "tax_year_begin": FieldCoord(
        page=0, x=185, y=697, width=80, alignment="left", font_size=8
    ),
    "tax_year_end": FieldCoord(
        page=0, x=365, y=697, width=80, alignment="left", font_size=8
    ),
}

# ---------------------------------------------------------------------------
# Page 0 — Income (lines 1a through 6)
#
# Main amount column: right-aligned, right edge at x=588
# Sub-column (1a, 1b): smaller fields within the row
# Line 1 is a single row: 1a / b / c all share the same y position.
# ---------------------------------------------------------------------------
PAGE1_INCOME: dict[str, FieldCoord] = {
    # 1a gross receipts (sub-column, between description and "b" label)
    "1a": FieldCoord(page=0, x=145, y=545, width=85),
    # 1b returns/allowances (sub-column, between "b" description and "c")
    "1b": FieldCoord(page=0, x=335, y=545, width=75),
    # 1c balance (main column)
    "1c": FieldCoord(page=0, x=475, y=545, width=113),
    "2": FieldCoord(page=0, x=475, y=534, width=113),
    "3": FieldCoord(page=0, x=475, y=523, width=113),
    "4": FieldCoord(page=0, x=475, y=512, width=113),
    "5": FieldCoord(page=0, x=475, y=501, width=113),
    "6": FieldCoord(page=0, x=475, y=490, width=113),
}

# ---------------------------------------------------------------------------
# Page 0 — Deductions (lines 7 through 21)
# All in main amount column, ~10.9pt vertical spacing.
# ---------------------------------------------------------------------------
PAGE1_DEDUCTIONS: dict[str, FieldCoord] = {
    "7": FieldCoord(page=0, x=475, y=479, width=113),
    "8": FieldCoord(page=0, x=475, y=468, width=113),
    "9": FieldCoord(page=0, x=475, y=457, width=113),
    "10": FieldCoord(page=0, x=475, y=446, width=113),
    "11": FieldCoord(page=0, x=475, y=435, width=113),
    "12": FieldCoord(page=0, x=475, y=424, width=113),
    "13": FieldCoord(page=0, x=475, y=413, width=113),
    "14": FieldCoord(page=0, x=475, y=402, width=113),
    "15": FieldCoord(page=0, x=475, y=391, width=113),
    "16": FieldCoord(page=0, x=475, y=380, width=113),
    "17": FieldCoord(page=0, x=475, y=370, width=113),
    "18": FieldCoord(page=0, x=475, y=359, width=113),
    "19": FieldCoord(page=0, x=475, y=348, width=113),
    "20": FieldCoord(page=0, x=475, y=337, width=113),
    "21": FieldCoord(page=0, x=475, y=326, width=113),
}

# ---------------------------------------------------------------------------
# Page 0 — Tax and Payments (lines 22 through 28)
# ---------------------------------------------------------------------------
PAGE1_TAX: dict[str, FieldCoord] = {
    "22": FieldCoord(page=0, x=475, y=315, width=113),
    # Estimated tax payments / credits (sub-column)
    "23a": FieldCoord(page=0, x=345, y=304, width=113),
    "23b": FieldCoord(page=0, x=345, y=293, width=113),
    "23c": FieldCoord(page=0, x=345, y=282, width=113),
    "23d": FieldCoord(page=0, x=475, y=271, width=113),
    "24": FieldCoord(page=0, x=475, y=260, width=113),
    # Amount owed / Overpayment
    "25": FieldCoord(page=0, x=475, y=205, width=113),
    "26": FieldCoord(page=0, x=475, y=194, width=113),
    "27": FieldCoord(page=0, x=475, y=183, width=113),
    "28": FieldCoord(page=0, x=475, y=172, width=113),
}

# ---------------------------------------------------------------------------
# Schedule K — Shareholders' Pro Rata Share Items
# Lines 1-16 on page 2 (bottom half), lines 17-18 on page 3 (top)
# Amount column: right-aligned, right edge at x=588
# ---------------------------------------------------------------------------
SCHEDULE_K: dict[str, FieldCoord] = {
    # Page 2 — Schedule K lines 1 through 16
    # Amount column right edge ~570 (narrower than page 0's ~588)
    "K1": FieldCoord(page=2, x=457, y=559, width=113),
    "K2": FieldCoord(page=2, x=457, y=547, width=113),
    "K3c": FieldCoord(page=2, x=457, y=513, width=113),
    "K4": FieldCoord(page=2, x=457, y=501, width=113),
    "K5a": FieldCoord(page=2, x=457, y=490, width=113),
    "K6": FieldCoord(page=2, x=457, y=467, width=113),
    "K7": FieldCoord(page=2, x=457, y=455, width=113),
    "K8a": FieldCoord(page=2, x=457, y=444, width=113),
    "K9": FieldCoord(page=2, x=457, y=409, width=113),
    "K10": FieldCoord(page=2, x=457, y=397, width=113),
    "K11": FieldCoord(page=2, x=457, y=385, width=113),
    "K12a": FieldCoord(page=2, x=457, y=374, width=113),
    "K12b": FieldCoord(page=2, x=457, y=362, width=113),
    "K12c": FieldCoord(page=2, x=457, y=351, width=113),
    "K12d": FieldCoord(page=2, x=457, y=340, width=113),
    "K13a": FieldCoord(page=2, x=457, y=315, width=113),
    "K13b": FieldCoord(page=2, x=457, y=304, width=113),
    "K13c": FieldCoord(page=2, x=457, y=292, width=113),
    "K13d": FieldCoord(page=2, x=457, y=281, width=113),
    "K15a": FieldCoord(page=2, x=457, y=193, width=113),
    "K15b": FieldCoord(page=2, x=457, y=181, width=113),
    "K15c": FieldCoord(page=2, x=457, y=170, width=113),
    "K15d": FieldCoord(page=2, x=457, y=158, width=113),
    "K16a": FieldCoord(page=2, x=457, y=124, width=113),
    "K16b": FieldCoord(page=2, x=457, y=112, width=113),
    "K16c": FieldCoord(page=2, x=457, y=101, width=113),
    "K16d": FieldCoord(page=2, x=457, y=89, width=113),
    # Page 3 — Schedule K continued (lines 17-18)
    "K17a": FieldCoord(page=3, x=468, y=708, width=120),
    "K17b": FieldCoord(page=3, x=468, y=696, width=120),
    "K17c": FieldCoord(page=3, x=468, y=685, width=120),
    "K18": FieldCoord(page=3, x=468, y=638, width=120),
}

# ---------------------------------------------------------------------------
# Schedule L — Balance Sheet per Books (page 3, lower portion)
#
# Four amount columns:
#   (a) Beginning — gross/debit:  right edge ~327
#   (b) Beginning — net:          right edge ~407
#   (c) End of year — gross:      right edge ~487
#   (d) End of year — net:        right edge ~567
# ---------------------------------------------------------------------------
SCHEDULE_L: dict[str, FieldCoord] = {
    # Beginning of year — column (b) for simple lines, (a) for gross amounts
    "L1a": FieldCoord(page=3, x=332, y=599, width=75),   # Cash — col (b)
    "L2a": FieldCoord(page=3, x=252, y=587, width=75),   # Trade notes — col (a)
    "L2b": FieldCoord(page=3, x=332, y=575, width=75),   # Less allowance — col (b)
    "L3a": FieldCoord(page=3, x=332, y=563, width=75),   # Inventories — col (b)
    "L4a": FieldCoord(page=3, x=332, y=552, width=75),   # U.S. govt obligations
    "L5a": FieldCoord(page=3, x=332, y=540, width=75),   # Tax-exempt securities
    "L6a": FieldCoord(page=3, x=332, y=528, width=75),   # Other current assets
    "L7a": FieldCoord(page=3, x=332, y=517, width=75),   # Loans to shareholders
    "L8a": FieldCoord(page=3, x=332, y=505, width=75),   # Mortgage/RE loans
    "L9a": FieldCoord(page=3, x=332, y=493, width=75),   # Other investments
    "L10a": FieldCoord(page=3, x=252, y=481, width=75),  # Buildings — col (a)
    "L10b": FieldCoord(page=3, x=332, y=469, width=75),  # Less depreciation — col (b)
    "L11a": FieldCoord(page=3, x=252, y=458, width=75),  # Depletable — col (a)
    "L11b": FieldCoord(page=3, x=332, y=446, width=75),  # Less depletion — col (b)
    "L12a": FieldCoord(page=3, x=332, y=434, width=75),  # Land
    "L13a_gross": FieldCoord(page=3, x=252, y=422, width=75),  # Intangibles — col (a)
    "L13b": FieldCoord(page=3, x=332, y=411, width=75),  # Less amortization — col (b)
    "L14a": FieldCoord(page=3, x=332, y=399, width=75),  # Other assets
    "L15a": FieldCoord(page=3, x=332, y=387, width=75),  # Total assets
    "L16a": FieldCoord(page=3, x=332, y=364, width=75),  # Accounts payable
    "L17a": FieldCoord(page=3, x=332, y=352, width=75),  # Mortgages <1yr
    "L18a": FieldCoord(page=3, x=332, y=340, width=75),  # Other current liabilities
    "L19a": FieldCoord(page=3, x=332, y=328, width=75),  # Loans from shareholders
    "L20a": FieldCoord(page=3, x=332, y=317, width=75),  # Mortgages 1yr+
    "L21a": FieldCoord(page=3, x=332, y=305, width=75),  # Other liabilities
    "L22a": FieldCoord(page=3, x=332, y=293, width=75),  # Capital stock
    "L23a": FieldCoord(page=3, x=332, y=281, width=75),  # Additional paid-in capital
    "L24a": FieldCoord(page=3, x=332, y=270, width=75),  # Retained earnings
    "L25a": FieldCoord(page=3, x=332, y=258, width=75),  # Adjustments to equity
    "L26a": FieldCoord(page=3, x=332, y=246, width=75),  # Less treasury stock
    "L27a": FieldCoord(page=3, x=332, y=235, width=75),  # Total liabilities + equity
    # End of year — column (d) for simple lines, (c) for gross amounts
    "L1d": FieldCoord(page=3, x=492, y=599, width=75),
    "L2c": FieldCoord(page=3, x=412, y=587, width=75),   # Trade notes — col (c)
    "L2d": FieldCoord(page=3, x=492, y=575, width=75),   # Less allowance — col (d)
    "L3d": FieldCoord(page=3, x=492, y=563, width=75),
    "L4d": FieldCoord(page=3, x=492, y=552, width=75),
    "L5d": FieldCoord(page=3, x=492, y=540, width=75),
    "L6d": FieldCoord(page=3, x=492, y=528, width=75),
    "L7d": FieldCoord(page=3, x=492, y=517, width=75),
    "L8d": FieldCoord(page=3, x=492, y=505, width=75),
    "L9d": FieldCoord(page=3, x=492, y=493, width=75),
    "L10c": FieldCoord(page=3, x=412, y=481, width=75),  # Buildings — col (c)
    "L10d": FieldCoord(page=3, x=492, y=469, width=75),  # Less depreciation — col (d)
    "L11c": FieldCoord(page=3, x=412, y=458, width=75),  # Depletable — col (c)
    "L11d": FieldCoord(page=3, x=492, y=446, width=75),  # Less depletion — col (d)
    "L12d": FieldCoord(page=3, x=492, y=434, width=75),
    "L13c": FieldCoord(page=3, x=412, y=422, width=75),  # Intangibles — col (c)
    "L13d": FieldCoord(page=3, x=492, y=411, width=75),  # Less amortization — col (d)
    "L14d": FieldCoord(page=3, x=492, y=399, width=75),
    "L15d": FieldCoord(page=3, x=492, y=387, width=75),
    "L16d": FieldCoord(page=3, x=492, y=364, width=75),
    "L17d": FieldCoord(page=3, x=492, y=352, width=75),
    "L18d": FieldCoord(page=3, x=492, y=340, width=75),
    "L19d": FieldCoord(page=3, x=492, y=328, width=75),
    "L20d": FieldCoord(page=3, x=492, y=317, width=75),
    "L21d": FieldCoord(page=3, x=492, y=305, width=75),
    "L22d": FieldCoord(page=3, x=492, y=293, width=75),
    "L23d": FieldCoord(page=3, x=492, y=281, width=75),
    "L24d": FieldCoord(page=3, x=492, y=270, width=75),
    "L25d": FieldCoord(page=3, x=492, y=258, width=75),
    "L26d": FieldCoord(page=3, x=492, y=246, width=75),
    "L27d": FieldCoord(page=3, x=492, y=235, width=75),
}

# ---------------------------------------------------------------------------
# Schedule M-1 — Reconciliation of Income (page 4, top)
#
# Two-column layout:
#   Left column (lines 1-4): additions.  Amount right edge ~x=225
#   Right column (lines 5-8): subtractions.  Amount right edge ~x=588
# ---------------------------------------------------------------------------
SCHEDULE_M1: dict[str, FieldCoord] = {
    # Left column
    "M1_1": FieldCoord(page=4, x=155, y=710, width=70),
    "M1_2": FieldCoord(page=4, x=155, y=698, width=70),
    "M1_3a": FieldCoord(page=4, x=115, y=614, width=110),
    "M1_3b": FieldCoord(page=4, x=165, y=590, width=60),
    "M1_4": FieldCoord(page=4, x=155, y=566, width=70),
    # Right column
    "M1_5": FieldCoord(page=4, x=500, y=710, width=88),
    "M1_6": FieldCoord(page=4, x=500, y=650, width=88),
    "M1_7": FieldCoord(page=4, x=500, y=590, width=88),
    "M1_8": FieldCoord(page=4, x=500, y=578, width=88),
}

# ---------------------------------------------------------------------------
# Schedule M-2 — Analysis of AAA, STUPIT, E&P, Other (page 4, bottom)
#
# Column (a) — Accumulated adjustments account.  Right edge ~x=307
# Lines 1-8 are vertically stacked with ~12pt spacing.
# ---------------------------------------------------------------------------
SCHEDULE_M2: dict[str, FieldCoord] = {
    "M2_1": FieldCoord(page=4, x=222, y=482, width=85),
    "M2_2": FieldCoord(page=4, x=222, y=470, width=85),
    "M2_3": FieldCoord(page=4, x=222, y=458, width=85),
    "M2_4": FieldCoord(page=4, x=222, y=446, width=85),
    "M2_5": FieldCoord(page=4, x=222, y=434, width=85),
    "M2_6": FieldCoord(page=4, x=222, y=422, width=85),
    "M2_7": FieldCoord(page=4, x=222, y=410, width=85),
    "M2_8": FieldCoord(page=4, x=222, y=392, width=85),
}

# ---------------------------------------------------------------------------
# Combined field map — used by the renderer
# ---------------------------------------------------------------------------
FIELD_MAP: dict[str, FieldCoord] = {
    **PAGE1_INCOME,
    **PAGE1_DEDUCTIONS,
    **PAGE1_TAX,
    **SCHEDULE_K,
    **SCHEDULE_L,
    **SCHEDULE_M1,
    **SCHEDULE_M2,
}
