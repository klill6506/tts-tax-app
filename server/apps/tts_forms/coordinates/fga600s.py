"""
Field coordinate mappings for Georgia Form 600S -- S Corporation Tax Return (2024).

Coordinates are in PDF points (1 point = 1/72 inch).
Origin (0, 0) is the bottom-left corner of the page (ReportLab convention).
Page size: 612 x 792 points (US Letter).

7-page form. Schedules covered:
  Page 0: Header (fields A-X, dates, checkboxes) + Schedule 1
  Page 1: Schedule 4 (Tax Due) + Schedule 3 (Net Worth) + Schedule 5 + Schedule 6
  Page 2: Header (FEIN, Name) + Schedule 7 (Additions) + Schedule 8 (Subtractions)
  Pages 3-6: Schedules 9-13 (deferred — NOL, apportionment, credits)

Coordinates verified against pymupdf text extraction from the official 2024 PDF.
"""

from .f1120s import FieldCoord

# ---------------------------------------------------------------------------
# Header fields (Page 0 — corporation identification area)
# ---------------------------------------------------------------------------
HEADER_FIELDS: dict[str, FieldCoord] = {
    # --- Tax period dates ---
    # Income Tax Period: Beginning / Ending (labels at rl_y≈636/612)
    "income_tax_begin": FieldCoord(
        page=0, x=100, y=636, width=80, alignment="left", font_size=9
    ),
    "income_tax_end": FieldCoord(
        page=0, x=100, y=612, width=80, alignment="left", font_size=9
    ),
    # Net Worth Tax Period: Beginning / Ending (labels at rl_y≈564/540)
    "nw_tax_begin": FieldCoord(
        page=0, x=100, y=564, width=80, alignment="left", font_size=9
    ),
    "nw_tax_end": FieldCoord(
        page=0, x=100, y=540, width=80, alignment="left", font_size=9
    ),

    # --- Entity Identification (A-I) ---
    # A. Federal Employer ID Number (label at rl_y≈520, value below)
    "ein": FieldCoord(
        page=0, x=44, y=503, width=160, alignment="left", font_size=10
    ),
    # B. Corporation Name (label at rl_y≈520, value below)
    "entity_name": FieldCoord(
        page=0, x=210, y=503, width=365, alignment="left", font_size=10
    ),
    # C. GA Withholding Tax Acct. Number (label at rl_y≈483, value below)
    "ga_withholding_number": FieldCoord(
        page=0, x=44, y=467, width=160, alignment="left", font_size=9
    ),
    # D. Business Street Address (label at rl_y≈483, value below)
    "address_street": FieldCoord(
        page=0, x=210, y=467, width=365, alignment="left", font_size=10
    ),
    # E. GA Sales Tax Reg. Number (label at rl_y≈447, value below)
    "ga_sales_tax_number": FieldCoord(
        page=0, x=44, y=432, width=115, alignment="left", font_size=9
    ),
    # F. City or Town (label at rl_y≈447, value below)
    "address_city": FieldCoord(
        page=0, x=162, y=432, width=195, alignment="left", font_size=10
    ),
    # G. State (label at rl_y≈446, value below)
    "address_state": FieldCoord(
        page=0, x=360, y=432, width=38, alignment="left", font_size=10
    ),
    # H. ZIP Code (label at rl_y≈446, value below)
    "address_zip": FieldCoord(
        page=0, x=402, y=432, width=65, alignment="left", font_size=10
    ),
    # I. Foreign Country Name (label at rl_y≈446, value below — usually blank)
    "foreign_country": FieldCoord(
        page=0, x=472, y=432, width=100, alignment="left", font_size=9
    ),

    # --- Entity Details (J-P) ---
    # J. NAICS Code (label at rl_y≈411, value below at rl_y≈396)
    "naics_code": FieldCoord(
        page=0, x=43, y=396, width=80, alignment="left", font_size=9
    ),
    # K. Date of Incorporation (label at rl_y≈411, value below)
    "date_incorporated": FieldCoord(
        page=0, x=126, y=396, width=100, alignment="left", font_size=9
    ),
    # L. State of Incorporation (label at rl_y≈411, value below)
    "state_incorporated": FieldCoord(
        page=0, x=233, y=396, width=90, alignment="left", font_size=9
    ),
    # M. Date admitted into GA (label at rl_y≈411, value below)
    "date_admitted_ga": FieldCoord(
        page=0, x=329, y=396, width=100, alignment="left", font_size=9
    ),
    # N. Type of Business (label at rl_y≈411, value below)
    "type_of_business": FieldCoord(
        page=0, x=435, y=396, width=140, alignment="left", font_size=9
    ),
    # O. Location of Records for Audit: City, State, Country (label at rl_y≈374)
    "records_city": FieldCoord(
        page=0, x=43, y=360, width=185, alignment="left", font_size=9
    ),
    "records_state": FieldCoord(
        page=0, x=235, y=360, width=50, alignment="left", font_size=9
    ),
    "records_country": FieldCoord(
        page=0, x=292, y=360, width=130, alignment="left", font_size=9
    ),
    # P. Corporation's Telephone Number (label at rl_y≈376, value below)
    "phone": FieldCoord(
        page=0, x=436, y=360, width=140, alignment="left", font_size=9
    ),

    # --- Shareholders & Representative (Q-X) ---
    # Q. Total Shareholders (label at rl_y≈349, value below)
    "total_shareholders": FieldCoord(
        page=0, x=43, y=335, width=60, alignment="left", font_size=9
    ),
    # R. Total Nonresident Shareholders (label at rl_y≈349, value below)
    "nonresident_shareholders": FieldCoord(
        page=0, x=133, y=335, width=65, alignment="left", font_size=9
    ),

    # --- Page 1 header (top of page) ---
    # FEIN at top of Page 1
    "p2_fein": FieldCoord(
        page=1, x=44, y=755, width=160, alignment="left", font_size=9
    ),
    # Corporation Name at top of Page 1
    "p2_name": FieldCoord(
        page=1, x=210, y=755, width=365, alignment="left", font_size=9
    ),

    # --- Page 2 header (top of Schedule 7/8 page) ---
    "p3_fein": FieldCoord(
        page=2, x=44, y=755, width=160, alignment="left", font_size=9
    ),
    "p3_name": FieldCoord(
        page=2, x=210, y=755, width=365, alignment="left", font_size=9
    ),

    # --- PTET Election checkbox ---
    # "S Corporation elects to pay the tax at the entity level" (rl_y≈577)
    "ptet_election": FieldCoord(
        page=0, x=435, y=577, width=15, alignment="left", font_size=10
    ),

    # --- Extension checkbox ---
    "extension_checkbox": FieldCoord(
        page=0, x=437, y=601, width=15, alignment="left", font_size=10
    ),
}

# ---------------------------------------------------------------------------
# Schedule 1 — Computation of GA Taxable Income and Tax (Page 0)
# Amount column: right-aligned, x=442 to x=573
# ---------------------------------------------------------------------------
_S1_X = 442
_S1_W = 131

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
_S4_AX = 280
_S4_AW = 80
_S4_BX = 365
_S4_BW = 75
_S4_CX = 460
_S4_CW = 113

# ---------------------------------------------------------------------------
# Schedule 5 — Computation of Georgia Net Income (Page 1, lower-middle)
# Amount column: x=426 to x=575, right-aligned
# ---------------------------------------------------------------------------
_S5_X = 426
_S5_W = 149

# ---------------------------------------------------------------------------
# Schedule 6 — Total Income for GA Purposes (Page 1, bottom)
# ---------------------------------------------------------------------------
_S6_MAIN_X = 425
_S6_MAIN_W = 148
_S6_SUB_X = 289
_S6_SUB_W = 130
_S6_PORT_X = 424
_S6_PORT_W = 149

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
    "S1_1": FieldCoord(page=0, x=_S1_X, y=227, width=_S1_W),
    "S1_2": FieldCoord(page=0, x=_S1_X, y=215, width=_S1_W),
    "S1_3": FieldCoord(page=0, x=_S1_X, y=202, width=_S1_W),
    "S1_4": FieldCoord(page=0, x=_S1_X, y=190, width=_S1_W),
    "S1_5": FieldCoord(page=0, x=_S1_X, y=178, width=_S1_W),
    "S1_6": FieldCoord(page=0, x=_S1_X, y=167, width=_S1_W),
    "S1_7": FieldCoord(page=0, x=_S1_X, y=154, width=_S1_W),

    # ===== SCHEDULE 3 (Page 1) =====
    "S3_1": FieldCoord(page=1, x=_S3_X, y=648, width=_S3_W),
    "S3_2": FieldCoord(page=1, x=_S3_X, y=636, width=_S3_W),
    "S3_3": FieldCoord(page=1, x=_S3_X, y=624, width=_S3_W),
    "S3_4": FieldCoord(page=1, x=_S3_X, y=612, width=_S3_W),
    "S3_5": FieldCoord(page=1, x=_S3_X, y=600, width=_S3_W),
    "S3_6": FieldCoord(page=1, x=_S3_X, y=587, width=_S3_W),
    "S3_7": FieldCoord(page=1, x=_S3_X, y=575, width=_S3_W),

    # ===== SCHEDULE 4 (Page 1) — 3-column layout =====
    "S4_1a": FieldCoord(page=1, x=_S4_AX, y=525, width=_S4_AW),
    "S4_1b": FieldCoord(page=1, x=_S4_BX, y=525, width=_S4_BW),
    "S4_1c": FieldCoord(page=1, x=_S4_CX, y=525, width=_S4_CW),
    "S4_2a": FieldCoord(page=1, x=_S4_AX, y=513, width=_S4_AW),
    "S4_2b": FieldCoord(page=1, x=_S4_BX, y=513, width=_S4_BW),
    "S4_2c": FieldCoord(page=1, x=_S4_CX, y=513, width=_S4_CW),
    "S4_3a": FieldCoord(page=1, x=_S4_AX, y=501, width=_S4_AW),
    "S4_3b": FieldCoord(page=1, x=_S4_BX, y=501, width=_S4_BW),
    "S4_3c": FieldCoord(page=1, x=_S4_CX, y=501, width=_S4_CW),
    "S4_4a": FieldCoord(page=1, x=_S4_AX, y=489, width=_S4_AW),
    "S4_4b": FieldCoord(page=1, x=_S4_BX, y=489, width=_S4_BW),
    "S4_4c": FieldCoord(page=1, x=_S4_CX, y=489, width=_S4_CW),
    "S4_5a": FieldCoord(page=1, x=_S4_AX, y=477, width=_S4_AW),
    "S4_5b": FieldCoord(page=1, x=_S4_BX, y=477, width=_S4_BW),
    "S4_5c": FieldCoord(page=1, x=_S4_CX, y=477, width=_S4_CW),
    "S4_6a": FieldCoord(page=1, x=_S4_AX, y=464, width=_S4_AW),
    "S4_6b": FieldCoord(page=1, x=_S4_BX, y=464, width=_S4_BW),
    "S4_6c": FieldCoord(page=1, x=_S4_CX, y=464, width=_S4_CW),
    "S4_7a": FieldCoord(page=1, x=_S4_AX, y=453, width=_S4_AW),
    "S4_7b": FieldCoord(page=1, x=_S4_BX, y=453, width=_S4_BW),
    "S4_7c": FieldCoord(page=1, x=_S4_CX, y=453, width=_S4_CW),
    "S4_8a": FieldCoord(page=1, x=_S4_AX, y=441, width=_S4_AW),
    "S4_8b": FieldCoord(page=1, x=_S4_BX, y=441, width=_S4_BW),
    "S4_8c": FieldCoord(page=1, x=_S4_CX, y=441, width=_S4_CW),
    "S4_9a": FieldCoord(page=1, x=_S4_AX, y=428, width=_S4_AW),
    "S4_9b": FieldCoord(page=1, x=_S4_BX, y=428, width=_S4_BW),
    "S4_9c": FieldCoord(page=1, x=_S4_CX, y=428, width=_S4_CW),
    "S4_10a": FieldCoord(page=1, x=_S4_AX, y=417, width=_S4_AW),
    "S4_10b": FieldCoord(page=1, x=_S4_BX, y=417, width=_S4_BW),
    "S4_10c": FieldCoord(page=1, x=_S4_CX, y=417, width=_S4_CW),
    "S4_11a": FieldCoord(page=1, x=_S4_AX, y=406, width=_S4_AW),
    "S4_11b": FieldCoord(page=1, x=_S4_BX, y=406, width=_S4_BW),
    "S4_11c": FieldCoord(page=1, x=_S4_CX, y=406, width=_S4_CW),

    # ===== SCHEDULE 5 (Page 1) =====
    "S5_1": FieldCoord(page=1, x=_S5_X, y=371, width=_S5_W),
    "S5_2": FieldCoord(page=1, x=_S5_X, y=359, width=_S5_W),
    "S5_3": FieldCoord(page=1, x=_S5_X, y=347, width=_S5_W),
    "S5_4": FieldCoord(page=1, x=_S5_X, y=335, width=_S5_W),
    "S5_5": FieldCoord(page=1, x=_S5_X, y=322, width=_S5_W),
    "S5_6": FieldCoord(page=1, x=_S5_X, y=310, width=_S5_W),
    "S5_7": FieldCoord(page=1, x=_S5_X, y=298, width=_S5_W),

    # ===== SCHEDULE 6 (Page 1, bottom) =====
    "S6_1": FieldCoord(page=1, x=_S6_MAIN_X, y=262, width=_S6_MAIN_W),
    "S6_2": FieldCoord(page=1, x=_S6_MAIN_X, y=251, width=_S6_MAIN_W),
    "S6_3a": FieldCoord(page=1, x=_S6_SUB_X, y=239, width=_S6_SUB_W),
    "S6_3b": FieldCoord(page=1, x=_S6_SUB_X, y=228, width=_S6_SUB_W),
    "S6_3c": FieldCoord(page=1, x=_S6_MAIN_X, y=228, width=_S6_MAIN_W),
    "S6_4a": FieldCoord(page=1, x=_S6_PORT_X, y=203, width=_S6_PORT_W),
    "S6_4b": FieldCoord(page=1, x=_S6_PORT_X, y=191, width=_S6_PORT_W),
    "S6_4c": FieldCoord(page=1, x=_S6_PORT_X, y=180, width=_S6_PORT_W),
    "S6_4d": FieldCoord(page=1, x=_S6_PORT_X, y=167, width=_S6_PORT_W),
    "S6_4e": FieldCoord(page=1, x=_S6_PORT_X, y=156, width=_S6_PORT_W),
    "S6_4f": FieldCoord(page=1, x=_S6_PORT_X, y=144, width=_S6_PORT_W),
    "S6_5": FieldCoord(page=1, x=_S6_MAIN_X, y=132, width=_S6_MAIN_W),
    "S6_6": FieldCoord(page=1, x=_S6_MAIN_X, y=120, width=_S6_MAIN_W),
    "S6_7": FieldCoord(page=1, x=_S6_MAIN_X, y=108, width=_S6_MAIN_W),
    "S6_8": FieldCoord(page=1, x=_S6_MAIN_X, y=96, width=_S6_MAIN_W),
    "S6_9": FieldCoord(page=1, x=_S6_MAIN_X, y=83, width=_S6_MAIN_W),
    "S6_10": FieldCoord(page=1, x=_S6_MAIN_X, y=71, width=_S6_MAIN_W),
    "S6_11": FieldCoord(page=1, x=_S6_MAIN_X, y=58, width=_S6_MAIN_W),

    # ===== SCHEDULE 7 (Page 2) =====
    "S7_1": FieldCoord(page=2, x=_S7_X, y=647, width=_S7_W),
    "S7_2": FieldCoord(page=2, x=_S7_X, y=635, width=_S7_W),
    "S7_3": FieldCoord(page=2, x=_S7_X, y=623, width=_S7_W),
    "S7_4": FieldCoord(page=2, x=_S7_X, y=611, width=_S7_W),
    "S7_5": FieldCoord(page=2, x=_S7_X, y=599, width=_S7_W),
    "S7_6": FieldCoord(page=2, x=_S7_X, y=587, width=_S7_W),
    "S7_7": FieldCoord(page=2, x=_S7_X, y=575, width=_S7_W),
    "S7_8": FieldCoord(page=2, x=_S7_X, y=563, width=_S7_W),

    # ===== SCHEDULE 8 (Page 2) =====
    "S8_1": FieldCoord(page=2, x=_S8_X, y=538, width=_S8_W),
    "S8_2": FieldCoord(page=2, x=_S8_X, y=527, width=_S8_W),
    "S8_3": FieldCoord(page=2, x=_S8_X, y=515, width=_S8_W),
    "S8_4": FieldCoord(page=2, x=_S8_X, y=503, width=_S8_W),
    "S8_5": FieldCoord(page=2, x=_S8_X, y=491, width=_S8_W),
}
