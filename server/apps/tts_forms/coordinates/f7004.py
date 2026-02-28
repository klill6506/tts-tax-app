"""
Field coordinate mappings for Form 7004 — Application for Automatic
Extension of Time To File (Rev. December 2025).

Coordinates are in PDF points (1 point = 1/72 inch).
Origin (0, 0) is the bottom-left corner of the page.
Page size: 612 x 792 points.

Single-page form. Used for S-Corps (code 25), partnerships (code 09),
C-Corps (code 12), and other entity types.

Coordinates calibrated via pdfplumber extraction from the official 2025 PDF.
"""

from .f1120s import FieldCoord

# ---------------------------------------------------------------------------
# Header fields (entity info block at top of form)
# ---------------------------------------------------------------------------

HEADER_FIELDS: dict[str, FieldCoord] = {
    "entity_name": FieldCoord(
        page=0, x=90, y=696, width=350, alignment="left", font_size=10,
    ),
    "ein": FieldCoord(
        page=0, x=452, y=696, width=120, alignment="left", font_size=10,
    ),
    "address_street": FieldCoord(
        page=0, x=90, y=670, width=390, alignment="left", font_size=10,
    ),
    "address_city_state_zip": FieldCoord(
        page=0, x=90, y=646, width=380, alignment="left", font_size=10,
    ),
}

# ---------------------------------------------------------------------------
# Amount column x-position (right side of form, lines 6-8)
# ---------------------------------------------------------------------------

_AMT_X = 508
_AMT_W = 68

# ---------------------------------------------------------------------------
# Form fields
# ---------------------------------------------------------------------------

FIELD_MAP: dict[str, FieldCoord] = {
    # Part I — Line 1: 2-digit form code
    "1": FieldCoord(
        page=0, x=545, y=610, width=30, alignment="center", font_size=12,
    ),

    # Part II — Checkboxes (rarely used for domestic S-Corps)
    "2": FieldCoord(
        page=0, x=542, y=347, width=10, alignment="left", font_size=9,
    ),
    "3": FieldCoord(
        page=0, x=542, y=323, width=10, alignment="left", font_size=9,
    ),
    "4": FieldCoord(
        page=0, x=542, y=286, width=10, alignment="left", font_size=9,
    ),

    # Line 5a: Tax year
    "5a_year": FieldCoord(
        page=0, x=239, y=274, width=20, alignment="left", font_size=9,
    ),
    "5a_begin": FieldCoord(
        page=0, x=340, y=274, width=42, alignment="left", font_size=9,
    ),
    "5a_begin_year": FieldCoord(
        page=0, x=400, y=274, width=16, alignment="left", font_size=9,
    ),
    "5a_end": FieldCoord(
        page=0, x=478, y=274, width=50, alignment="left", font_size=9,
    ),
    "5a_end_year": FieldCoord(
        page=0, x=552, y=274, width=16, alignment="left", font_size=9,
    ),

    # Line 5b: Short tax year checkboxes
    "5b_initial": FieldCoord(
        page=0, x=374, y=262, width=10, alignment="left", font_size=9,
    ),
    "5b_final": FieldCoord(
        page=0, x=460, y=262, width=10, alignment="left", font_size=9,
    ),
    "5b_change": FieldCoord(
        page=0, x=64, y=250, width=10, alignment="left", font_size=9,
    ),
    "5b_consolidated": FieldCoord(
        page=0, x=216, y=250, width=10, alignment="left", font_size=9,
    ),
    "5b_other": FieldCoord(
        page=0, x=374, y=250, width=10, alignment="left", font_size=9,
    ),

    # Line 6: Tentative total tax
    "6": FieldCoord(
        page=0, x=_AMT_X, y=226, width=_AMT_W, alignment="right", font_size=9,
    ),

    # Line 7: Total payments and credits
    "7": FieldCoord(
        page=0, x=_AMT_X, y=202, width=_AMT_W, alignment="right", font_size=9,
    ),

    # Line 8: Balance due
    "8": FieldCoord(
        page=0, x=_AMT_X, y=178, width=_AMT_W, alignment="right", font_size=9,
    ),
}
