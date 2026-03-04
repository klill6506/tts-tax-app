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
    # y shifted −4pt from coord tool calibration
    # A — Entity name
    "entity_name": FieldCoord(
        page=0, x=141.3, y=675.4, width=310, alignment="left"
    ),
    # B — Street address
    "address_street": FieldCoord(
        page=0, x=141.3, y=651.3, width=248, alignment="left"
    ),
    # C — City, State, ZIP (three separate fields)
    "address_city": FieldCoord(
        page=0, x=141.3, y=626.0, width=190, alignment="left"
    ),
    "address_state": FieldCoord(
        page=0, x=256.0, y=627.0, width=30, alignment="left"
    ),
    "address_zip": FieldCoord(
        page=0, x=383.0, y=628.0, width=80, alignment="left"
    ),

    # ----- Entity info (right side) -----
    # D — Employer identification number
    "ein": FieldCoord(
        page=0, x=470.0, y=676.6, width=120, alignment="left"
    ),
    # E — Date incorporated
    "date_incorporated": FieldCoord(
        page=0, x=471.3, y=652.7, width=120, alignment="left"
    ),
    # F — Total assets (end of year)
    "total_assets": FieldCoord(
        page=0, x=470.0, y=628.0, width=100, alignment="right", font_size=9
    ),

    # ----- Line G area -----
    # S election date (Ken positioned in top-left area)
    "s_election_date": FieldCoord(
        page=0, x=43.4, y=676.7, width=90, alignment="left", font_size=8
    ),
    # Business activity code (Ken positioned below s_election_date)
    "business_activity_code": FieldCoord(
        page=0, x=42.6, y=640.0, width=90, alignment="left", font_size=9
    ),
    # Check if electing S corp this year
    "chk_s_election": FieldCoord(
        page=0, x=406.0, y=609.0, width=10, alignment="left", font_size=9
    ),

    # ----- Line H checkboxes (Ken's adjusted positions) -----
    "chk_final_return": FieldCoord(
        page=0, x=102.0, y=596.7, width=10, alignment="left", font_size=9
    ),
    "chk_name_change": FieldCoord(
        page=0, x=182.7, y=596.0, width=10, alignment="left", font_size=9
    ),
    "chk_address_change": FieldCoord(
        page=0, x=273.0, y=596.0, width=10, alignment="left", font_size=9
    ),
    "chk_amended_return": FieldCoord(
        page=0, x=365.4, y=596.7, width=10, alignment="left", font_size=9
    ),
    # S election termination or revocation
    "s_election_termination": FieldCoord(
        page=0, x=460.0, y=596.0, width=100, alignment="left", font_size=8
    ),
    # Check if Schedule M-3 attached
    "chk_sch_m3": FieldCoord(
        page=0, x=170.0, y=584.0, width=10, alignment="left", font_size=9
    ),

    # ----- Sign Here / Third Party Designee -----
    # May the IRS discuss this return with the preparer?
    # y shifted −4pt (preparer section)
    "chk_discuss_yes": FieldCoord(
        page=0, x=532.0, y=115.0, width=10, alignment="left", font_size=9
    ),
    "chk_discuss_no": FieldCoord(
        page=0, x=566.0, y=115.0, width=10, alignment="left", font_size=9
    ),

    # ----- Paid Preparer Use Only — y shifted −4pt -----
    "preparer_signature": FieldCoord(
        page=0, x=231.0, y=94.0, width=130, alignment="left", font_size=8
    ),
    "preparer_name": FieldCoord(
        page=0, x=97.0, y=92.0, width=170, alignment="left", font_size=8
    ),
    "preparer_date": FieldCoord(
        page=0, x=403.7, y=92.7, width=40, alignment="left", font_size=8
    ),
    "preparer_ptin": FieldCoord(
        page=0, x=516.4, y=92.6, width=85, alignment="left", font_size=8
    ),
    "preparer_self_employed": FieldCoord(
        page=0, x=484.3, y=102.0, width=10, alignment="left", font_size=9
    ),
    "firm_name": FieldCoord(
        page=0, x=140.3, y=81.7, width=310, alignment="left", font_size=8
    ),
    "firm_ein": FieldCoord(
        page=0, x=516.3, y=82.7, width=100, alignment="left", font_size=8
    ),
    # Firm address — street on one line, city/state/zip on the line below
    "firm_street": FieldCoord(
        page=0, x=140.3, y=67.3, width=160, alignment="left", font_size=8
    ),
    "firm_city": FieldCoord(
        page=0, x=140.0, y=61.3, width=90, alignment="left", font_size=8
    ),
    "firm_state": FieldCoord(
        page=0, x=377.0, y=60.3, width=25, alignment="left", font_size=8
    ),
    "firm_zip": FieldCoord(
        page=0, x=516.0, y=62.3, width=70, alignment="left", font_size=8
    ),
    "firm_phone": FieldCoord(
        page=0, x=516.0, y=71.0, width=100, alignment="left", font_size=8
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
    # y adjusted +4pt (was −9, now net −5 from coord tool)
    "1a": FieldCoord(page=0, x=130.7, y=544.0, width=85),
    # 1b returns/allowances (sub-column)
    # x = coord_tool 397.6 − width 75 = 322.6 (right edge renders at 397.6)
    "1b": FieldCoord(page=0, x=322.6, y=544.0, width=75),
    # 1c–6: main column.  coord_tool right edge = 578.3, width 113
    # x = 578.3 − 113 = 465.3
    "1c": FieldCoord(page=0, x=465.3, y=544.7, width=113),
    "2": FieldCoord(page=0, x=465.3, y=533.0, width=113),
    "3": FieldCoord(page=0, x=465.3, y=521.3, width=113),
    "4": FieldCoord(page=0, x=465.3, y=509.7, width=113),
    "5": FieldCoord(page=0, x=465.3, y=498.0, width=113),
    "6": FieldCoord(page=0, x=465.3, y=489.0, width=113),
}

# ---------------------------------------------------------------------------
# Page 0 — Deductions (lines 7 through 21)
# All in main amount column, ~10.9pt vertical spacing.
# ---------------------------------------------------------------------------
PAGE1_DEDUCTIONS: dict[str, FieldCoord] = {
    # All main column: coord_tool right edge 578.3 − width 113 = 465.3
    # y adjusted +4pt (was −9, now net −5 from coord tool)
    "7": FieldCoord(page=0, x=465.3, y=477.3, width=113),
    "8": FieldCoord(page=0, x=465.3, y=465.7, width=113),
    "9": FieldCoord(page=0, x=465.3, y=455.3, width=113),
    "10": FieldCoord(page=0, x=465.3, y=444.3, width=113),
    "11": FieldCoord(page=0, x=465.3, y=432.7, width=113),
    "12": FieldCoord(page=0, x=465.3, y=423.0, width=113),
    "13": FieldCoord(page=0, x=465.3, y=412.0, width=113),
    "14": FieldCoord(page=0, x=465.3, y=401.0, width=113),
    "15": FieldCoord(page=0, x=465.3, y=389.3, width=113),
    "16": FieldCoord(page=0, x=465.3, y=377.7, width=113),
    "17": FieldCoord(page=0, x=465.3, y=367.0, width=113),
    "18": FieldCoord(page=0, x=465.3, y=357.3, width=113),
    "19": FieldCoord(page=0, x=465.3, y=345.0, width=113),
    "20": FieldCoord(page=0, x=465.3, y=334.0, width=113),
    "21": FieldCoord(page=0, x=465.3, y=323.7, width=113),
}

# ---------------------------------------------------------------------------
# Page 0 — Tax and Payments (lines 22 through 28)
# ---------------------------------------------------------------------------
PAGE1_TAX: dict[str, FieldCoord] = {
    # Main column: coord_tool 578.3 − 113 = 465.3
    # y adjusted +4pt (was −9, now net −5 from coord tool)
    "22": FieldCoord(page=0, x=465.3, y=313.3, width=113),
    # Sub-column: coord_tool 445.0 − 113 = 332.0
    "23a": FieldCoord(page=0, x=332.0, y=301.7, width=113),
    "23b": FieldCoord(page=0, x=332.0, y=291.4, width=113),
    # 23c total (main column)
    "23c": FieldCoord(page=0, x=465.3, y=281.0, width=113),
    # Line 24 sub-items (sub-column: coord_tool 445.0 − 113 = 332.0)
    "24": FieldCoord(page=0, x=332.0, y=259.7, width=113),
    "24b": FieldCoord(page=0, x=332.0, y=248.0, width=113),
    "24c": FieldCoord(page=0, x=332.0, y=236.0, width=113),
    # 24d total (main column)
    "24d": FieldCoord(page=0, x=465.3, y=224.0, width=113),
    # 24z other (sub-column)
    "24z": FieldCoord(page=0, x=332.0, y=213.0, width=113),
    # Amount owed / Overpayment (main column)
    "25": FieldCoord(page=0, x=465.3, y=203.3, width=113),
    "26": FieldCoord(page=0, x=465.3, y=191.0, width=113),
    "27": FieldCoord(page=0, x=465.3, y=180.7, width=113),
    "28": FieldCoord(page=0, x=465.3, y=170.3, width=113),
}

# ---------------------------------------------------------------------------
# Schedule K — Shareholders' Pro Rata Share Items
# Lines 1-16 on page 2 (bottom half), lines 17-18 on page 3 (top)
# Amount column: right-aligned, right edge at x=588
# ---------------------------------------------------------------------------
SCHEDULE_K: dict[str, FieldCoord] = {
    # Page 2 — Schedule K lines 1 through 16
    # Right edge shifted +28 to match page 1 alignment (550 → 578)
    # x = 578 − 113 = 465
    "K1": FieldCoord(page=2, x=465, y=560, width=113),
    "K2": FieldCoord(page=2, x=465, y=545, width=113),
    "K3c": FieldCoord(page=2, x=465, y=516, width=113),
    "K4": FieldCoord(page=2, x=465, y=500, width=113),
    "K5a": FieldCoord(page=2, x=465, y=488, width=113),
    "K6": FieldCoord(page=2, x=465, y=468, width=113),
    "K7": FieldCoord(page=2, x=465, y=454, width=113),
    "K8a": FieldCoord(page=2, x=465, y=440, width=113),
    "K9": FieldCoord(page=2, x=465, y=412, width=113),
    "K10": FieldCoord(page=2, x=465, y=397, width=113),
    "K11": FieldCoord(page=2, x=465, y=384, width=113),
    "K12a": FieldCoord(page=2, x=465, y=372, width=113),
    "K12b": FieldCoord(page=2, x=465, y=361, width=113),
    "K12c": FieldCoord(page=2, x=465, y=348, width=113),
    "K12d": FieldCoord(page=2, x=466, y=337, width=113),
    "K13a": FieldCoord(page=2, x=465, y=316, width=113),
    "K13b": FieldCoord(page=2, x=465, y=302, width=113),
    "K13c": FieldCoord(page=2, x=465, y=288, width=113),
    "K13d": FieldCoord(page=2, x=465, y=278, width=113),
    "K15a": FieldCoord(page=2, x=465, y=192, width=113),
    "K15b": FieldCoord(page=2, x=465, y=179, width=113),
    "K15c": FieldCoord(page=2, x=465, y=167, width=113),
    "K15d": FieldCoord(page=2, x=465, y=154, width=113),
    "K16a": FieldCoord(page=2, x=465, y=123, width=113),
    "K16b": FieldCoord(page=2, x=465, y=110, width=113),
    "K16c": FieldCoord(page=2, x=465, y=99, width=113),
    "K16d": FieldCoord(page=2, x=465, y=87, width=113),
    # Page 3 — Schedule K continued (lines 17-18)
    # x = 578 − 120 = 458
    "K17a": FieldCoord(page=3, x=458, y=707, width=120),
    "K17b": FieldCoord(page=3, x=458, y=694, width=120),
    "K17c": FieldCoord(page=3, x=458, y=683, width=120),
    "K18": FieldCoord(page=3, x=458, y=639, width=120),
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
    # All columns shifted +28 right to match page 1 alignment.
    #   (a) col: x = 261,  right edge 336
    #   (b) col: x = 343,  right edge 418
    #   (c) col: x = 423,  right edge 498
    #   (d) col: x = 503,  right edge 578
    #
    # Beginning of year — column (b) for simple lines, (a) for gross amounts
    "L1a": FieldCoord(page=3, x=343, y=599, width=75),   # Cash — col (b)
    "L2a": FieldCoord(page=3, x=261, y=587, width=75),   # Trade notes — col (a)
    "L2b": FieldCoord(page=3, x=343, y=575, width=75),   # Less allowance — col (b)
    "L3a": FieldCoord(page=3, x=343, y=561, width=75),   # Inventories — col (b)
    "L4a": FieldCoord(page=3, x=343, y=548, width=75),   # U.S. govt obligations
    "L5a": FieldCoord(page=3, x=343, y=537, width=75),   # Tax-exempt securities
    "L6a": FieldCoord(page=3, x=343, y=527, width=75),   # Other current assets
    "L7a": FieldCoord(page=3, x=343, y=515, width=75),   # Loans to shareholders
    "L8a": FieldCoord(page=3, x=343, y=501, width=75),   # Mortgage/RE loans
    "L9a": FieldCoord(page=3, x=343, y=489, width=75),   # Other investments
    "L10a": FieldCoord(page=3, x=261, y=480, width=75),  # Buildings — col (a)
    "L10b": FieldCoord(page=3, x=343, y=469, width=75),  # Less depreciation — col (b)
    "L11a": FieldCoord(page=3, x=261, y=457, width=75),  # Depletable — col (a)
    "L11b": FieldCoord(page=3, x=343, y=446, width=75),  # Less depletion — col (b)
    "L12a": FieldCoord(page=3, x=343, y=433, width=75),  # Land
    "L13a_gross": FieldCoord(page=3, x=261, y=422, width=75),  # Intangibles — col (a)
    "L13b": FieldCoord(page=3, x=343, y=412, width=75),  # Less amortization — col (b)
    "L14a": FieldCoord(page=3, x=343, y=400, width=75),  # Other assets
    "L15a": FieldCoord(page=3, x=343, y=386, width=75),  # Total assets
    "L16a": FieldCoord(page=3, x=343, y=364, width=75),  # Accounts payable
    "L17a": FieldCoord(page=3, x=343, y=352, width=75),  # Mortgages <1yr
    "L18a": FieldCoord(page=3, x=343, y=339, width=75),  # Other current liabilities
    "L19a": FieldCoord(page=3, x=343, y=327, width=75),  # Loans from shareholders
    "L20a": FieldCoord(page=3, x=343, y=315, width=75),  # Mortgages 1yr+
    "L21a": FieldCoord(page=3, x=343, y=302, width=75),  # Other liabilities
    "L22a": FieldCoord(page=3, x=343, y=291, width=75),  # Capital stock
    "L23a": FieldCoord(page=3, x=343, y=280, width=75),  # Additional paid-in capital
    "L24a": FieldCoord(page=3, x=343, y=268, width=75),  # Retained earnings
    "L25a": FieldCoord(page=3, x=343, y=258, width=75),  # Adjustments to equity
    "L26a": FieldCoord(page=3, x=344, y=244, width=75),  # Less treasury stock
    "L27a": FieldCoord(page=3, x=343, y=231, width=75),  # Total liabilities + equity
    # End of year — column (d) for simple lines, (c) for gross amounts
    "L1d": FieldCoord(page=3, x=503, y=600, width=75),
    "L2c": FieldCoord(page=3, x=423, y=587, width=75),   # Trade notes — col (c)
    "L2d": FieldCoord(page=3, x=503, y=574, width=75),   # Less allowance — col (d)
    "L3d": FieldCoord(page=3, x=503, y=562, width=75),
    "L4d": FieldCoord(page=3, x=503, y=550, width=75),
    "L5d": FieldCoord(page=3, x=503, y=538, width=75),
    "L6d": FieldCoord(page=3, x=503, y=528, width=75),
    "L7d": FieldCoord(page=3, x=503, y=517, width=75),
    "L8d": FieldCoord(page=3, x=503, y=504, width=75),
    "L9d": FieldCoord(page=3, x=503, y=491, width=75),
    "L10c": FieldCoord(page=3, x=423, y=480, width=75),  # Buildings — col (c)
    "L10d": FieldCoord(page=3, x=503, y=471, width=75),  # Less depreciation — col (d)
    "L11c": FieldCoord(page=3, x=423, y=457, width=75),  # Depletable — col (c)
    "L11d": FieldCoord(page=3, x=503, y=445, width=75),  # Less depletion — col (d)
    "L12d": FieldCoord(page=3, x=503, y=433, width=75),
    "L13c": FieldCoord(page=3, x=423, y=422, width=75),  # Intangibles — col (c)
    "L13d": FieldCoord(page=3, x=503, y=410, width=75),  # Less amortization — col (d)
    "L14d": FieldCoord(page=3, x=503, y=397, width=75),
    "L15d": FieldCoord(page=3, x=503, y=385, width=75),
    "L16d": FieldCoord(page=3, x=503, y=364, width=75),
    "L17d": FieldCoord(page=3, x=503, y=350, width=75),
    "L18d": FieldCoord(page=3, x=503, y=339, width=75),
    "L19d": FieldCoord(page=3, x=503, y=326, width=75),
    "L20d": FieldCoord(page=3, x=503, y=316, width=75),
    "L21d": FieldCoord(page=3, x=503, y=304, width=75),
    "L22d": FieldCoord(page=3, x=503, y=293, width=75),
    "L23d": FieldCoord(page=3, x=503, y=281, width=75),
    "L24d": FieldCoord(page=3, x=503, y=270, width=75),
    "L25d": FieldCoord(page=3, x=503, y=257, width=75),
    "L26d": FieldCoord(page=3, x=503, y=246, width=75),
    "L27d": FieldCoord(page=3, x=503, y=232, width=75),
}

# ---------------------------------------------------------------------------
# Schedule M-1 — Reconciliation of Income (page 4, top)
#
# Two-column layout:
#   Left column (lines 1-4): additions.  Amount right edge ~x=225
#   Right column (lines 5-8): subtractions.  Amount right edge ~x=588
# ---------------------------------------------------------------------------
SCHEDULE_M1: dict[str, FieldCoord] = {
    # All fields shifted +8 right to better match page 1 column alignment
    # Left column: right edge 290 → 298
    "M1_1": FieldCoord(page=4, x=228, y=711, width=70),
    "M1_2": FieldCoord(page=4, x=228, y=664, width=70),
    "M1_3a": FieldCoord(page=4, x=101, y=616, width=110),
    "M1_3b": FieldCoord(page=4, x=151, y=592, width=60),
    "M1_4": FieldCoord(page=4, x=228, y=568, width=70),
    # Right column: right edge 570 → 578 (matches page 1)
    "M1_5": FieldCoord(page=4, x=490, y=665, width=88),
    "M1_6": FieldCoord(page=4, x=490, y=604, width=88),
    "M1_7": FieldCoord(page=4, x=490, y=589, width=88),
    "M1_8": FieldCoord(page=4, x=490, y=552, width=88),
}

# ---------------------------------------------------------------------------
# Schedule M-2 — Analysis of AAA, STUPIT, E&P, Other (page 4, bottom)
#
# Column (a) — Accumulated adjustments account.  Right edge ~x=307
# Lines 1-8 are vertically stacked with ~12pt spacing.
# ---------------------------------------------------------------------------
SCHEDULE_M2: dict[str, FieldCoord] = {
    # All fields shifted +8 right to better match page 1 column alignment
    # Right edge 290 → 298
    "M2_1": FieldCoord(page=4, x=213, y=481, width=85),
    "M2_2": FieldCoord(page=4, x=215, y=469, width=85),
    "M2_3": FieldCoord(page=4, x=213, y=456, width=85),
    "M2_4": FieldCoord(page=4, x=213, y=443, width=85),
    "M2_5": FieldCoord(page=4, x=213, y=433, width=85),
    "M2_6": FieldCoord(page=4, x=213, y=421, width=85),
    "M2_7": FieldCoord(page=4, x=213, y=410, width=85),
    "M2_8": FieldCoord(page=4, x=213, y=388, width=85),
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
    # y shifted −2pt from original positions
    # Line 3
    "B3_yes": FieldCoord(page=1, x=533, y=661, width=10, alignment="left", font_size=9),
    "B3_no": FieldCoord(page=1, x=555, y=661, width=10, alignment="left", font_size=9),
    # Line 4a
    "B4a_yes": FieldCoord(page=1, x=533, y=610, width=10, alignment="left", font_size=9),
    "B4a_no": FieldCoord(page=1, x=555, y=610, width=10, alignment="left", font_size=9),
    # Line 4b
    "B4b_yes": FieldCoord(page=1, x=533, y=494, width=10, alignment="left", font_size=9),
    "B4b_no": FieldCoord(page=1, x=555, y=494, width=10, alignment="left", font_size=9),
    # Line 5a
    "B5a_yes": FieldCoord(page=1, x=533, y=403, width=10, alignment="left", font_size=9),
    "B5a_no": FieldCoord(page=1, x=555, y=403, width=10, alignment="left", font_size=9),
    # Line 5b
    "B5b_yes": FieldCoord(page=1, x=533, y=357, width=10, alignment="left", font_size=9),
    "B5b_no": FieldCoord(page=1, x=555, y=357, width=10, alignment="left", font_size=9),
    # Line 6
    "B6_yes": FieldCoord(page=1, x=533, y=301, width=10, alignment="left", font_size=9),
    "B6_no": FieldCoord(page=1, x=555, y=301, width=10, alignment="left", font_size=9),
    # Line 7 — single checkbox ("Check this box if …"), no Yes/No pair
    "B7_yes": FieldCoord(page=1, x=533, y=285, width=10, alignment="left", font_size=9),
    # Line 8 — currency amount (net unrealized built-in gain)
    "B8": FieldCoord(page=1, x=555, y=243, width=50, alignment="right", font_size=9),
    # Line 9
    "B9_yes": FieldCoord(page=1, x=533, y=191, width=10, alignment="left", font_size=9),
    "B9_no": FieldCoord(page=1, x=555, y=191, width=10, alignment="left", font_size=9),
    # Line 10
    "B10_yes": FieldCoord(page=1, x=533, y=179, width=10, alignment="left", font_size=9),
    "B10_no": FieldCoord(page=1, x=555, y=179, width=10, alignment="left", font_size=9),
    # Line 11
    "B11_yes": FieldCoord(page=1, x=533, y=111, width=10, alignment="left", font_size=9),
    "B11_no": FieldCoord(page=1, x=555, y=111, width=10, alignment="left", font_size=9),

    # --- Page 2 (Schedule B continued) ---
    # Line 12
    "B12_yes": FieldCoord(page=2, x=532, y=701, width=10, alignment="left", font_size=9),
    "B12_no": FieldCoord(page=2, x=554, y=701, width=10, alignment="left", font_size=9),
    # Line 13
    "B13_yes": FieldCoord(page=2, x=532, y=676, width=10, alignment="left", font_size=9),
    "B13_no": FieldCoord(page=2, x=554, y=676, width=10, alignment="left", font_size=9),
    # Line 14a
    "B14a_yes": FieldCoord(page=2, x=532, y=664, width=10, alignment="left", font_size=9),
    "B14a_no": FieldCoord(page=2, x=554, y=664, width=10, alignment="left", font_size=9),
    # Line 14b
    "B14b_yes": FieldCoord(page=2, x=532, y=653, width=10, alignment="left", font_size=9),
    "B14b_no": FieldCoord(page=2, x=554, y=653, width=10, alignment="left", font_size=9),
    # Line 15
    "B15_yes": FieldCoord(page=2, x=532, y=641, width=10, alignment="left", font_size=9),
    "B15_no": FieldCoord(page=2, x=554, y=641, width=10, alignment="left", font_size=9),
    # Line 16
    "B16_yes": FieldCoord(page=2, x=532, y=607, width=10, alignment="left", font_size=9),
    "B16_no": FieldCoord(page=2, x=554, y=607, width=10, alignment="left", font_size=9),
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
