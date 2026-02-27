"""
Field coordinate mappings for IRS Form 1065 (U.S. Return of Partnership Income).

Coordinates are in PDF points (1 point = 1/72 inch).
Origin (0, 0) is the bottom-left corner of each page.
Standard US letter size: 612 x 792 points.

Each entry maps a form line_number to:
    (page, x, y, width, alignment, font_size)

CALIBRATION NOTE: These coordinates are approximate starting points
based on the standard 2024/2025 Form 1065 layout. After downloading
the actual IRS PDF via update_irs_forms.py, fine-tune coordinates by
rendering a test PDF and comparing field positions.

To calibrate:
    1. Render a return with known values.
    2. Open the generated PDF alongside the blank IRS form.
    3. Adjust x/y values here until fields align with the IRS boxes.
"""

from .f1120s import FieldCoord  # Reuse the same dataclass

# ---------------------------------------------------------------------------
# Page 1 — Header / Entity Information
# ---------------------------------------------------------------------------
HEADER_FIELDS: dict[str, FieldCoord] = {
    "entity_name": FieldCoord(page=0, x=140, y=672, width=280, alignment="left"),
    "address_street": FieldCoord(page=0, x=140, y=650, width=280, alignment="left"),
    "address_city_state_zip": FieldCoord(
        page=0, x=140, y=628, width=280, alignment="left"
    ),
    "ein": FieldCoord(page=0, x=480, y=672, width=100, alignment="left"),
    "date_business_started": FieldCoord(
        page=0, x=480, y=650, width=100, alignment="left"
    ),
    "tax_year_begin": FieldCoord(
        page=0, x=145, y=737, width=80, alignment="left", font_size=8
    ),
    "tax_year_end": FieldCoord(
        page=0, x=310, y=737, width=80, alignment="left", font_size=8
    ),
    "principal_business_activity": FieldCoord(
        page=0, x=140, y=606, width=200, alignment="left", font_size=9
    ),
    "business_code": FieldCoord(
        page=0, x=480, y=606, width=80, alignment="left", font_size=9
    ),
    # ----- Page 0: Paid Preparer Use Only (bottom of first page) -----
    "preparer_name": FieldCoord(
        page=0, x=90, y=70, width=150, alignment="left", font_size=8
    ),
    "preparer_date": FieldCoord(
        page=0, x=393, y=70, width=60, alignment="left", font_size=8
    ),
    "preparer_ptin": FieldCoord(
        page=0, x=525, y=70, width=50, alignment="left", font_size=8
    ),
    "preparer_self_employed": FieldCoord(
        page=0, x=514, y=65, width=10, alignment="left", font_size=9
    ),
    "firm_name": FieldCoord(
        page=0, x=132, y=50, width=310, alignment="left", font_size=8
    ),
    "firm_ein": FieldCoord(
        page=0, x=490, y=50, width=85, alignment="left", font_size=8
    ),
    "firm_address": FieldCoord(
        page=0, x=140, y=38, width=310, alignment="left", font_size=8
    ),
    "firm_phone": FieldCoord(
        page=0, x=500, y=38, width=75, alignment="left", font_size=8
    ),
}

# ---------------------------------------------------------------------------
# Page 1 — Income (lines 1a through 8)
# ---------------------------------------------------------------------------
PAGE1_INCOME: dict[str, FieldCoord] = {
    "1a": FieldCoord(page=0, x=440, y=510, width=120),
    "1b": FieldCoord(page=0, x=440, y=498, width=120),
    "1c": FieldCoord(page=0, x=500, y=486, width=70),
    "2": FieldCoord(page=0, x=500, y=474, width=70),
    "3": FieldCoord(page=0, x=500, y=462, width=70),
    "4": FieldCoord(page=0, x=500, y=450, width=70),
    "5": FieldCoord(page=0, x=500, y=438, width=70),
    "6": FieldCoord(page=0, x=500, y=426, width=70),
    "7": FieldCoord(page=0, x=500, y=414, width=70),
    "8": FieldCoord(page=0, x=500, y=402, width=70),
}

# ---------------------------------------------------------------------------
# Page 1 — Deductions (lines 9 through 22)
# ---------------------------------------------------------------------------
PAGE1_DEDUCTIONS: dict[str, FieldCoord] = {
    "9": FieldCoord(page=0, x=500, y=378, width=70),
    "10": FieldCoord(page=0, x=500, y=366, width=70),
    "11": FieldCoord(page=0, x=500, y=354, width=70),
    "12": FieldCoord(page=0, x=500, y=342, width=70),
    "13": FieldCoord(page=0, x=500, y=330, width=70),
    "14": FieldCoord(page=0, x=500, y=318, width=70),
    "15": FieldCoord(page=0, x=500, y=306, width=70),
    "16a": FieldCoord(page=0, x=500, y=294, width=70),
    "16b": FieldCoord(page=0, x=440, y=282, width=120),
    "16c": FieldCoord(page=0, x=500, y=270, width=70),
    "17": FieldCoord(page=0, x=500, y=258, width=70),
    "18": FieldCoord(page=0, x=500, y=246, width=70),
    "19": FieldCoord(page=0, x=500, y=234, width=70),
    "20": FieldCoord(page=0, x=500, y=222, width=70),
    "21": FieldCoord(page=0, x=500, y=210, width=70),
    "22": FieldCoord(page=0, x=500, y=198, width=70),
}

# ---------------------------------------------------------------------------
# Page 1 — Analysis / bottom section
# ---------------------------------------------------------------------------
PAGE1_ANALYSIS: dict[str, FieldCoord] = {
    # Ordinary business income (loss) from line 22
    # Analysis of Net Income (Loss) — lines at bottom of page 1
    "analysis_a_i": FieldCoord(page=0, x=400, y=140, width=70),
    "analysis_a_ii": FieldCoord(page=0, x=470, y=140, width=70),
    "analysis_b_i": FieldCoord(page=0, x=400, y=128, width=70),
    "analysis_b_ii": FieldCoord(page=0, x=470, y=128, width=70),
}

# ---------------------------------------------------------------------------
# Schedule A — Cost of Goods Sold (page 2)
# ---------------------------------------------------------------------------
SCHEDULE_A: dict[str, FieldCoord] = {
    "A1": FieldCoord(page=1, x=500, y=600, width=70),
    "A2": FieldCoord(page=1, x=500, y=588, width=70),
    "A3": FieldCoord(page=1, x=500, y=576, width=70),
    "A4": FieldCoord(page=1, x=500, y=564, width=70),
    "A5": FieldCoord(page=1, x=500, y=552, width=70),
    "A6": FieldCoord(page=1, x=500, y=540, width=70),
    "A7": FieldCoord(page=1, x=500, y=528, width=70),
    "A8": FieldCoord(page=1, x=500, y=516, width=70),
}

# ---------------------------------------------------------------------------
# Schedule K — Partners' Distributive Share Items (pages 3-4)
#
# Form 1065 Schedule K is larger than 1120-S — income, deductions,
# self-employment, credits, foreign transactions, AMT, other info.
# ---------------------------------------------------------------------------
SCHEDULE_K: dict[str, FieldCoord] = {
    # Income (Loss)
    "K1": FieldCoord(page=3, x=500, y=670, width=70),
    "K2": FieldCoord(page=3, x=500, y=654, width=70),
    "K3a": FieldCoord(page=3, x=500, y=638, width=70),
    "K3b": FieldCoord(page=3, x=500, y=622, width=70),
    "K3c": FieldCoord(page=3, x=500, y=606, width=70),
    "K4": FieldCoord(page=3, x=500, y=590, width=70),
    "K5": FieldCoord(page=3, x=500, y=574, width=70),
    "K6a": FieldCoord(page=3, x=500, y=558, width=70),
    "K6b": FieldCoord(page=3, x=500, y=542, width=70),
    "K6c": FieldCoord(page=3, x=500, y=526, width=70),
    "K7": FieldCoord(page=3, x=500, y=510, width=70),
    "K8": FieldCoord(page=3, x=500, y=494, width=70),
    "K9a": FieldCoord(page=3, x=500, y=478, width=70),
    "K9b": FieldCoord(page=3, x=500, y=462, width=70),
    "K9c": FieldCoord(page=3, x=500, y=446, width=70),
    "K10": FieldCoord(page=3, x=500, y=430, width=70),
    "K11": FieldCoord(page=3, x=500, y=414, width=70),
    # Deductions
    "K12": FieldCoord(page=3, x=500, y=390, width=70),
    "K13a": FieldCoord(page=3, x=500, y=374, width=70),
    "K13b": FieldCoord(page=3, x=500, y=358, width=70),
    "K13c": FieldCoord(page=3, x=500, y=342, width=70),
    "K13d": FieldCoord(page=3, x=500, y=326, width=70),
    # Self-Employment
    "K14a": FieldCoord(page=3, x=500, y=302, width=70),
    "K14b": FieldCoord(page=3, x=500, y=286, width=70),
    "K14c": FieldCoord(page=3, x=500, y=270, width=70),
    # Credits
    "K15a": FieldCoord(page=3, x=500, y=246, width=70),
    "K15b": FieldCoord(page=3, x=500, y=230, width=70),
    "K15c": FieldCoord(page=3, x=500, y=214, width=70),
    "K15d": FieldCoord(page=3, x=500, y=198, width=70),
    "K15e": FieldCoord(page=3, x=500, y=182, width=70),
    "K15f": FieldCoord(page=3, x=500, y=166, width=70),
    # Page 4 of Schedule K — Foreign transactions, AMT, Other
    "K16a": FieldCoord(page=4, x=500, y=670, width=70),
    "K16b": FieldCoord(page=4, x=500, y=654, width=70),
    "K16c": FieldCoord(page=4, x=500, y=638, width=70),
    "K16d": FieldCoord(page=4, x=500, y=622, width=70),
    "K16e": FieldCoord(page=4, x=500, y=606, width=70),
    "K16f": FieldCoord(page=4, x=500, y=590, width=70),
    # AMT Items
    "K17a": FieldCoord(page=4, x=500, y=558, width=70),
    "K17b": FieldCoord(page=4, x=500, y=542, width=70),
    "K17c": FieldCoord(page=4, x=500, y=526, width=70),
    # Other information
    "K18a": FieldCoord(page=4, x=500, y=494, width=70),
    "K18b": FieldCoord(page=4, x=500, y=478, width=70),
    "K18c": FieldCoord(page=4, x=500, y=462, width=70),
    "K19a": FieldCoord(page=4, x=500, y=438, width=70),
    "K19b": FieldCoord(page=4, x=500, y=422, width=70),
    "K20a": FieldCoord(page=4, x=500, y=398, width=70),
    "K20b": FieldCoord(page=4, x=500, y=382, width=70),
    "K20c": FieldCoord(page=4, x=500, y=366, width=70),
}

# ---------------------------------------------------------------------------
# Schedule L — Balance Sheet per Books (page 5)
# Two columns: beginning of year (col b) and end of year (col d)
# ---------------------------------------------------------------------------
SCHEDULE_L: dict[str, FieldCoord] = {
    # Assets — Beginning of year
    "L1b": FieldCoord(page=4, x=200, y=300, width=80),
    "L2b": FieldCoord(page=4, x=200, y=284, width=80),
    "L3b": FieldCoord(page=4, x=200, y=268, width=80),
    "L4b": FieldCoord(page=4, x=200, y=252, width=80),
    "L5b": FieldCoord(page=4, x=200, y=236, width=80),
    "L6b": FieldCoord(page=4, x=200, y=220, width=80),
    "L7b": FieldCoord(page=4, x=200, y=204, width=80),
    "L8b": FieldCoord(page=4, x=200, y=188, width=80),
    "L9ab": FieldCoord(page=4, x=200, y=172, width=80),
    "L9bb": FieldCoord(page=4, x=280, y=172, width=80),
    "L10ab": FieldCoord(page=4, x=200, y=156, width=80),
    "L10bb": FieldCoord(page=4, x=280, y=156, width=80),
    "L11b": FieldCoord(page=4, x=200, y=140, width=80),
    "L12b": FieldCoord(page=4, x=200, y=124, width=80),
    "L13b": FieldCoord(page=4, x=200, y=108, width=80),
    "L14b": FieldCoord(page=4, x=200, y=92, width=80),
    # Assets — End of year
    "L1d": FieldCoord(page=4, x=440, y=300, width=80),
    "L2d": FieldCoord(page=4, x=440, y=284, width=80),
    "L3d": FieldCoord(page=4, x=440, y=268, width=80),
    "L4d": FieldCoord(page=4, x=440, y=252, width=80),
    "L5d": FieldCoord(page=4, x=440, y=236, width=80),
    "L6d": FieldCoord(page=4, x=440, y=220, width=80),
    "L7d": FieldCoord(page=4, x=440, y=204, width=80),
    "L8d": FieldCoord(page=4, x=440, y=188, width=80),
    "L9ad": FieldCoord(page=4, x=440, y=172, width=80),
    "L9bd": FieldCoord(page=4, x=520, y=172, width=80),
    "L10ad": FieldCoord(page=4, x=440, y=156, width=80),
    "L10bd": FieldCoord(page=4, x=520, y=156, width=80),
    "L11d": FieldCoord(page=4, x=440, y=140, width=80),
    "L12d": FieldCoord(page=4, x=440, y=124, width=80),
    "L13d": FieldCoord(page=4, x=440, y=108, width=80),
    "L14d": FieldCoord(page=4, x=440, y=92, width=80),
    # Liabilities & Capital — Beginning of year
    "L15b": FieldCoord(page=5, x=200, y=700, width=80),
    "L16b": FieldCoord(page=5, x=200, y=684, width=80),
    "L17b": FieldCoord(page=5, x=200, y=668, width=80),
    "L18b": FieldCoord(page=5, x=200, y=652, width=80),
    "L19b": FieldCoord(page=5, x=200, y=636, width=80),
    "L20b": FieldCoord(page=5, x=200, y=620, width=80),
    "L21b": FieldCoord(page=5, x=200, y=604, width=80),
    "L22b": FieldCoord(page=5, x=200, y=588, width=80),
    # Liabilities & Capital — End of year
    "L15d": FieldCoord(page=5, x=440, y=700, width=80),
    "L16d": FieldCoord(page=5, x=440, y=684, width=80),
    "L17d": FieldCoord(page=5, x=440, y=668, width=80),
    "L18d": FieldCoord(page=5, x=440, y=652, width=80),
    "L19d": FieldCoord(page=5, x=440, y=636, width=80),
    "L20d": FieldCoord(page=5, x=440, y=620, width=80),
    "L21d": FieldCoord(page=5, x=440, y=604, width=80),
    "L22d": FieldCoord(page=5, x=440, y=588, width=80),
}

# ---------------------------------------------------------------------------
# Schedule M-1 — Reconciliation of Income (Loss) (page 5)
# ---------------------------------------------------------------------------
SCHEDULE_M1: dict[str, FieldCoord] = {
    "M1_1": FieldCoord(page=5, x=250, y=540, width=80),
    "M1_2": FieldCoord(page=5, x=250, y=524, width=80),
    "M1_3a": FieldCoord(page=5, x=250, y=508, width=80),
    "M1_3b": FieldCoord(page=5, x=250, y=492, width=80),
    "M1_4": FieldCoord(page=5, x=250, y=476, width=80),
    "M1_5": FieldCoord(page=5, x=500, y=540, width=70),
    "M1_6": FieldCoord(page=5, x=500, y=524, width=70),
    "M1_7": FieldCoord(page=5, x=500, y=508, width=70),
    "M1_8": FieldCoord(page=5, x=500, y=492, width=70),
    "M1_9": FieldCoord(page=5, x=500, y=476, width=70),
}

# ---------------------------------------------------------------------------
# Schedule M-2 — Analysis of Partners' Capital Accounts (page 5)
# ---------------------------------------------------------------------------
SCHEDULE_M2: dict[str, FieldCoord] = {
    "M2_1": FieldCoord(page=5, x=250, y=430, width=80),
    "M2_2": FieldCoord(page=5, x=250, y=414, width=80),
    "M2_3a": FieldCoord(page=5, x=250, y=398, width=80),
    "M2_3b": FieldCoord(page=5, x=250, y=382, width=80),
    "M2_4": FieldCoord(page=5, x=250, y=366, width=80),
    "M2_5": FieldCoord(page=5, x=500, y=430, width=70),
    "M2_6a": FieldCoord(page=5, x=500, y=414, width=70),
    "M2_6b": FieldCoord(page=5, x=500, y=398, width=70),
    "M2_7": FieldCoord(page=5, x=500, y=382, width=70),
    "M2_8": FieldCoord(page=5, x=500, y=366, width=70),
    "M2_9": FieldCoord(page=5, x=500, y=350, width=70),
}

# ---------------------------------------------------------------------------
# Combined field map — used by the renderer
# ---------------------------------------------------------------------------
FIELD_MAP: dict[str, FieldCoord] = {
    **PAGE1_INCOME,
    **PAGE1_DEDUCTIONS,
    **PAGE1_ANALYSIS,
    **SCHEDULE_A,
    **SCHEDULE_K,
    **SCHEDULE_L,
    **SCHEDULE_M1,
    **SCHEDULE_M2,
}
