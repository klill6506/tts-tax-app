"""
Field coordinate mappings for IRS Form 1120 (U.S. Corporation Income Tax Return).

Coordinates are in PDF points (1 point = 1/72 inch).
Origin (0, 0) is the bottom-left corner of each page.
Standard US letter size: 612 x 792 points.

Each entry maps a form line_number to:
    (page, x, y, width, alignment, font_size)

CALIBRATION NOTE: These coordinates are approximate starting points
based on the standard 2024/2025 Form 1120 layout. After downloading
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
    "date_incorporated": FieldCoord(
        page=0, x=480, y=650, width=100, alignment="left"
    ),
    "tax_year_begin": FieldCoord(
        page=0, x=145, y=737, width=80, alignment="left", font_size=8
    ),
    "tax_year_end": FieldCoord(
        page=0, x=310, y=737, width=80, alignment="left", font_size=8
    ),
}

# ---------------------------------------------------------------------------
# Page 1 — Income (lines 1a through 11)
# ---------------------------------------------------------------------------
PAGE1_INCOME: dict[str, FieldCoord] = {
    "1a": FieldCoord(page=0, x=440, y=520, width=120),
    "1b": FieldCoord(page=0, x=440, y=508, width=120),
    "1c": FieldCoord(page=0, x=500, y=496, width=70),
    "2": FieldCoord(page=0, x=500, y=484, width=70),
    "3": FieldCoord(page=0, x=500, y=472, width=70),
    "4": FieldCoord(page=0, x=500, y=460, width=70),
    "5": FieldCoord(page=0, x=500, y=448, width=70),
    "6": FieldCoord(page=0, x=500, y=436, width=70),
    "7": FieldCoord(page=0, x=500, y=424, width=70),
    "8": FieldCoord(page=0, x=500, y=412, width=70),
    "9": FieldCoord(page=0, x=500, y=400, width=70),
    "10": FieldCoord(page=0, x=500, y=388, width=70),
    "11": FieldCoord(page=0, x=500, y=376, width=70),
}

# ---------------------------------------------------------------------------
# Page 1 — Deductions (lines 12 through 30)
# ---------------------------------------------------------------------------
PAGE1_DEDUCTIONS: dict[str, FieldCoord] = {
    "12": FieldCoord(page=0, x=500, y=352, width=70),
    "13": FieldCoord(page=0, x=500, y=340, width=70),
    "14": FieldCoord(page=0, x=500, y=328, width=70),
    "15": FieldCoord(page=0, x=500, y=316, width=70),
    "16": FieldCoord(page=0, x=500, y=304, width=70),
    "17": FieldCoord(page=0, x=500, y=292, width=70),
    "18": FieldCoord(page=0, x=500, y=280, width=70),
    "19": FieldCoord(page=0, x=500, y=268, width=70),
    "20": FieldCoord(page=0, x=500, y=256, width=70),
    "21": FieldCoord(page=0, x=500, y=244, width=70),
    "22": FieldCoord(page=0, x=500, y=232, width=70),
    "23": FieldCoord(page=0, x=500, y=220, width=70),
    "24": FieldCoord(page=0, x=500, y=208, width=70),
    "25": FieldCoord(page=0, x=500, y=196, width=70),
    "26": FieldCoord(page=0, x=500, y=184, width=70),
    "27": FieldCoord(page=0, x=500, y=172, width=70),
    "28": FieldCoord(page=0, x=500, y=160, width=70),
    "29a": FieldCoord(page=0, x=440, y=148, width=120),
    "29b": FieldCoord(page=0, x=440, y=136, width=120),
    "29c": FieldCoord(page=0, x=500, y=124, width=70),
    "30": FieldCoord(page=0, x=500, y=112, width=70),
}

# ---------------------------------------------------------------------------
# Page 1 — Tax, Refundable Credits, and Payments (lines 31-36)
# ---------------------------------------------------------------------------
PAGE1_TAX: dict[str, FieldCoord] = {
    "31": FieldCoord(page=0, x=500, y=92, width=70),
    "32": FieldCoord(page=0, x=500, y=80, width=70),
    "33": FieldCoord(page=0, x=500, y=68, width=70),
    "34": FieldCoord(page=0, x=500, y=56, width=70),
    "35": FieldCoord(page=0, x=500, y=44, width=70),
    "36": FieldCoord(page=0, x=500, y=32, width=70),
}

# ---------------------------------------------------------------------------
# Schedule C — Dividends, Inclusions, and Special Deductions (page 2)
# ---------------------------------------------------------------------------
SCHEDULE_C: dict[str, FieldCoord] = {
    # Column (a) — Dividends and inclusions
    "C1a": FieldCoord(page=1, x=200, y=640, width=80),
    "C2a": FieldCoord(page=1, x=200, y=624, width=80),
    "C3a": FieldCoord(page=1, x=200, y=608, width=80),
    "C4a": FieldCoord(page=1, x=200, y=592, width=80),
    "C5a": FieldCoord(page=1, x=200, y=576, width=80),
    "C6a": FieldCoord(page=1, x=200, y=560, width=80),
    "C7a": FieldCoord(page=1, x=200, y=544, width=80),
    "C8a": FieldCoord(page=1, x=200, y=528, width=80),
    "C9a": FieldCoord(page=1, x=200, y=512, width=80),
    "C10a": FieldCoord(page=1, x=200, y=496, width=80),
    # Column (b) — Percentage
    "C1b": FieldCoord(page=1, x=320, y=640, width=50),
    "C2b": FieldCoord(page=1, x=320, y=624, width=50),
    "C3b": FieldCoord(page=1, x=320, y=608, width=50),
    # Column (c) — Special deductions
    "C1c": FieldCoord(page=1, x=440, y=640, width=80),
    "C2c": FieldCoord(page=1, x=440, y=624, width=80),
    "C3c": FieldCoord(page=1, x=440, y=608, width=80),
    "C4c": FieldCoord(page=1, x=440, y=592, width=80),
    "C5c": FieldCoord(page=1, x=440, y=576, width=80),
    "C6c": FieldCoord(page=1, x=440, y=560, width=80),
    "C7c": FieldCoord(page=1, x=440, y=544, width=80),
    "C8c": FieldCoord(page=1, x=440, y=528, width=80),
    "C9c": FieldCoord(page=1, x=440, y=512, width=80),
    "C10c": FieldCoord(page=1, x=440, y=496, width=80),
    # Totals
    "C19": FieldCoord(page=1, x=440, y=400, width=80),
    "C20": FieldCoord(page=1, x=440, y=384, width=80),
}

# ---------------------------------------------------------------------------
# Schedule J — Tax Computation (page 2-3)
# ---------------------------------------------------------------------------
SCHEDULE_J: dict[str, FieldCoord] = {
    "J1": FieldCoord(page=1, x=500, y=340, width=70),
    "J2": FieldCoord(page=1, x=500, y=326, width=70),
    "J3": FieldCoord(page=1, x=500, y=312, width=70),
    "J4": FieldCoord(page=1, x=500, y=298, width=70),
    "J5a": FieldCoord(page=1, x=440, y=284, width=120),
    "J5b": FieldCoord(page=1, x=440, y=270, width=120),
    "J5c": FieldCoord(page=1, x=440, y=256, width=120),
    "J5d": FieldCoord(page=1, x=440, y=242, width=120),
    "J5e": FieldCoord(page=1, x=500, y=228, width=70),
    "J6": FieldCoord(page=1, x=500, y=214, width=70),
    "J7": FieldCoord(page=1, x=500, y=200, width=70),
    "J8": FieldCoord(page=1, x=500, y=186, width=70),
    "J9": FieldCoord(page=1, x=500, y=172, width=70),
    "J10": FieldCoord(page=1, x=500, y=158, width=70),
    # Part II — Payments, Refundable Credits, and Section 4971 Tax
    "J11": FieldCoord(page=2, x=500, y=680, width=70),
    "J12": FieldCoord(page=2, x=500, y=664, width=70),
    "J13": FieldCoord(page=2, x=500, y=648, width=70),
    "J14": FieldCoord(page=2, x=500, y=632, width=70),
    "J15": FieldCoord(page=2, x=500, y=616, width=70),
    "J16": FieldCoord(page=2, x=500, y=600, width=70),
    "J17": FieldCoord(page=2, x=500, y=584, width=70),
    "J18": FieldCoord(page=2, x=500, y=568, width=70),
    "J19": FieldCoord(page=2, x=500, y=552, width=70),
}

# ---------------------------------------------------------------------------
# Schedule K — Other Information (page 3)
# Checkboxes and text fields — many are yes/no
# ---------------------------------------------------------------------------
SCHEDULE_K_INFO: dict[str, FieldCoord] = {
    "K_1_method": FieldCoord(
        page=2, x=440, y=480, width=120, alignment="left", font_size=9
    ),
    "K_2_business_activity": FieldCoord(
        page=2, x=440, y=460, width=120, alignment="left", font_size=9
    ),
    "K_2_product_service": FieldCoord(
        page=2, x=440, y=444, width=120, alignment="left", font_size=9
    ),
}

# ---------------------------------------------------------------------------
# Schedule L — Balance Sheet per Books (page 4)
# ---------------------------------------------------------------------------
SCHEDULE_L: dict[str, FieldCoord] = {
    # Assets — Beginning of year (col b)
    "L1b": FieldCoord(page=3, x=200, y=600, width=80),
    "L2b": FieldCoord(page=3, x=200, y=584, width=80),
    "L3b": FieldCoord(page=3, x=200, y=568, width=80),
    "L4b": FieldCoord(page=3, x=200, y=552, width=80),
    "L5ab": FieldCoord(page=3, x=200, y=536, width=80),
    "L5bb": FieldCoord(page=3, x=280, y=536, width=80),
    "L6b": FieldCoord(page=3, x=200, y=520, width=80),
    "L7b": FieldCoord(page=3, x=200, y=504, width=80),
    "L8b": FieldCoord(page=3, x=200, y=488, width=80),
    "L9ab": FieldCoord(page=3, x=200, y=472, width=80),
    "L9bb": FieldCoord(page=3, x=280, y=472, width=80),
    "L10ab": FieldCoord(page=3, x=200, y=456, width=80),
    "L10bb": FieldCoord(page=3, x=280, y=456, width=80),
    "L11b": FieldCoord(page=3, x=200, y=440, width=80),
    "L12b": FieldCoord(page=3, x=200, y=424, width=80),
    "L13b": FieldCoord(page=3, x=200, y=408, width=80),
    "L14b": FieldCoord(page=3, x=200, y=392, width=80),
    "L15b": FieldCoord(page=3, x=200, y=376, width=80),
    # Assets — End of year (col d)
    "L1d": FieldCoord(page=3, x=440, y=600, width=80),
    "L2d": FieldCoord(page=3, x=440, y=584, width=80),
    "L3d": FieldCoord(page=3, x=440, y=568, width=80),
    "L4d": FieldCoord(page=3, x=440, y=552, width=80),
    "L5ad": FieldCoord(page=3, x=440, y=536, width=80),
    "L5bd": FieldCoord(page=3, x=520, y=536, width=80),
    "L6d": FieldCoord(page=3, x=440, y=520, width=80),
    "L7d": FieldCoord(page=3, x=440, y=504, width=80),
    "L8d": FieldCoord(page=3, x=440, y=488, width=80),
    "L9ad": FieldCoord(page=3, x=440, y=472, width=80),
    "L9bd": FieldCoord(page=3, x=520, y=472, width=80),
    "L10ad": FieldCoord(page=3, x=440, y=456, width=80),
    "L10bd": FieldCoord(page=3, x=520, y=456, width=80),
    "L11d": FieldCoord(page=3, x=440, y=440, width=80),
    "L12d": FieldCoord(page=3, x=440, y=424, width=80),
    "L13d": FieldCoord(page=3, x=440, y=408, width=80),
    "L14d": FieldCoord(page=3, x=440, y=392, width=80),
    "L15d": FieldCoord(page=3, x=440, y=376, width=80),
    # Liabilities & Shareholders' Equity — Beginning
    "L16b": FieldCoord(page=3, x=200, y=348, width=80),
    "L17b": FieldCoord(page=3, x=200, y=332, width=80),
    "L18b": FieldCoord(page=3, x=200, y=316, width=80),
    "L19b": FieldCoord(page=3, x=200, y=300, width=80),
    "L20b": FieldCoord(page=3, x=200, y=284, width=80),
    "L21b": FieldCoord(page=3, x=200, y=268, width=80),
    "L22b": FieldCoord(page=3, x=200, y=252, width=80),
    "L23b": FieldCoord(page=3, x=200, y=236, width=80),
    "L24b": FieldCoord(page=3, x=200, y=220, width=80),
    "L25b": FieldCoord(page=3, x=200, y=204, width=80),
    "L26b": FieldCoord(page=3, x=200, y=188, width=80),
    "L27b": FieldCoord(page=3, x=200, y=172, width=80),
    "L28b": FieldCoord(page=3, x=200, y=156, width=80),
    # Liabilities & Shareholders' Equity — End
    "L16d": FieldCoord(page=3, x=440, y=348, width=80),
    "L17d": FieldCoord(page=3, x=440, y=332, width=80),
    "L18d": FieldCoord(page=3, x=440, y=316, width=80),
    "L19d": FieldCoord(page=3, x=440, y=300, width=80),
    "L20d": FieldCoord(page=3, x=440, y=284, width=80),
    "L21d": FieldCoord(page=3, x=440, y=268, width=80),
    "L22d": FieldCoord(page=3, x=440, y=252, width=80),
    "L23d": FieldCoord(page=3, x=440, y=236, width=80),
    "L24d": FieldCoord(page=3, x=440, y=220, width=80),
    "L25d": FieldCoord(page=3, x=440, y=204, width=80),
    "L26d": FieldCoord(page=3, x=440, y=188, width=80),
    "L27d": FieldCoord(page=3, x=440, y=172, width=80),
    "L28d": FieldCoord(page=3, x=440, y=156, width=80),
}

# ---------------------------------------------------------------------------
# Schedule M-1 — Reconciliation of Income (Loss) (page 4, lower section)
# ---------------------------------------------------------------------------
SCHEDULE_M1: dict[str, FieldCoord] = {
    "M1_1": FieldCoord(page=3, x=250, y=120, width=80),
    "M1_2": FieldCoord(page=3, x=250, y=104, width=80),
    "M1_3": FieldCoord(page=3, x=250, y=88, width=80),
    "M1_4": FieldCoord(page=3, x=250, y=72, width=80),
    "M1_5": FieldCoord(page=3, x=250, y=56, width=80),
    "M1_6": FieldCoord(page=3, x=500, y=120, width=70),
    "M1_7": FieldCoord(page=3, x=500, y=104, width=70),
    "M1_8": FieldCoord(page=3, x=500, y=88, width=70),
    "M1_9": FieldCoord(page=3, x=500, y=72, width=70),
    "M1_10": FieldCoord(page=3, x=500, y=56, width=70),
}

# ---------------------------------------------------------------------------
# Schedule M-2 — Analysis of Unappropriated Retained Earnings (page 5)
# ---------------------------------------------------------------------------
SCHEDULE_M2: dict[str, FieldCoord] = {
    "M2_1": FieldCoord(page=4, x=250, y=700, width=80),
    "M2_2": FieldCoord(page=4, x=250, y=684, width=80),
    "M2_3": FieldCoord(page=4, x=250, y=668, width=80),
    "M2_4": FieldCoord(page=4, x=250, y=652, width=80),
    "M2_5a": FieldCoord(page=4, x=500, y=700, width=70),
    "M2_5b": FieldCoord(page=4, x=500, y=684, width=70),
    "M2_6": FieldCoord(page=4, x=500, y=668, width=70),
    "M2_7": FieldCoord(page=4, x=500, y=652, width=70),
    "M2_8": FieldCoord(page=4, x=500, y=636, width=70),
}

# ---------------------------------------------------------------------------
# Schedule A — Cost of Goods Sold (shared page with Schedule C)
# On Form 1120, COGS is part of the income section, typically referenced
# from page 2 or a separate schedule.
# ---------------------------------------------------------------------------
SCHEDULE_A: dict[str, FieldCoord] = {
    "A1": FieldCoord(page=1, x=500, y=140, width=70),
    "A2": FieldCoord(page=1, x=500, y=128, width=70),
    "A3": FieldCoord(page=1, x=500, y=116, width=70),
    "A4": FieldCoord(page=1, x=500, y=104, width=70),
    "A5": FieldCoord(page=1, x=500, y=92, width=70),
    "A6": FieldCoord(page=1, x=500, y=80, width=70),
    "A7": FieldCoord(page=1, x=500, y=68, width=70),
    "A8": FieldCoord(page=1, x=500, y=56, width=70),
}

# ---------------------------------------------------------------------------
# Combined field map — used by the renderer
# ---------------------------------------------------------------------------
FIELD_MAP: dict[str, FieldCoord] = {
    **PAGE1_INCOME,
    **PAGE1_DEDUCTIONS,
    **PAGE1_TAX,
    **SCHEDULE_A,
    **SCHEDULE_C,
    **SCHEDULE_J,
    **SCHEDULE_K_INFO,
    **SCHEDULE_L,
    **SCHEDULE_M1,
    **SCHEDULE_M2,
}
