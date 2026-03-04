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
#
# Positions calibrated by Ken via coord_tool_1120s.py (Mar 2026).
# Fields Ken removed from the form: state_incorporated, chk_initial_return,
# number_of_shareholders, product_or_service, phone, tax_year_begin,
# tax_year_end, address_city_state_zip (replaced by split fields).
# ---------------------------------------------------------------------------
HEADER_FIELDS: dict[str, FieldCoord] = {
    # ----- Entity info (left side, consistent x=141.3) -----
    # A — Entity name
    "entity_name": FieldCoord(
        page=0, x=141.3, y=679.4, width=310, alignment="left"
    ),
    # B — Street address
    "address_street": FieldCoord(
        page=0, x=141.3, y=655.3, width=248, alignment="left"
    ),
    # C — City, State, ZIP (three separate fields)
    "address_city": FieldCoord(
        page=0, x=141.3, y=630.0, width=190, alignment="left"
    ),
    "address_state": FieldCoord(
        page=0, x=256.0, y=631.0, width=30, alignment="left"
    ),
    "address_zip": FieldCoord(
        page=0, x=383.0, y=632.0, width=80, alignment="left"
    ),

    # ----- Entity info (right side) -----
    # D — Employer identification number
    "ein": FieldCoord(
        page=0, x=470.0, y=680.6, width=120, alignment="left"
    ),
    # E — Date incorporated
    "date_incorporated": FieldCoord(
        page=0, x=471.3, y=656.7, width=120, alignment="left"
    ),
    # F — Total assets (end of year)
    "total_assets": FieldCoord(
        page=0, x=470.0, y=632.0, width=100, alignment="right", font_size=9
    ),

    # ----- Line G area -----
    # S election date (Ken positioned in top-left area)
    "s_election_date": FieldCoord(
        page=0, x=43.4, y=680.7, width=90, alignment="left", font_size=8
    ),
    # Business activity code (Ken positioned below s_election_date)
    "business_activity_code": FieldCoord(
        page=0, x=42.6, y=644.0, width=90, alignment="left", font_size=9
    ),
    # Check if electing S corp this year
    "chk_s_election": FieldCoord(
        page=0, x=406.0, y=613.0, width=10, alignment="left", font_size=9
    ),

    # ----- Line H checkboxes (Ken's adjusted positions) -----
    "chk_final_return": FieldCoord(
        page=0, x=102.0, y=600.7, width=10, alignment="left", font_size=9
    ),
    "chk_name_change": FieldCoord(
        page=0, x=182.7, y=600.0, width=10, alignment="left", font_size=9
    ),
    "chk_address_change": FieldCoord(
        page=0, x=273.0, y=600.0, width=10, alignment="left", font_size=9
    ),
    "chk_amended_return": FieldCoord(
        page=0, x=365.4, y=600.7, width=10, alignment="left", font_size=9
    ),
    # S election termination or revocation
    "s_election_termination": FieldCoord(
        page=0, x=460.0, y=600.0, width=100, alignment="left", font_size=8
    ),
    # Check if Schedule M-3 attached
    "chk_sch_m3": FieldCoord(
        page=0, x=170.0, y=588.0, width=10, alignment="left", font_size=9
    ),

    # ----- Sign Here / Third Party Designee -----
    # May the IRS discuss this return with the preparer?
    "chk_discuss_yes": FieldCoord(
        page=0, x=532.0, y=119.0, width=10, alignment="left", font_size=9
    ),
    "chk_discuss_no": FieldCoord(
        page=0, x=566.0, y=119.0, width=10, alignment="left", font_size=9
    ),

    # ----- Paid Preparer Use Only (Ken's adjusted positions) -----
    "preparer_signature": FieldCoord(
        page=0, x=231.0, y=98.0, width=130, alignment="left", font_size=8
    ),
    "preparer_name": FieldCoord(
        page=0, x=97.0, y=96.0, width=170, alignment="left", font_size=8
    ),
    "preparer_date": FieldCoord(
        page=0, x=403.7, y=96.7, width=40, alignment="left", font_size=8
    ),
    "preparer_ptin": FieldCoord(
        page=0, x=516.4, y=96.6, width=85, alignment="left", font_size=8
    ),
    "preparer_self_employed": FieldCoord(
        page=0, x=484.3, y=106.0, width=10, alignment="left", font_size=9
    ),
    "firm_name": FieldCoord(
        page=0, x=140.3, y=85.7, width=310, alignment="left", font_size=8
    ),
    "firm_ein": FieldCoord(
        page=0, x=516.3, y=86.7, width=100, alignment="left", font_size=8
    ),
    # Firm address — street on one line, city/state/zip on the line below
    "firm_street": FieldCoord(
        page=0, x=140.3, y=71.3, width=160, alignment="left", font_size=8
    ),
    "firm_city": FieldCoord(
        page=0, x=140.0, y=65.3, width=90, alignment="left", font_size=8
    ),
    "firm_state": FieldCoord(
        page=0, x=377.0, y=64.3, width=25, alignment="left", font_size=8
    ),
    "firm_zip": FieldCoord(
        page=0, x=516.0, y=66.3, width=70, alignment="left", font_size=8
    ),
    "firm_phone": FieldCoord(
        page=0, x=516.0, y=75.0, width=100, alignment="left", font_size=8
    ),
}

# ---------------------------------------------------------------------------
# Page 0 — Income (lines 1a through 6)
#
# Main amount column: right-aligned, right edge at x≈578 (coord tool position)
# For right-aligned fields: x = coord_tool_position − width, so that
# drawRightString(x + width) places the right edge at the coord tool position.
# Sub-column (1a, 1b): smaller fields within the row
# Line 1 is a single row: 1a / b / c all share the same y position.
# ---------------------------------------------------------------------------
PAGE1_INCOME: dict[str, FieldCoord] = {
    # 1a gross receipts (sub-column)
    # x = coord_tool 215.7 − width 85 = 130.7 (right edge renders at 215.7)
    "1a": FieldCoord(page=0, x=130.7, y=549.0, width=85),
    # 1b returns/allowances (sub-column)
    # x = coord_tool 397.6 − width 75 = 322.6 (right edge renders at 397.6)
    "1b": FieldCoord(page=0, x=322.6, y=549.0, width=75),
    # 1c–6: main column.  coord_tool right edge = 578.3, width 113
    # x = 578.3 − 113 = 465.3
    "1c": FieldCoord(page=0, x=465.3, y=549.7, width=113),
    "2": FieldCoord(page=0, x=465.3, y=538.0, width=113),
    "3": FieldCoord(page=0, x=465.3, y=526.3, width=113),
    "4": FieldCoord(page=0, x=465.3, y=514.7, width=113),
    "5": FieldCoord(page=0, x=465.3, y=503.0, width=113),
    "6": FieldCoord(page=0, x=465.3, y=494.0, width=113),
}

# ---------------------------------------------------------------------------
# Page 0 — Deductions (lines 7 through 21)
# All in main amount column, ~10.9pt vertical spacing.
# ---------------------------------------------------------------------------
PAGE1_DEDUCTIONS: dict[str, FieldCoord] = {
    # All main column: coord_tool right edge 578.3 − width 113 = 465.3
    "7": FieldCoord(page=0, x=465.3, y=482.3, width=113),
    "8": FieldCoord(page=0, x=465.3, y=470.7, width=113),
    "9": FieldCoord(page=0, x=465.3, y=460.3, width=113),
    "10": FieldCoord(page=0, x=465.3, y=449.3, width=113),
    "11": FieldCoord(page=0, x=465.3, y=437.7, width=113),
    "12": FieldCoord(page=0, x=465.3, y=428.0, width=113),
    "13": FieldCoord(page=0, x=465.3, y=417.0, width=113),
    "14": FieldCoord(page=0, x=465.3, y=406.0, width=113),
    "15": FieldCoord(page=0, x=465.3, y=394.3, width=113),
    "16": FieldCoord(page=0, x=465.3, y=382.7, width=113),
    "17": FieldCoord(page=0, x=465.3, y=372.0, width=113),
    "18": FieldCoord(page=0, x=465.3, y=362.3, width=113),
    "19": FieldCoord(page=0, x=465.3, y=350.0, width=113),
    "20": FieldCoord(page=0, x=465.3, y=339.0, width=113),
    "21": FieldCoord(page=0, x=465.3, y=328.7, width=113),
}

# ---------------------------------------------------------------------------
# Page 0 — Tax and Payments (lines 22 through 28)
# ---------------------------------------------------------------------------
PAGE1_TAX: dict[str, FieldCoord] = {
    # Main column: coord_tool 578.3 − 113 = 465.3
    "22": FieldCoord(page=0, x=465.3, y=318.3, width=113),
    # Sub-column: coord_tool 445.0 − 113 = 332.0
    "23a": FieldCoord(page=0, x=332.0, y=306.7, width=113),
    "23b": FieldCoord(page=0, x=332.0, y=296.4, width=113),
    # 23c total (main column)
    "23c": FieldCoord(page=0, x=465.3, y=286.0, width=113),
    # Line 24 sub-items (sub-column: coord_tool 445.0 − 113 = 332.0)
    "24": FieldCoord(page=0, x=332.0, y=264.7, width=113),
    "24b": FieldCoord(page=0, x=332.0, y=253.0, width=113),
    "24c": FieldCoord(page=0, x=332.0, y=241.0, width=113),
    # 24d total (main column)
    "24d": FieldCoord(page=0, x=465.3, y=229.0, width=113),
    # 24z other (sub-column)
    "24z": FieldCoord(page=0, x=332.0, y=218.0, width=113),
    # Amount owed / Overpayment (main column)
    "25": FieldCoord(page=0, x=465.3, y=208.3, width=113),
    "26": FieldCoord(page=0, x=465.3, y=196.0, width=113),
    "27": FieldCoord(page=0, x=465.3, y=185.7, width=113),
    "28": FieldCoord(page=0, x=465.3, y=175.3, width=113),
}

# ---------------------------------------------------------------------------
# Schedule K — Shareholders' Pro Rata Share Items
# Lines 1-16 on page 2 (bottom half), lines 17-18 on page 3 (top)
# Amount column: right-aligned, right edge at x=588
# ---------------------------------------------------------------------------
SCHEDULE_K: dict[str, FieldCoord] = {
    # Page 2 — Schedule K lines 1 through 16
    # coord_tool right edge = 550, width 113 → x = 550 − 113 = 437
    "K1": FieldCoord(page=2, x=437, y=565, width=113),
    "K2": FieldCoord(page=2, x=437, y=550, width=113),
    "K3c": FieldCoord(page=2, x=437, y=521, width=113),
    "K4": FieldCoord(page=2, x=437, y=505, width=113),
    "K5a": FieldCoord(page=2, x=437, y=493, width=113),
    "K6": FieldCoord(page=2, x=437, y=473, width=113),
    "K7": FieldCoord(page=2, x=437, y=459, width=113),
    "K8a": FieldCoord(page=2, x=437, y=445, width=113),
    "K9": FieldCoord(page=2, x=437, y=417, width=113),
    "K10": FieldCoord(page=2, x=437, y=402, width=113),
    "K11": FieldCoord(page=2, x=437, y=389, width=113),
    "K12a": FieldCoord(page=2, x=437, y=377, width=113),
    "K12b": FieldCoord(page=2, x=437, y=366, width=113),
    "K12c": FieldCoord(page=2, x=437, y=353, width=113),
    "K12d": FieldCoord(page=2, x=438, y=342, width=113),
    "K13a": FieldCoord(page=2, x=437, y=321, width=113),
    "K13b": FieldCoord(page=2, x=437, y=307, width=113),
    "K13c": FieldCoord(page=2, x=437, y=293, width=113),
    "K13d": FieldCoord(page=2, x=437, y=283, width=113),
    "K15a": FieldCoord(page=2, x=437, y=197, width=113),
    "K15b": FieldCoord(page=2, x=437, y=184, width=113),
    "K15c": FieldCoord(page=2, x=437, y=172, width=113),
    "K15d": FieldCoord(page=2, x=437, y=159, width=113),
    "K16a": FieldCoord(page=2, x=437, y=128, width=113),
    "K16b": FieldCoord(page=2, x=437, y=115, width=113),
    "K16c": FieldCoord(page=2, x=437, y=104, width=113),
    "K16d": FieldCoord(page=2, x=437, y=92, width=113),
    # Page 3 — Schedule K continued (lines 17-18)
    # coord_tool right edge = 550, width 120 → x = 550 − 120 = 430
    "K17a": FieldCoord(page=3, x=430, y=712, width=120),
    "K17b": FieldCoord(page=3, x=430, y=699, width=120),
    "K17c": FieldCoord(page=3, x=430, y=688, width=120),
    "K18": FieldCoord(page=3, x=430, y=644, width=120),
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
    # Coord tool right-edge positions (width=75 for all L fields):
    #   (a) col right edge: 308 → x = 308 − 75 = 233
    #   (b) col right edge: 390 → x = 390 − 75 = 315
    #   (c) col right edge: 470 → x = 470 − 75 = 395
    #   (d) col right edge: 550 → x = 550 − 75 = 475
    #
    # Beginning of year — column (b) for simple lines, (a) for gross amounts
    "L1a": FieldCoord(page=3, x=315, y=604, width=75),   # Cash — col (b)
    "L2a": FieldCoord(page=3, x=233, y=592, width=75),   # Trade notes — col (a)
    "L2b": FieldCoord(page=3, x=315, y=580, width=75),   # Less allowance — col (b)
    "L3a": FieldCoord(page=3, x=315, y=566, width=75),   # Inventories — col (b)
    "L4a": FieldCoord(page=3, x=315, y=553, width=75),   # U.S. govt obligations
    "L5a": FieldCoord(page=3, x=315, y=542, width=75),   # Tax-exempt securities
    "L6a": FieldCoord(page=3, x=315, y=532, width=75),   # Other current assets
    "L7a": FieldCoord(page=3, x=315, y=520, width=75),   # Loans to shareholders
    "L8a": FieldCoord(page=3, x=315, y=506, width=75),   # Mortgage/RE loans
    "L9a": FieldCoord(page=3, x=315, y=494, width=75),   # Other investments
    "L10a": FieldCoord(page=3, x=233, y=485, width=75),  # Buildings — col (a)
    "L10b": FieldCoord(page=3, x=315, y=474, width=75),  # Less depreciation — col (b)
    "L11a": FieldCoord(page=3, x=233, y=462, width=75),  # Depletable — col (a)
    "L11b": FieldCoord(page=3, x=315, y=451, width=75),  # Less depletion — col (b)
    "L12a": FieldCoord(page=3, x=315, y=438, width=75),  # Land
    "L13a_gross": FieldCoord(page=3, x=233, y=427, width=75),  # Intangibles — col (a)
    "L13b": FieldCoord(page=3, x=315, y=417, width=75),  # Less amortization — col (b)
    "L14a": FieldCoord(page=3, x=315, y=405, width=75),  # Other assets
    "L15a": FieldCoord(page=3, x=315, y=391, width=75),  # Total assets
    "L16a": FieldCoord(page=3, x=315, y=369, width=75),  # Accounts payable
    "L17a": FieldCoord(page=3, x=315, y=357, width=75),  # Mortgages <1yr
    "L18a": FieldCoord(page=3, x=315, y=344, width=75),  # Other current liabilities
    "L19a": FieldCoord(page=3, x=315, y=332, width=75),  # Loans from shareholders
    "L20a": FieldCoord(page=3, x=315, y=320, width=75),  # Mortgages 1yr+
    "L21a": FieldCoord(page=3, x=315, y=307, width=75),  # Other liabilities
    "L22a": FieldCoord(page=3, x=315, y=296, width=75),  # Capital stock
    "L23a": FieldCoord(page=3, x=315, y=285, width=75),  # Additional paid-in capital
    "L24a": FieldCoord(page=3, x=315, y=273, width=75),  # Retained earnings
    "L25a": FieldCoord(page=3, x=315, y=263, width=75),  # Adjustments to equity
    "L26a": FieldCoord(page=3, x=316, y=249, width=75),  # Less treasury stock
    "L27a": FieldCoord(page=3, x=315, y=236, width=75),  # Total liabilities + equity
    # End of year — column (d) for simple lines, (c) for gross amounts
    "L1d": FieldCoord(page=3, x=475, y=605, width=75),
    "L2c": FieldCoord(page=3, x=395, y=592, width=75),   # Trade notes — col (c)
    "L2d": FieldCoord(page=3, x=475, y=579, width=75),   # Less allowance — col (d)
    "L3d": FieldCoord(page=3, x=475, y=567, width=75),
    "L4d": FieldCoord(page=3, x=475, y=555, width=75),
    "L5d": FieldCoord(page=3, x=475, y=543, width=75),
    "L6d": FieldCoord(page=3, x=475, y=533, width=75),
    "L7d": FieldCoord(page=3, x=475, y=522, width=75),
    "L8d": FieldCoord(page=3, x=475, y=509, width=75),
    "L9d": FieldCoord(page=3, x=475, y=496, width=75),
    "L10c": FieldCoord(page=3, x=395, y=485, width=75),  # Buildings — col (c)
    "L10d": FieldCoord(page=3, x=475, y=476, width=75),  # Less depreciation — col (d)
    "L11c": FieldCoord(page=3, x=395, y=462, width=75),  # Depletable — col (c)
    "L11d": FieldCoord(page=3, x=475, y=450, width=75),  # Less depletion — col (d)
    "L12d": FieldCoord(page=3, x=475, y=438, width=75),
    "L13c": FieldCoord(page=3, x=395, y=427, width=75),  # Intangibles — col (c)
    "L13d": FieldCoord(page=3, x=475, y=415, width=75),  # Less amortization — col (d)
    "L14d": FieldCoord(page=3, x=475, y=402, width=75),
    "L15d": FieldCoord(page=3, x=475, y=390, width=75),
    "L16d": FieldCoord(page=3, x=475, y=369, width=75),
    "L17d": FieldCoord(page=3, x=475, y=355, width=75),
    "L18d": FieldCoord(page=3, x=475, y=344, width=75),
    "L19d": FieldCoord(page=3, x=475, y=331, width=75),
    "L20d": FieldCoord(page=3, x=475, y=321, width=75),
    "L21d": FieldCoord(page=3, x=475, y=309, width=75),
    "L22d": FieldCoord(page=3, x=475, y=298, width=75),
    "L23d": FieldCoord(page=3, x=475, y=286, width=75),
    "L24d": FieldCoord(page=3, x=475, y=275, width=75),
    "L25d": FieldCoord(page=3, x=475, y=262, width=75),
    "L26d": FieldCoord(page=3, x=475, y=251, width=75),
    "L27d": FieldCoord(page=3, x=475, y=237, width=75),
}

# ---------------------------------------------------------------------------
# Schedule M-1 — Reconciliation of Income (page 4, top)
#
# Two-column layout:
#   Left column (lines 1-4): additions.  Amount right edge ~x=225
#   Right column (lines 5-8): subtractions.  Amount right edge ~x=588
# ---------------------------------------------------------------------------
SCHEDULE_M1: dict[str, FieldCoord] = {
    # Left column: coord_tool right edge 290, width 70 → x = 220
    "M1_1": FieldCoord(page=4, x=220, y=716, width=70),
    "M1_2": FieldCoord(page=4, x=220, y=669, width=70),
    # 3a: coord_tool 203, width 110 → x = 93
    "M1_3a": FieldCoord(page=4, x=93, y=621, width=110),
    # 3b: coord_tool 203, width 60 → x = 143
    "M1_3b": FieldCoord(page=4, x=143, y=597, width=60),
    "M1_4": FieldCoord(page=4, x=220, y=573, width=70),
    # Right column: coord_tool right edge 570, width 88 → x = 482
    "M1_5": FieldCoord(page=4, x=482, y=670, width=88),
    "M1_6": FieldCoord(page=4, x=482, y=609, width=88),
    "M1_7": FieldCoord(page=4, x=482, y=594, width=88),
    "M1_8": FieldCoord(page=4, x=482, y=557, width=88),
}

# ---------------------------------------------------------------------------
# Schedule M-2 — Analysis of AAA, STUPIT, E&P, Other (page 4, bottom)
#
# Column (a) — Accumulated adjustments account.  Right edge ~x=307
# Lines 1-8 are vertically stacked with ~12pt spacing.
# ---------------------------------------------------------------------------
SCHEDULE_M2: dict[str, FieldCoord] = {
    # coord_tool right edge 290, width 85 → x = 205
    "M2_1": FieldCoord(page=4, x=205, y=486, width=85),
    "M2_2": FieldCoord(page=4, x=207, y=474, width=85),
    "M2_3": FieldCoord(page=4, x=205, y=461, width=85),
    "M2_4": FieldCoord(page=4, x=205, y=448, width=85),
    "M2_5": FieldCoord(page=4, x=205, y=438, width=85),
    "M2_6": FieldCoord(page=4, x=205, y=426, width=85),
    "M2_7": FieldCoord(page=4, x=205, y=415, width=85),
    "M2_8": FieldCoord(page=4, x=205, y=393, width=85),
}

# ---------------------------------------------------------------------------
# Schedule B — Other Information (Yes/No questions)
#
# Pages 1-2.  Each boolean question has a "Yes" column and "No" column.
# Coordinate keys use _yes / _no suffixes (e.g. B3_yes, B3_no).
# The renderer expands boolean field values into the correct suffix.
#
# Yes column center: x≈533 (page 1) / x≈532 (page 2)
# No  column center: x≈555 (page 1) / x≈554 (page 2)
#
# Y positions derived from dot-leader extraction on the official 2025 PDF.
# B7 is a single "check this box" (no No column).
# B8 is a currency amount field.
# ---------------------------------------------------------------------------
SCHEDULE_B: dict[str, FieldCoord] = {
    # --- Page 1 ---
    # Line 3
    "B3_yes": FieldCoord(page=1, x=533, y=663, width=10, alignment="left", font_size=9),
    "B3_no": FieldCoord(page=1, x=555, y=663, width=10, alignment="left", font_size=9),
    # Line 4a
    "B4a_yes": FieldCoord(page=1, x=533, y=612, width=10, alignment="left", font_size=9),
    "B4a_no": FieldCoord(page=1, x=555, y=612, width=10, alignment="left", font_size=9),
    # Line 4b
    "B4b_yes": FieldCoord(page=1, x=533, y=496, width=10, alignment="left", font_size=9),
    "B4b_no": FieldCoord(page=1, x=555, y=496, width=10, alignment="left", font_size=9),
    # Line 5a
    "B5a_yes": FieldCoord(page=1, x=533, y=405, width=10, alignment="left", font_size=9),
    "B5a_no": FieldCoord(page=1, x=555, y=405, width=10, alignment="left", font_size=9),
    # Line 5b
    "B5b_yes": FieldCoord(page=1, x=533, y=359, width=10, alignment="left", font_size=9),
    "B5b_no": FieldCoord(page=1, x=555, y=359, width=10, alignment="left", font_size=9),
    # Line 6
    "B6_yes": FieldCoord(page=1, x=533, y=303, width=10, alignment="left", font_size=9),
    "B6_no": FieldCoord(page=1, x=555, y=303, width=10, alignment="left", font_size=9),
    # Line 7 — single checkbox ("Check this box if …"), no Yes/No pair
    "B7_yes": FieldCoord(page=1, x=533, y=287, width=10, alignment="left", font_size=9),
    # Line 8 — currency amount (net unrealized built-in gain)
    "B8": FieldCoord(page=1, x=555, y=245, width=50, alignment="right", font_size=9),
    # Line 9
    "B9_yes": FieldCoord(page=1, x=533, y=193, width=10, alignment="left", font_size=9),
    "B9_no": FieldCoord(page=1, x=555, y=193, width=10, alignment="left", font_size=9),
    # Line 10
    "B10_yes": FieldCoord(page=1, x=533, y=181, width=10, alignment="left", font_size=9),
    "B10_no": FieldCoord(page=1, x=555, y=181, width=10, alignment="left", font_size=9),
    # Line 11
    "B11_yes": FieldCoord(page=1, x=533, y=113, width=10, alignment="left", font_size=9),
    "B11_no": FieldCoord(page=1, x=555, y=113, width=10, alignment="left", font_size=9),

    # --- Page 2 (Schedule B continued) ---
    # Line 12
    "B12_yes": FieldCoord(page=2, x=532, y=703, width=10, alignment="left", font_size=9),
    "B12_no": FieldCoord(page=2, x=554, y=703, width=10, alignment="left", font_size=9),
    # Line 13
    "B13_yes": FieldCoord(page=2, x=532, y=678, width=10, alignment="left", font_size=9),
    "B13_no": FieldCoord(page=2, x=554, y=678, width=10, alignment="left", font_size=9),
    # Line 14a
    "B14a_yes": FieldCoord(page=2, x=532, y=666, width=10, alignment="left", font_size=9),
    "B14a_no": FieldCoord(page=2, x=554, y=666, width=10, alignment="left", font_size=9),
    # Line 14b
    "B14b_yes": FieldCoord(page=2, x=532, y=655, width=10, alignment="left", font_size=9),
    "B14b_no": FieldCoord(page=2, x=554, y=655, width=10, alignment="left", font_size=9),
    # Line 15
    "B15_yes": FieldCoord(page=2, x=532, y=643, width=10, alignment="left", font_size=9),
    "B15_no": FieldCoord(page=2, x=554, y=643, width=10, alignment="left", font_size=9),
    # Line 16
    "B16_yes": FieldCoord(page=2, x=532, y=609, width=10, alignment="left", font_size=9),
    "B16_no": FieldCoord(page=2, x=554, y=609, width=10, alignment="left", font_size=9),
}

# ---------------------------------------------------------------------------
# Combined field map — used by the renderer
# ---------------------------------------------------------------------------
FIELD_MAP: dict[str, FieldCoord] = {
    **PAGE1_INCOME,
    **PAGE1_DEDUCTIONS,
    **PAGE1_TAX,
    **SCHEDULE_B,
    **SCHEDULE_K,
    **SCHEDULE_L,
    **SCHEDULE_M1,
    **SCHEDULE_M2,
}
