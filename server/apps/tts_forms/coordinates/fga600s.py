"""
Field coordinate mappings for Georgia Form 600S -- S Corporation Tax Return (2024).

Coordinates are in PDF points (1 point = 1/72 inch).
Origin (0, 0) is the bottom-left corner of the page.
Page size: 612 x 792 points (US Letter).

7-page form. Schedules covered:
  Page 0: Header + Schedule 1 (GA Taxable Income & Tax)
  Page 1: Schedule 3 (Net Worth Tax) + Schedule 4 (Tax Due/Overpayment)
          + Schedule 5 (GA Net Income) + Schedule 6 (Total Income)
  Page 2: Schedule 7 (Additions) + Schedule 8 (Subtractions)
  Pages 3-6: Schedules 9-13 (deferred — NOL, apportionment, credits)

Coordinates calibrated via pdfplumber extraction from the official 2024 PDF.
"""

from .f1120s import FieldCoord

# ---------------------------------------------------------------------------
# Header fields (Page 0 — corporation identification area)
# ---------------------------------------------------------------------------
HEADER_FIELDS: dict[str, FieldCoord] = {
    # B. Corporation name (top of info block, right of FEIN)
    "entity_name": FieldCoord(
        page=0, x=245, y=518, width=325, alignment="left", font_size=10
    ),
    # A. FEIN (top of info block, left side)
    "ein": FieldCoord(
        page=0, x=65, y=518, width=135, alignment="left", font_size=10
    ),
}

# ---------------------------------------------------------------------------
# Schedule 1 — Computation of GA Taxable Income and Tax (Page 0)
# Amount column on right side: x=430 to x=573, right-aligned
# ---------------------------------------------------------------------------
_S1_X = 430
_S1_W = 143

# ---------------------------------------------------------------------------
# Schedule 3 — Computation of Net Worth Tax (Page 1, top)
# Amount column: x=432 to x=575, right-aligned
# ---------------------------------------------------------------------------
_S3_X = 432
_S3_W = 143

# ---------------------------------------------------------------------------
# Schedule 4 — Tax Due or Overpayment (Page 1, middle)
# Three columns: A=Income Tax, B=Net Worth Tax, C=Total
# ---------------------------------------------------------------------------
_S4_AX = 280    # Column A left edge
_S4_AW = 80     # Column A width (right edge at 360)
_S4_BX = 365    # Column B left edge
_S4_BW = 75     # Column B width (right edge at 440)
_S4_CX = 460    # Column C left edge
_S4_CW = 113    # Column C width (right edge at 573)

# ---------------------------------------------------------------------------
# Schedule 5 — Computation of Georgia Net Income (Page 1, lower-middle)
# Amount column: x=426 to x=575, right-aligned
# ---------------------------------------------------------------------------
_S5_X = 426
_S5_W = 149

# ---------------------------------------------------------------------------
# Schedule 6 — Total Income for GA Purposes (Page 1, bottom)
# Main column: x=425 to x=573, right-aligned
# Sub-column for lines 3a/3b: x=289 to x=419, right-aligned
# Sub-column for lines 4a-4f: x=460 to x=573, right-aligned
# ---------------------------------------------------------------------------
_S6_MAIN_X = 425
_S6_MAIN_W = 148
_S6_SUB_X = 289
_S6_SUB_W = 130
_S6_PORT_X = 460   # portfolio sub-lines (4a-4f)
_S6_PORT_W = 113

# ---------------------------------------------------------------------------
# Schedule 7 — Additions to Federal Taxable Income (Page 2, top)
# Amount column: x=428 to x=576, right-aligned
# ---------------------------------------------------------------------------
_S7_X = 428
_S7_W = 148

# ---------------------------------------------------------------------------
# Schedule 8 — Subtractions from Federal Taxable Income (Page 2, middle)
# Amount column: x=428 to x=575, right-aligned
# ---------------------------------------------------------------------------
_S8_X = 428
_S8_W = 147


FIELD_MAP: dict[str, FieldCoord] = {
    # ===== SCHEDULE 1 (Page 0) =====
    "S1_1": FieldCoord(page=0, x=_S1_X, y=230, width=_S1_W),
    "S1_2": FieldCoord(page=0, x=_S1_X, y=218, width=_S1_W),
    "S1_3": FieldCoord(page=0, x=_S1_X, y=206, width=_S1_W),
    "S1_4": FieldCoord(page=0, x=_S1_X, y=194, width=_S1_W),
    "S1_5": FieldCoord(page=0, x=_S1_X, y=182, width=_S1_W),
    "S1_6": FieldCoord(page=0, x=_S1_X, y=170, width=_S1_W),
    "S1_7": FieldCoord(page=0, x=_S1_X, y=157, width=_S1_W),

    # ===== SCHEDULE 3 (Page 1) =====
    "S3_1": FieldCoord(page=1, x=_S3_X, y=649, width=_S3_W),
    "S3_2": FieldCoord(page=1, x=_S3_X, y=637, width=_S3_W),
    "S3_3": FieldCoord(page=1, x=_S3_X, y=625, width=_S3_W),
    "S3_4": FieldCoord(page=1, x=_S3_X, y=616, width=_S3_W),
    "S3_5": FieldCoord(page=1, x=_S3_X, y=601, width=_S3_W),
    "S3_6": FieldCoord(page=1, x=_S3_X, y=589, width=_S3_W),
    "S3_7": FieldCoord(page=1, x=_S3_X, y=577, width=_S3_W),

    # ===== SCHEDULE 4 (Page 1) — 3-column layout =====
    # Row 1: Total Tax
    "S4_1a": FieldCoord(page=1, x=_S4_AX, y=529, width=_S4_AW),
    "S4_1b": FieldCoord(page=1, x=_S4_BX, y=529, width=_S4_BW),
    "S4_1c": FieldCoord(page=1, x=_S4_CX, y=529, width=_S4_CW),
    # Row 2: Estimated tax payments
    "S4_2a": FieldCoord(page=1, x=_S4_AX, y=516, width=_S4_AW),
    "S4_2b": FieldCoord(page=1, x=_S4_BX, y=516, width=_S4_BW),
    "S4_2c": FieldCoord(page=1, x=_S4_CX, y=516, width=_S4_CW),
    # Row 3: Credits from Schedule 11
    "S4_3a": FieldCoord(page=1, x=_S4_AX, y=505, width=_S4_AW),
    "S4_3b": FieldCoord(page=1, x=_S4_BX, y=505, width=_S4_BW),
    "S4_3c": FieldCoord(page=1, x=_S4_CX, y=505, width=_S4_CW),
    # Row 4: Withholding Credits
    "S4_4a": FieldCoord(page=1, x=_S4_AX, y=493, width=_S4_AW),
    "S4_4b": FieldCoord(page=1, x=_S4_BX, y=493, width=_S4_BW),
    "S4_4c": FieldCoord(page=1, x=_S4_CX, y=493, width=_S4_CW),
    # Row 5: Balance of tax due
    "S4_5a": FieldCoord(page=1, x=_S4_AX, y=482, width=_S4_AW),
    "S4_5b": FieldCoord(page=1, x=_S4_BX, y=482, width=_S4_BW),
    "S4_5c": FieldCoord(page=1, x=_S4_CX, y=482, width=_S4_CW),
    # Row 6: Amount of overpayment
    "S4_6a": FieldCoord(page=1, x=_S4_AX, y=468, width=_S4_AW),
    "S4_6b": FieldCoord(page=1, x=_S4_BX, y=468, width=_S4_BW),
    "S4_6c": FieldCoord(page=1, x=_S4_CX, y=468, width=_S4_CW),
    # Row 7: Interest due
    "S4_7a": FieldCoord(page=1, x=_S4_AX, y=457, width=_S4_AW),
    "S4_7b": FieldCoord(page=1, x=_S4_BX, y=457, width=_S4_BW),
    "S4_7c": FieldCoord(page=1, x=_S4_CX, y=457, width=_S4_CW),
    # Row 8: Form 600 UET penalty
    "S4_8a": FieldCoord(page=1, x=_S4_AX, y=446, width=_S4_AW),
    "S4_8b": FieldCoord(page=1, x=_S4_BX, y=446, width=_S4_BW),
    "S4_8c": FieldCoord(page=1, x=_S4_CX, y=446, width=_S4_CW),
    # Row 9: Other penalty due
    "S4_9a": FieldCoord(page=1, x=_S4_AX, y=433, width=_S4_AW),
    "S4_9b": FieldCoord(page=1, x=_S4_BX, y=433, width=_S4_BW),
    "S4_9c": FieldCoord(page=1, x=_S4_CX, y=433, width=_S4_CW),
    # Row 10: Amount Due
    "S4_10a": FieldCoord(page=1, x=_S4_AX, y=421, width=_S4_AW),
    "S4_10b": FieldCoord(page=1, x=_S4_BX, y=421, width=_S4_BW),
    "S4_10c": FieldCoord(page=1, x=_S4_CX, y=421, width=_S4_CW),
    # Row 11: Credit to next year estimated tax
    "S4_11a": FieldCoord(page=1, x=_S4_AX, y=409, width=_S4_AW),
    "S4_11b": FieldCoord(page=1, x=_S4_BX, y=409, width=_S4_BW),
    "S4_11c": FieldCoord(page=1, x=_S4_CX, y=409, width=_S4_CW),

    # ===== SCHEDULE 5 (Page 1) =====
    "S5_1": FieldCoord(page=1, x=_S5_X, y=375, width=_S5_W),
    "S5_2": FieldCoord(page=1, x=_S5_X, y=363, width=_S5_W),
    "S5_3": FieldCoord(page=1, x=_S5_X, y=351, width=_S5_W),
    "S5_4": FieldCoord(page=1, x=_S5_X, y=339, width=_S5_W),
    "S5_5": FieldCoord(page=1, x=_S5_X, y=325, width=_S5_W),
    "S5_6": FieldCoord(page=1, x=_S5_X, y=313, width=_S5_W),
    "S5_7": FieldCoord(page=1, x=_S5_X, y=300, width=_S5_W),

    # ===== SCHEDULE 6 (Page 1, bottom) =====
    # Lines 1-2: main column
    "S6_1": FieldCoord(page=1, x=_S6_MAIN_X, y=266, width=_S6_MAIN_W),
    "S6_2": FieldCoord(page=1, x=_S6_MAIN_X, y=255, width=_S6_MAIN_W),
    # Lines 3a-3b: sub-column (rental activities detail)
    "S6_3a": FieldCoord(page=1, x=_S6_SUB_X, y=243, width=_S6_SUB_W),
    "S6_3b": FieldCoord(page=1, x=_S6_SUB_X, y=231, width=_S6_SUB_W),
    # Line 3c: main column (net rental)
    "S6_3c": FieldCoord(page=1, x=_S6_MAIN_X, y=231, width=_S6_MAIN_W),
    # Lines 4a-4f: portfolio income (right sub-column after sub-labels)
    "S6_4a": FieldCoord(page=1, x=_S6_PORT_X, y=219, width=_S6_PORT_W),
    "S6_4b": FieldCoord(page=1, x=_S6_PORT_X, y=206, width=_S6_PORT_W),
    "S6_4c": FieldCoord(page=1, x=_S6_PORT_X, y=195, width=_S6_PORT_W),
    "S6_4d": FieldCoord(page=1, x=_S6_PORT_X, y=183, width=_S6_PORT_W),
    "S6_4e": FieldCoord(page=1, x=_S6_PORT_X, y=171, width=_S6_PORT_W),
    "S6_4f": FieldCoord(page=1, x=_S6_PORT_X, y=159, width=_S6_PORT_W),
    # Lines 5-11: main column
    "S6_5": FieldCoord(page=1, x=_S6_MAIN_X, y=146, width=_S6_MAIN_W),
    "S6_6": FieldCoord(page=1, x=_S6_MAIN_X, y=134, width=_S6_MAIN_W),
    "S6_7": FieldCoord(page=1, x=_S6_MAIN_X, y=123, width=_S6_MAIN_W),
    "S6_8": FieldCoord(page=1, x=_S6_MAIN_X, y=110, width=_S6_MAIN_W),
    "S6_9": FieldCoord(page=1, x=_S6_MAIN_X, y=99, width=_S6_MAIN_W),
    "S6_10": FieldCoord(page=1, x=_S6_MAIN_X, y=86, width=_S6_MAIN_W),
    "S6_11": FieldCoord(page=1, x=_S6_MAIN_X, y=74, width=_S6_MAIN_W),

    # ===== SCHEDULE 7 (Page 2) =====
    "S7_1": FieldCoord(page=2, x=_S7_X, y=650, width=_S7_W),
    "S7_2": FieldCoord(page=2, x=_S7_X, y=638, width=_S7_W),
    "S7_3": FieldCoord(page=2, x=_S7_X, y=626, width=_S7_W),
    "S7_4": FieldCoord(page=2, x=_S7_X, y=613, width=_S7_W),
    "S7_5": FieldCoord(page=2, x=_S7_X, y=601, width=_S7_W),
    "S7_6": FieldCoord(page=2, x=_S7_X, y=589, width=_S7_W),
    "S7_7": FieldCoord(page=2, x=_S7_X, y=577, width=_S7_W),
    "S7_8": FieldCoord(page=2, x=_S7_X, y=565, width=_S7_W),

    # ===== SCHEDULE 8 (Page 2) =====
    "S8_1": FieldCoord(page=2, x=_S8_X, y=541, width=_S8_W),
    "S8_2": FieldCoord(page=2, x=_S8_X, y=529, width=_S8_W),
    "S8_3": FieldCoord(page=2, x=_S8_X, y=518, width=_S8_W),
    "S8_4": FieldCoord(page=2, x=_S8_X, y=506, width=_S8_W),
    "S8_5": FieldCoord(page=2, x=_S8_X, y=493, width=_S8_W),
}
