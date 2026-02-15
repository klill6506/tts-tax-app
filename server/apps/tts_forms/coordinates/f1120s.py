"""
Field coordinate mappings for IRS Form 1120-S.

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

CALIBRATION NOTE: These coordinates are approximate starting points
based on the standard 2024/2025 Form 1120-S layout. After downloading
the actual IRS PDF via update_irs_forms.py, fine-tune coordinates by
rendering a test PDF and comparing field positions.

To calibrate:
    1. Render a return with known values.
    2. Open the generated PDF alongside the blank IRS form.
    3. Adjust x/y values here until fields align with the IRS boxes.
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
# Page 1 — Header / Entity Information
# ---------------------------------------------------------------------------
HEADER_FIELDS: dict[str, FieldCoord] = {
    # Entity name (top of form)
    "entity_name": FieldCoord(page=0, x=140, y=672, width=280, alignment="left"),
    # Street address
    "address_street": FieldCoord(page=0, x=140, y=650, width=280, alignment="left"),
    # City, state, ZIP
    "address_city_state_zip": FieldCoord(
        page=0, x=140, y=628, width=280, alignment="left"
    ),
    # EIN
    "ein": FieldCoord(page=0, x=480, y=672, width=100, alignment="left"),
    # Date incorporated
    "date_incorporated": FieldCoord(
        page=0, x=480, y=650, width=100, alignment="left"
    ),
    # Tax year (beginning / ending)
    "tax_year_begin": FieldCoord(
        page=0, x=145, y=737, width=80, alignment="left", font_size=8
    ),
    "tax_year_end": FieldCoord(
        page=0, x=310, y=737, width=80, alignment="left", font_size=8
    ),
}

# ---------------------------------------------------------------------------
# Page 1 — Income (lines 1a through 6)
# Y coordinates descend from top of income section (~545) downward
# ---------------------------------------------------------------------------
PAGE1_INCOME: dict[str, FieldCoord] = {
    "1a": FieldCoord(page=0, x=440, y=506, width=120),
    "1b": FieldCoord(page=0, x=440, y=494, width=120),
    "1c": FieldCoord(page=0, x=500, y=482, width=70),
    "2": FieldCoord(page=0, x=500, y=470, width=70),
    "3": FieldCoord(page=0, x=500, y=458, width=70),
    "4": FieldCoord(page=0, x=500, y=446, width=70),
    "5": FieldCoord(page=0, x=500, y=434, width=70),
    "6": FieldCoord(page=0, x=500, y=422, width=70),
}

# ---------------------------------------------------------------------------
# Page 1 — Deductions (lines 7 through 21)
# ---------------------------------------------------------------------------
PAGE1_DEDUCTIONS: dict[str, FieldCoord] = {
    "7": FieldCoord(page=0, x=500, y=398, width=70),
    "8": FieldCoord(page=0, x=500, y=386, width=70),
    "9": FieldCoord(page=0, x=500, y=374, width=70),
    "10": FieldCoord(page=0, x=500, y=362, width=70),
    "11": FieldCoord(page=0, x=500, y=350, width=70),
    "12": FieldCoord(page=0, x=500, y=338, width=70),
    "13": FieldCoord(page=0, x=500, y=326, width=70),
    "14": FieldCoord(page=0, x=500, y=314, width=70),
    "15": FieldCoord(page=0, x=500, y=302, width=70),
    "16": FieldCoord(page=0, x=500, y=290, width=70),
    "17": FieldCoord(page=0, x=500, y=278, width=70),
    "18": FieldCoord(page=0, x=500, y=266, width=70),
    "19": FieldCoord(page=0, x=500, y=254, width=70),
    "20": FieldCoord(page=0, x=500, y=242, width=70),
    "21": FieldCoord(page=0, x=500, y=230, width=70),
}

# ---------------------------------------------------------------------------
# Page 1 — Tax and Payments (lines 22a through 27)
# ---------------------------------------------------------------------------
PAGE1_TAX: dict[str, FieldCoord] = {
    "22a": FieldCoord(page=0, x=440, y=206, width=120),
    "22b": FieldCoord(page=0, x=440, y=194, width=120),
    "22c": FieldCoord(page=0, x=500, y=182, width=70),
    "23a": FieldCoord(page=0, x=440, y=170, width=120),
    "23b": FieldCoord(page=0, x=440, y=158, width=120),
    "23c": FieldCoord(page=0, x=440, y=146, width=120),
    "23d": FieldCoord(page=0, x=500, y=134, width=70),
    "24": FieldCoord(page=0, x=500, y=122, width=70),
    "25": FieldCoord(page=0, x=500, y=110, width=70),
    "26": FieldCoord(page=0, x=500, y=98, width=70),
    "27": FieldCoord(page=0, x=500, y=86, width=70),
}

# ---------------------------------------------------------------------------
# Schedule A — Cost of Goods Sold (page 2 of PDF, 0-indexed page 1)
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
# Schedule K — Shareholders' Pro Rata Share Items (page 3, 0-indexed page 2)
# ---------------------------------------------------------------------------
SCHEDULE_K: dict[str, FieldCoord] = {
    "K1": FieldCoord(page=3, x=500, y=640, width=70),
    "K2": FieldCoord(page=3, x=500, y=624, width=70),
    "K3": FieldCoord(page=3, x=500, y=608, width=70),
    "K4": FieldCoord(page=3, x=500, y=592, width=70),
    "K5a": FieldCoord(page=3, x=500, y=576, width=70),
    "K5b": FieldCoord(page=3, x=500, y=560, width=70),
    "K6": FieldCoord(page=3, x=500, y=544, width=70),
    "K7": FieldCoord(page=3, x=500, y=528, width=70),
    "K8a": FieldCoord(page=3, x=500, y=512, width=70),
    "K9": FieldCoord(page=3, x=500, y=496, width=70),
    "K10": FieldCoord(page=3, x=500, y=480, width=70),
    "K11": FieldCoord(page=3, x=500, y=464, width=70),
    "K12a": FieldCoord(page=3, x=500, y=448, width=70),
    "K13a": FieldCoord(page=3, x=500, y=432, width=70),
    "K14a": FieldCoord(page=3, x=500, y=416, width=70, alignment="left"),
    "K15a": FieldCoord(page=3, x=500, y=400, width=70),
    "K16a": FieldCoord(page=3, x=500, y=384, width=70),
    "K16b": FieldCoord(page=3, x=500, y=368, width=70),
    "K16c": FieldCoord(page=3, x=500, y=352, width=70),
    "K16d": FieldCoord(page=3, x=500, y=336, width=70),
    "K17a": FieldCoord(page=3, x=500, y=320, width=70),
    "K17b": FieldCoord(page=3, x=500, y=304, width=70),
}

# ---------------------------------------------------------------------------
# Schedule L — Balance Sheet (page 4, 0-indexed page 4)
# Two columns: beginning of year (col a) and end of year (col d)
# ---------------------------------------------------------------------------
SCHEDULE_L: dict[str, FieldCoord] = {
    # Beginning of year (left column)
    "L1a": FieldCoord(page=4, x=200, y=620, width=80),
    "L2a": FieldCoord(page=4, x=200, y=604, width=80),
    "L5a": FieldCoord(page=4, x=200, y=572, width=80),
    "L7a": FieldCoord(page=4, x=200, y=556, width=80),
    "L9a": FieldCoord(page=4, x=200, y=524, width=80),
    "L9b": FieldCoord(page=4, x=280, y=524, width=80),
    "L14a": FieldCoord(page=4, x=200, y=476, width=80),
    "L15a": FieldCoord(page=4, x=200, y=460, width=80),
    "L17a": FieldCoord(page=4, x=200, y=428, width=80),
    "L18a": FieldCoord(page=4, x=200, y=412, width=80),
    "L20a": FieldCoord(page=4, x=200, y=380, width=80),
    "L21a": FieldCoord(page=4, x=200, y=364, width=80),
    "L23a": FieldCoord(page=4, x=200, y=332, width=80),
    "L24a": FieldCoord(page=4, x=200, y=316, width=80),
    "L25a": FieldCoord(page=4, x=200, y=300, width=80),
    "L27a": FieldCoord(page=4, x=200, y=268, width=80),
    # End of year (right column)
    "L1d": FieldCoord(page=4, x=440, y=620, width=80),
    "L2d": FieldCoord(page=4, x=440, y=604, width=80),
    "L5d": FieldCoord(page=4, x=440, y=572, width=80),
    "L7d": FieldCoord(page=4, x=440, y=556, width=80),
    "L9d": FieldCoord(page=4, x=440, y=524, width=80),
    "L9e": FieldCoord(page=4, x=520, y=524, width=80),
    "L14d": FieldCoord(page=4, x=440, y=476, width=80),
    "L15d": FieldCoord(page=4, x=440, y=460, width=80),
    "L17d": FieldCoord(page=4, x=440, y=428, width=80),
    "L18d": FieldCoord(page=4, x=440, y=412, width=80),
    "L20d": FieldCoord(page=4, x=440, y=380, width=80),
    "L21d": FieldCoord(page=4, x=440, y=364, width=80),
    "L23d": FieldCoord(page=4, x=440, y=332, width=80),
    "L24d": FieldCoord(page=4, x=440, y=316, width=80),
    "L25d": FieldCoord(page=4, x=440, y=300, width=80),
    "L27d": FieldCoord(page=4, x=440, y=268, width=80),
}

# ---------------------------------------------------------------------------
# Schedule M-1 and M-2 (page 4, lower portion)
# ---------------------------------------------------------------------------
SCHEDULE_M1: dict[str, FieldCoord] = {
    "M1_1": FieldCoord(page=4, x=250, y=220, width=80),
    "M1_2": FieldCoord(page=4, x=250, y=204, width=80),
    "M1_3a": FieldCoord(page=4, x=250, y=188, width=80),
    "M1_3b": FieldCoord(page=4, x=250, y=172, width=80),
    "M1_4": FieldCoord(page=4, x=250, y=156, width=80),
    "M1_5": FieldCoord(page=4, x=500, y=220, width=70),
    "M1_6": FieldCoord(page=4, x=500, y=204, width=70),
    "M1_7": FieldCoord(page=4, x=500, y=188, width=70),
    "M1_8": FieldCoord(page=4, x=500, y=172, width=70),
}

SCHEDULE_M2: dict[str, FieldCoord] = {
    "M2_1": FieldCoord(page=4, x=250, y=120, width=80),
    "M2_2": FieldCoord(page=4, x=250, y=104, width=80),
    "M2_3": FieldCoord(page=4, x=250, y=88, width=80),
    "M2_4": FieldCoord(page=4, x=500, y=120, width=70),
    "M2_5": FieldCoord(page=4, x=500, y=104, width=70),
    "M2_6": FieldCoord(page=4, x=500, y=88, width=70),
    "M2_7": FieldCoord(page=4, x=500, y=72, width=70),
    "M2_8": FieldCoord(page=4, x=500, y=56, width=70),
}

# ---------------------------------------------------------------------------
# Combined field map — used by the renderer
# ---------------------------------------------------------------------------
FIELD_MAP: dict[str, FieldCoord] = {
    **PAGE1_INCOME,
    **PAGE1_DEDUCTIONS,
    **PAGE1_TAX,
    **SCHEDULE_A,
    **SCHEDULE_K,
    **SCHEDULE_L,
    **SCHEDULE_M1,
    **SCHEDULE_M2,
}
