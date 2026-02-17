"""
Field coordinate mappings for Schedule K-1 (Form 1120-S) — 2025 official print version.

Coordinates are in PDF points (1 point = 1/72 inch).
Origin (0, 0) is the bottom-left corner of the page.
Standard US letter size: 612 x 792 points.

PDF structure (1 page):
    Left half (x 36–309): Part I (Corporation info) + Part II (Shareholder info)
    Right half (x 309–576): Part III (Shareholder's share of items)
        Left column (x 309–449): Lines 1–12
        Right column (x 449–576): Lines 13–17

Lines 10, 12, 13, 15, 16, 17 have multi-row code+amount areas.
For K-1 generation, we fill the first entry in each coded area.

Coordinates calibrated via pdfplumber extraction from the official 2025 PDF.
"""

from .f1120s import FieldCoord

# ---------------------------------------------------------------------------
# Part I — Corporation Information
# ---------------------------------------------------------------------------
K1_HEADER: dict[str, FieldCoord] = {
    # A — Corporation's employer identification number
    "corp_ein": FieldCoord(
        page=0, x=55, y=605, width=200, alignment="left", font_size=10
    ),
    # B — Corporation's name
    "corp_name": FieldCoord(
        page=0, x=55, y=580, width=240, alignment="left", font_size=9
    ),
    # B — Corporation's address (street)
    "corp_address": FieldCoord(
        page=0, x=55, y=568, width=240, alignment="left", font_size=9
    ),
    # B — Corporation's city, state, ZIP
    "corp_city_state_zip": FieldCoord(
        page=0, x=55, y=556, width=240, alignment="left", font_size=9
    ),
    # C — IRS Center where corporation filed return
    "irs_center": FieldCoord(
        page=0, x=55, y=510, width=200, alignment="left", font_size=9
    ),
    # D — Corporation's total number of shares, beginning
    "corp_shares_boy": FieldCoord(
        page=0, x=210, y=488, width=90, alignment="right", font_size=9
    ),
    # D — Corporation's total number of shares, end
    "corp_shares_eoy": FieldCoord(
        page=0, x=210, y=476, width=90, alignment="right", font_size=9
    ),
    # Tax year beginning
    "tax_year_begin": FieldCoord(
        page=0, x=100, y=692, width=50, alignment="left", font_size=8
    ),
    # Tax year ending
    "tax_year_end": FieldCoord(
        page=0, x=225, y=692, width=50, alignment="left", font_size=8
    ),
    # E — Shareholder's identifying number (SSN/TIN)
    "sh_ssn": FieldCoord(
        page=0, x=55, y=413, width=200, alignment="left", font_size=10
    ),
    # F1 — Shareholder's name
    "sh_name": FieldCoord(
        page=0, x=55, y=389, width=240, alignment="left", font_size=9
    ),
    # F1 — Shareholder's address (street)
    "sh_address": FieldCoord(
        page=0, x=55, y=377, width=240, alignment="left", font_size=9
    ),
    # F1 — Shareholder's city, state, ZIP
    "sh_city_state_zip": FieldCoord(
        page=0, x=55, y=365, width=240, alignment="left", font_size=9
    ),
    # G — Current year allocation percentage
    "sh_ownership_pct": FieldCoord(
        page=0, x=250, y=260, width=40, alignment="right", font_size=9
    ),
    # H — Shareholder's number of shares, beginning
    "sh_shares_boy": FieldCoord(
        page=0, x=210, y=224, width=90, alignment="right", font_size=9
    ),
    # H — Shareholder's number of shares, end
    "sh_shares_eoy": FieldCoord(
        page=0, x=210, y=212, width=90, alignment="right", font_size=9
    ),
}

# ---------------------------------------------------------------------------
# Part III — Shareholder's Share of Current Year Income, Deductions, etc.
#
# Left column (lines 1–12): amounts right-aligned at x=445
# Right column (lines 13–17): code+amount in sub-areas
# ---------------------------------------------------------------------------
K1_FIELD_MAP: dict[str, FieldCoord] = {
    # ---- Left column: Income ----
    # Line 1: Ordinary business income (loss)
    "1": FieldCoord(page=0, x=370, y=717, width=75, alignment="right", font_size=9),
    # Line 2: Net rental real estate income (loss)
    "2": FieldCoord(page=0, x=370, y=693, width=75, alignment="right", font_size=9),
    # Line 3: Other net rental income (loss)
    "3": FieldCoord(page=0, x=370, y=669, width=75, alignment="right", font_size=9),
    # Line 4: Interest income
    "4": FieldCoord(page=0, x=370, y=645, width=75, alignment="right", font_size=9),
    # Line 5a: Ordinary dividends
    "5a": FieldCoord(page=0, x=370, y=621, width=75, alignment="right", font_size=9),
    # Line 5b: Qualified dividends
    "5b": FieldCoord(page=0, x=370, y=597, width=75, alignment="right", font_size=9),
    # Line 6: Royalties
    "6": FieldCoord(page=0, x=370, y=573, width=75, alignment="right", font_size=9),
    # Line 7: Net short-term capital gain (loss)
    "7": FieldCoord(page=0, x=370, y=549, width=75, alignment="right", font_size=9),
    # Line 8a: Net long-term capital gain (loss)
    "8a": FieldCoord(page=0, x=370, y=525, width=75, alignment="right", font_size=9),
    # Line 8b: Collectibles (28%) gain (loss)
    "8b": FieldCoord(page=0, x=370, y=501, width=75, alignment="right", font_size=9),
    # Line 8c: Unrecaptured section 1250 gain
    "8c": FieldCoord(page=0, x=370, y=477, width=75, alignment="right", font_size=9),
    # Line 9: Net section 1231 gain (loss)
    "9": FieldCoord(page=0, x=370, y=453, width=75, alignment="right", font_size=9),

    # ---- Left column: Other income (line 10) — code + amount area ----
    # First entry in the code+amount area below line 10
    "10_code": FieldCoord(page=0, x=320, y=410, width=20, alignment="left", font_size=8),
    "10": FieldCoord(page=0, x=370, y=410, width=75, alignment="right", font_size=9),

    # ---- Left column: Deductions ----
    # Line 11: Section 179 deduction
    "11": FieldCoord(page=0, x=370, y=309, width=75, alignment="right", font_size=9),
    # Line 12: Other deductions — code + amount area
    "12_code": FieldCoord(page=0, x=320, y=268, width=20, alignment="left", font_size=8),
    "12": FieldCoord(page=0, x=370, y=268, width=75, alignment="right", font_size=9),

    # ---- Right column: Credits (line 13) — code + amount area ----
    "13_code": FieldCoord(page=0, x=458, y=700, width=20, alignment="left", font_size=8),
    "13": FieldCoord(page=0, x=500, y=700, width=70, alignment="right", font_size=9),

    # ---- Right column: AMT items (line 15) — code + amount area ----
    "15_code": FieldCoord(page=0, x=458, y=556, width=20, alignment="left", font_size=8),
    "15": FieldCoord(page=0, x=500, y=556, width=70, alignment="right", font_size=9),

    # ---- Right column: Items affecting shareholder basis (line 16) ----
    # These have lettered sub-codes: A through D commonly used
    "16_code_1": FieldCoord(page=0, x=458, y=436, width=20, alignment="left", font_size=8),
    "16_amt_1": FieldCoord(page=0, x=500, y=436, width=70, alignment="right", font_size=9),
    "16_code_2": FieldCoord(page=0, x=458, y=424, width=20, alignment="left", font_size=8),
    "16_amt_2": FieldCoord(page=0, x=500, y=424, width=70, alignment="right", font_size=9),
    "16_code_3": FieldCoord(page=0, x=458, y=412, width=20, alignment="left", font_size=8),
    "16_amt_3": FieldCoord(page=0, x=500, y=412, width=70, alignment="right", font_size=9),
    "16_code_4": FieldCoord(page=0, x=458, y=400, width=20, alignment="left", font_size=8),
    "16_amt_4": FieldCoord(page=0, x=500, y=400, width=70, alignment="right", font_size=9),

    # ---- Right column: Other information (line 17) — code + amount area ----
    "17_code_1": FieldCoord(page=0, x=458, y=316, width=20, alignment="left", font_size=8),
    "17_amt_1": FieldCoord(page=0, x=500, y=316, width=70, alignment="right", font_size=9),
    "17_code_2": FieldCoord(page=0, x=458, y=304, width=20, alignment="left", font_size=8),
    "17_amt_2": FieldCoord(page=0, x=500, y=304, width=70, alignment="right", font_size=9),
}
