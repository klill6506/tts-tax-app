"""
Field coordinate mappings for Form 7203 -- S Corporation Shareholder
Stock and Debt Basis Limitations (Rev. December 2022).

Coordinates are in PDF points (1 point = 1/72 inch).
Origin (0, 0) is the bottom-left corner of the page.
Page size: 612 x 792 points.

2-page form:
    Page 0: Header + Part I (Stock Basis, lines 1-15)
            + Part II Section A (Amount of Debt, lines 16-20)
    Page 1: Part II Section B (Adjustments to Debt Basis, lines 21-31)
            + Part II Section C (Gain on Repayment, lines 32-34)
            + Part III (Allowable Loss and Deduction Items, lines 35-47)

Part I has two amount columns:
    - Sub-column (lines 3a-3m, 8a-8c): right edge ~483
    - Main column (lines 1, 2, 4-7, 9-15): right edge ~572

Part II has 4 debt columns: (a) Debt 1, (b) Debt 2, (c) Debt 3, (d) Total

Part III has 5 columns: (a) Current year, (b) Carryover from prior year,
    (c) Allowed from stock basis, (d) Allowed from debt basis,
    (e) Carryover to next year

Coordinates calibrated via pdfplumber extraction from the 2025 IRS template.
"""

from .f1120s import FieldCoord


# ---- Header Fields ----

HEADER_FIELDS: dict[str, FieldCoord] = {
    # Shareholder info
    "taxpayer_name": FieldCoord(
        page=0, x=36, y=695, width=400, alignment="left", font_size=10,
    ),
    "taxpayer_ssn": FieldCoord(
        page=0, x=445, y=695, width=130, alignment="left", font_size=10,
    ),
    # S Corporation info
    "entity_name": FieldCoord(
        page=0, x=50, y=671, width=388, alignment="left", font_size=9,
    ),
    "entity_ein": FieldCoord(
        page=0, x=457, y=671, width=118, alignment="left", font_size=9,
    ),
    # Item C: Stock block
    "stock_block": FieldCoord(
        page=0, x=175, y=657, width=200, alignment="left", font_size=8,
    ),
}


# ---- Part I: Shareholder Stock Basis (page 0) ----
# Sub-column for lines 3a-3m, 8a-8c (right edge ~483)
_SUB_X = 480
_SUB_W = 45
# Main column for lines 1, 2, 4-7, 9-15 (right edge ~572)
_MAIN_X = 570
_MAIN_W = 68

# ---- Part II: Debt columns (pages 0-1) ----
# Column right edges for debt 1/2/3 and total
_DEBT_A_X = 354  # (a) Debt 1
_DEBT_B_X = 426  # (b) Debt 2
_DEBT_C_X = 498  # (c) Debt 3
_DEBT_D_X = 568  # (d) Total
_DEBT_W = 58

# ---- Part III: Loss limitation columns (page 1) ----
_P3_COL_A_X = 312   # (a) Current year losses
_P3_COL_B_X = 377   # (b) Carryover from prior year
_P3_COL_C_X = 442   # (c) Allowed from stock basis
_P3_COL_D_X = 507   # (d) Allowed from debt basis
_P3_COL_E_X = 572   # (e) Carryover to next year
_P3_W = 55


FIELD_MAP: dict[str, FieldCoord] = {
    # =====================================================================
    # Part I: Shareholder Stock Basis (page 0)
    # =====================================================================

    # Line 1: Stock basis at beginning of year
    "1": FieldCoord(page=0, x=_MAIN_X, y=598, width=_MAIN_W, alignment="right", font_size=9),
    # Line 2: Capital contributions / additional stock
    "2": FieldCoord(page=0, x=_MAIN_X, y=586, width=_MAIN_W, alignment="right", font_size=9),

    # Lines 3a-3m: Income items (sub-column)
    "3a": FieldCoord(page=0, x=_SUB_X, y=574, width=_SUB_W, alignment="right", font_size=8),
    "3b": FieldCoord(page=0, x=_SUB_X, y=562, width=_SUB_W, alignment="right", font_size=8),
    "3c": FieldCoord(page=0, x=_SUB_X, y=550, width=_SUB_W, alignment="right", font_size=8),
    "3d": FieldCoord(page=0, x=_SUB_X, y=538, width=_SUB_W, alignment="right", font_size=8),
    "3e": FieldCoord(page=0, x=_SUB_X, y=526, width=_SUB_W, alignment="right", font_size=8),
    "3f": FieldCoord(page=0, x=_SUB_X, y=514, width=_SUB_W, alignment="right", font_size=8),
    "3g": FieldCoord(page=0, x=_SUB_X, y=502, width=_SUB_W, alignment="right", font_size=8),
    "3h": FieldCoord(page=0, x=_SUB_X, y=490, width=_SUB_W, alignment="right", font_size=8),
    "3i": FieldCoord(page=0, x=_SUB_X, y=478, width=_SUB_W, alignment="right", font_size=8),
    "3j": FieldCoord(page=0, x=_SUB_X, y=466, width=_SUB_W, alignment="right", font_size=8),
    "3k": FieldCoord(page=0, x=_SUB_X, y=454, width=_SUB_W, alignment="right", font_size=8),
    "3l": FieldCoord(page=0, x=_SUB_X, y=442, width=_SUB_W, alignment="right", font_size=8),
    "3m": FieldCoord(page=0, x=_SUB_X, y=430, width=_SUB_W, alignment="right", font_size=8),

    # Line 4: Total of 3a-3m
    "4": FieldCoord(page=0, x=_MAIN_X, y=418, width=_MAIN_W, alignment="right", font_size=9),
    # Line 5: Stock basis before distributions (1 + 2 + 4)
    "5": FieldCoord(page=0, x=_MAIN_X, y=406, width=_MAIN_W, alignment="right", font_size=9),
    # Line 6: Distributions
    "6": FieldCoord(page=0, x=_MAIN_X, y=394, width=_MAIN_W, alignment="right", font_size=9),
    # Line 7: Stock basis after distributions
    "7": FieldCoord(page=0, x=_MAIN_X, y=346, width=_MAIN_W, alignment="right", font_size=9),

    # Lines 8a-8c: Non-deductible basis reduction items (sub-column)
    "8a": FieldCoord(page=0, x=_SUB_X, y=334, width=_SUB_W, alignment="right", font_size=8),
    "8b": FieldCoord(page=0, x=_SUB_X, y=322, width=_SUB_W, alignment="right", font_size=8),
    "8c": FieldCoord(page=0, x=_SUB_X, y=310, width=_SUB_W, alignment="right", font_size=8),

    # Line 9: Total of 8a-8c
    "9": FieldCoord(page=0, x=_MAIN_X, y=298, width=_MAIN_W, alignment="right", font_size=9),
    # Line 10: Stock basis before loss/deduction items (7 - 9)
    "10": FieldCoord(page=0, x=_MAIN_X, y=274, width=_MAIN_W, alignment="right", font_size=9),
    # Line 11: Allowable loss (from Part III line 47 col c)
    "11": FieldCoord(page=0, x=_MAIN_X, y=262, width=_MAIN_W, alignment="right", font_size=9),
    # Line 12: Debt basis restoration
    "12": FieldCoord(page=0, x=_MAIN_X, y=250, width=_MAIN_W, alignment="right", font_size=9),
    # Line 13: Other items that decrease stock basis
    "13": FieldCoord(page=0, x=_MAIN_X, y=238, width=_MAIN_W, alignment="right", font_size=9),
    # Line 14: Total of 11 + 12 + 13
    "14": FieldCoord(page=0, x=_MAIN_X, y=226, width=_MAIN_W, alignment="right", font_size=9),
    # Line 15: Stock basis at end of year (10 - 14)
    "15": FieldCoord(page=0, x=_MAIN_X, y=202, width=_MAIN_W, alignment="right", font_size=9),

    # =====================================================================
    # Part II Section A: Amount of Debt (page 0, lines 16-20)
    # Each line has 4 columns: (a) Debt 1, (b) Debt 2, (c) Debt 3, (d) Total
    # =====================================================================

    # Line 16: Loan balance at beginning
    "16a": FieldCoord(page=0, x=_DEBT_A_X, y=118, width=_DEBT_W, alignment="right", font_size=8),
    "16b": FieldCoord(page=0, x=_DEBT_B_X, y=118, width=_DEBT_W, alignment="right", font_size=8),
    "16c": FieldCoord(page=0, x=_DEBT_C_X, y=118, width=_DEBT_W, alignment="right", font_size=8),
    "16d": FieldCoord(page=0, x=_DEBT_D_X, y=118, width=_DEBT_W, alignment="right", font_size=8),

    # Line 17: Additional loans
    "17a": FieldCoord(page=0, x=_DEBT_A_X, y=106, width=_DEBT_W, alignment="right", font_size=8),
    "17b": FieldCoord(page=0, x=_DEBT_B_X, y=106, width=_DEBT_W, alignment="right", font_size=8),
    "17c": FieldCoord(page=0, x=_DEBT_C_X, y=106, width=_DEBT_W, alignment="right", font_size=8),
    "17d": FieldCoord(page=0, x=_DEBT_D_X, y=106, width=_DEBT_W, alignment="right", font_size=8),

    # Line 18: Loan balance before repayment (16 + 17)
    "18a": FieldCoord(page=0, x=_DEBT_A_X, y=94, width=_DEBT_W, alignment="right", font_size=8),
    "18b": FieldCoord(page=0, x=_DEBT_B_X, y=94, width=_DEBT_W, alignment="right", font_size=8),
    "18c": FieldCoord(page=0, x=_DEBT_C_X, y=94, width=_DEBT_W, alignment="right", font_size=8),
    "18d": FieldCoord(page=0, x=_DEBT_D_X, y=94, width=_DEBT_W, alignment="right", font_size=8),

    # Line 19: Principal repayments
    "19a": FieldCoord(page=0, x=_DEBT_A_X, y=70, width=_DEBT_W, alignment="right", font_size=8),
    "19b": FieldCoord(page=0, x=_DEBT_B_X, y=70, width=_DEBT_W, alignment="right", font_size=8),
    "19c": FieldCoord(page=0, x=_DEBT_C_X, y=70, width=_DEBT_W, alignment="right", font_size=8),
    "19d": FieldCoord(page=0, x=_DEBT_D_X, y=70, width=_DEBT_W, alignment="right", font_size=8),

    # Line 20: Loan balance at end (18 - 19)
    "20a": FieldCoord(page=0, x=_DEBT_A_X, y=47, width=_DEBT_W, alignment="right", font_size=8),
    "20b": FieldCoord(page=0, x=_DEBT_B_X, y=47, width=_DEBT_W, alignment="right", font_size=8),
    "20c": FieldCoord(page=0, x=_DEBT_C_X, y=47, width=_DEBT_W, alignment="right", font_size=8),
    "20d": FieldCoord(page=0, x=_DEBT_D_X, y=47, width=_DEBT_W, alignment="right", font_size=8),

    # =====================================================================
    # Part II Section B: Adjustments to Debt Basis (page 1, lines 21-31)
    # =====================================================================

    # Line 21: Debt basis at beginning
    "21a": FieldCoord(page=1, x=_DEBT_A_X, y=694, width=_DEBT_W, alignment="right", font_size=8),
    "21b": FieldCoord(page=1, x=_DEBT_B_X, y=694, width=_DEBT_W, alignment="right", font_size=8),
    "21c": FieldCoord(page=1, x=_DEBT_C_X, y=694, width=_DEBT_W, alignment="right", font_size=8),
    "21d": FieldCoord(page=1, x=_DEBT_D_X, y=694, width=_DEBT_W, alignment="right", font_size=8),

    # Line 22: Amount from line 17
    "22a": FieldCoord(page=1, x=_DEBT_A_X, y=682, width=_DEBT_W, alignment="right", font_size=8),
    "22b": FieldCoord(page=1, x=_DEBT_B_X, y=682, width=_DEBT_W, alignment="right", font_size=8),
    "22c": FieldCoord(page=1, x=_DEBT_C_X, y=682, width=_DEBT_W, alignment="right", font_size=8),
    "22d": FieldCoord(page=1, x=_DEBT_D_X, y=682, width=_DEBT_W, alignment="right", font_size=8),

    # Line 23: Debt basis restoration
    "23a": FieldCoord(page=1, x=_DEBT_A_X, y=670, width=_DEBT_W, alignment="right", font_size=8),
    "23b": FieldCoord(page=1, x=_DEBT_B_X, y=670, width=_DEBT_W, alignment="right", font_size=8),
    "23c": FieldCoord(page=1, x=_DEBT_C_X, y=670, width=_DEBT_W, alignment="right", font_size=8),
    "23d": FieldCoord(page=1, x=_DEBT_D_X, y=670, width=_DEBT_W, alignment="right", font_size=8),

    # Line 24: Debt basis before repayment (21 + 22 + 23)
    "24a": FieldCoord(page=1, x=_DEBT_A_X, y=658, width=_DEBT_W, alignment="right", font_size=8),
    "24b": FieldCoord(page=1, x=_DEBT_B_X, y=658, width=_DEBT_W, alignment="right", font_size=8),
    "24c": FieldCoord(page=1, x=_DEBT_C_X, y=658, width=_DEBT_W, alignment="right", font_size=8),
    "24d": FieldCoord(page=1, x=_DEBT_D_X, y=658, width=_DEBT_W, alignment="right", font_size=8),

    # Line 25: Ratio (line 24 / line 18)
    "25a": FieldCoord(page=1, x=_DEBT_A_X, y=646, width=_DEBT_W, alignment="right", font_size=8),
    "25b": FieldCoord(page=1, x=_DEBT_B_X, y=646, width=_DEBT_W, alignment="right", font_size=8),
    "25c": FieldCoord(page=1, x=_DEBT_C_X, y=646, width=_DEBT_W, alignment="right", font_size=8),
    "25d": FieldCoord(page=1, x=_DEBT_D_X, y=646, width=_DEBT_W, alignment="right", font_size=8),

    # Line 26: Nontaxable debt repayment (25 * 19)
    "26a": FieldCoord(page=1, x=_DEBT_A_X, y=634, width=_DEBT_W, alignment="right", font_size=8),
    "26b": FieldCoord(page=1, x=_DEBT_B_X, y=634, width=_DEBT_W, alignment="right", font_size=8),
    "26c": FieldCoord(page=1, x=_DEBT_C_X, y=634, width=_DEBT_W, alignment="right", font_size=8),
    "26d": FieldCoord(page=1, x=_DEBT_D_X, y=634, width=_DEBT_W, alignment="right", font_size=8),

    # Line 27: Debt basis before nondeductible expenses (24 - 26)
    "27a": FieldCoord(page=1, x=_DEBT_A_X, y=610, width=_DEBT_W, alignment="right", font_size=8),
    "27b": FieldCoord(page=1, x=_DEBT_B_X, y=610, width=_DEBT_W, alignment="right", font_size=8),
    "27c": FieldCoord(page=1, x=_DEBT_C_X, y=610, width=_DEBT_W, alignment="right", font_size=8),
    "27d": FieldCoord(page=1, x=_DEBT_D_X, y=610, width=_DEBT_W, alignment="right", font_size=8),

    # Line 28: Nondeductible expenses in excess of stock basis
    "28a": FieldCoord(page=1, x=_DEBT_A_X, y=586, width=_DEBT_W, alignment="right", font_size=8),
    "28b": FieldCoord(page=1, x=_DEBT_B_X, y=586, width=_DEBT_W, alignment="right", font_size=8),
    "28c": FieldCoord(page=1, x=_DEBT_C_X, y=586, width=_DEBT_W, alignment="right", font_size=8),
    "28d": FieldCoord(page=1, x=_DEBT_D_X, y=586, width=_DEBT_W, alignment="right", font_size=8),

    # Line 29: Debt basis before losses (27 - 28)
    "29a": FieldCoord(page=1, x=_DEBT_A_X, y=562, width=_DEBT_W, alignment="right", font_size=8),
    "29b": FieldCoord(page=1, x=_DEBT_B_X, y=562, width=_DEBT_W, alignment="right", font_size=8),
    "29c": FieldCoord(page=1, x=_DEBT_C_X, y=562, width=_DEBT_W, alignment="right", font_size=8),
    "29d": FieldCoord(page=1, x=_DEBT_D_X, y=562, width=_DEBT_W, alignment="right", font_size=8),

    # Line 30: Allowable losses in excess of stock basis (from Part III)
    "30a": FieldCoord(page=1, x=_DEBT_A_X, y=538, width=_DEBT_W, alignment="right", font_size=8),
    "30b": FieldCoord(page=1, x=_DEBT_B_X, y=538, width=_DEBT_W, alignment="right", font_size=8),
    "30c": FieldCoord(page=1, x=_DEBT_C_X, y=538, width=_DEBT_W, alignment="right", font_size=8),
    "30d": FieldCoord(page=1, x=_DEBT_D_X, y=538, width=_DEBT_W, alignment="right", font_size=8),

    # Line 31: Debt basis at end (29 - 30)
    "31a": FieldCoord(page=1, x=_DEBT_A_X, y=503, width=_DEBT_W, alignment="right", font_size=8),
    "31b": FieldCoord(page=1, x=_DEBT_B_X, y=503, width=_DEBT_W, alignment="right", font_size=8),
    "31c": FieldCoord(page=1, x=_DEBT_C_X, y=503, width=_DEBT_W, alignment="right", font_size=8),
    "31d": FieldCoord(page=1, x=_DEBT_D_X, y=503, width=_DEBT_W, alignment="right", font_size=8),

    # =====================================================================
    # Part II Section C: Gain on Repayment (page 1, lines 32-34)
    # =====================================================================

    "32a": FieldCoord(page=1, x=_DEBT_A_X, y=478, width=_DEBT_W, alignment="right", font_size=8),
    "32b": FieldCoord(page=1, x=_DEBT_B_X, y=478, width=_DEBT_W, alignment="right", font_size=8),
    "32c": FieldCoord(page=1, x=_DEBT_C_X, y=478, width=_DEBT_W, alignment="right", font_size=8),
    "32d": FieldCoord(page=1, x=_DEBT_D_X, y=478, width=_DEBT_W, alignment="right", font_size=8),

    "33a": FieldCoord(page=1, x=_DEBT_A_X, y=466, width=_DEBT_W, alignment="right", font_size=8),
    "33b": FieldCoord(page=1, x=_DEBT_B_X, y=466, width=_DEBT_W, alignment="right", font_size=8),
    "33c": FieldCoord(page=1, x=_DEBT_C_X, y=466, width=_DEBT_W, alignment="right", font_size=8),
    "33d": FieldCoord(page=1, x=_DEBT_D_X, y=466, width=_DEBT_W, alignment="right", font_size=8),

    "34a": FieldCoord(page=1, x=_DEBT_A_X, y=454, width=_DEBT_W, alignment="right", font_size=8),
    "34b": FieldCoord(page=1, x=_DEBT_B_X, y=454, width=_DEBT_W, alignment="right", font_size=8),
    "34c": FieldCoord(page=1, x=_DEBT_C_X, y=454, width=_DEBT_W, alignment="right", font_size=8),
    "34d": FieldCoord(page=1, x=_DEBT_D_X, y=454, width=_DEBT_W, alignment="right", font_size=8),

    # =====================================================================
    # Part III: Shareholder Allowable Loss and Deduction Items (page 1)
    # 5 columns: (a) current year, (b) carryover from prior,
    #            (c) from stock basis, (d) from debt basis,
    #            (e) carryover to next year
    # =====================================================================

    # Line 35: Ordinary business loss
    "35a": FieldCoord(page=1, x=_P3_COL_A_X, y=376, width=_P3_W, alignment="right", font_size=7),
    "35b": FieldCoord(page=1, x=_P3_COL_B_X, y=376, width=_P3_W, alignment="right", font_size=7),
    "35c": FieldCoord(page=1, x=_P3_COL_C_X, y=376, width=_P3_W, alignment="right", font_size=7),
    "35d": FieldCoord(page=1, x=_P3_COL_D_X, y=376, width=_P3_W, alignment="right", font_size=7),
    "35e": FieldCoord(page=1, x=_P3_COL_E_X, y=376, width=_P3_W, alignment="right", font_size=7),

    # Line 36: Net rental real estate loss
    "36a": FieldCoord(page=1, x=_P3_COL_A_X, y=364, width=_P3_W, alignment="right", font_size=7),
    "36b": FieldCoord(page=1, x=_P3_COL_B_X, y=364, width=_P3_W, alignment="right", font_size=7),
    "36c": FieldCoord(page=1, x=_P3_COL_C_X, y=364, width=_P3_W, alignment="right", font_size=7),
    "36d": FieldCoord(page=1, x=_P3_COL_D_X, y=364, width=_P3_W, alignment="right", font_size=7),
    "36e": FieldCoord(page=1, x=_P3_COL_E_X, y=364, width=_P3_W, alignment="right", font_size=7),

    # Line 37: Other net rental loss
    "37a": FieldCoord(page=1, x=_P3_COL_A_X, y=352, width=_P3_W, alignment="right", font_size=7),
    "37b": FieldCoord(page=1, x=_P3_COL_B_X, y=352, width=_P3_W, alignment="right", font_size=7),
    "37c": FieldCoord(page=1, x=_P3_COL_C_X, y=352, width=_P3_W, alignment="right", font_size=7),
    "37d": FieldCoord(page=1, x=_P3_COL_D_X, y=352, width=_P3_W, alignment="right", font_size=7),
    "37e": FieldCoord(page=1, x=_P3_COL_E_X, y=352, width=_P3_W, alignment="right", font_size=7),

    # Line 38: Net capital loss
    "38a": FieldCoord(page=1, x=_P3_COL_A_X, y=340, width=_P3_W, alignment="right", font_size=7),
    "38b": FieldCoord(page=1, x=_P3_COL_B_X, y=340, width=_P3_W, alignment="right", font_size=7),
    "38c": FieldCoord(page=1, x=_P3_COL_C_X, y=340, width=_P3_W, alignment="right", font_size=7),
    "38d": FieldCoord(page=1, x=_P3_COL_D_X, y=340, width=_P3_W, alignment="right", font_size=7),
    "38e": FieldCoord(page=1, x=_P3_COL_E_X, y=340, width=_P3_W, alignment="right", font_size=7),

    # Line 39: Net section 1231 loss
    "39a": FieldCoord(page=1, x=_P3_COL_A_X, y=328, width=_P3_W, alignment="right", font_size=7),
    "39b": FieldCoord(page=1, x=_P3_COL_B_X, y=328, width=_P3_W, alignment="right", font_size=7),
    "39c": FieldCoord(page=1, x=_P3_COL_C_X, y=328, width=_P3_W, alignment="right", font_size=7),
    "39d": FieldCoord(page=1, x=_P3_COL_D_X, y=328, width=_P3_W, alignment="right", font_size=7),
    "39e": FieldCoord(page=1, x=_P3_COL_E_X, y=328, width=_P3_W, alignment="right", font_size=7),

    # Line 40: Other loss
    "40a": FieldCoord(page=1, x=_P3_COL_A_X, y=316, width=_P3_W, alignment="right", font_size=7),
    "40b": FieldCoord(page=1, x=_P3_COL_B_X, y=316, width=_P3_W, alignment="right", font_size=7),
    "40c": FieldCoord(page=1, x=_P3_COL_C_X, y=316, width=_P3_W, alignment="right", font_size=7),
    "40d": FieldCoord(page=1, x=_P3_COL_D_X, y=316, width=_P3_W, alignment="right", font_size=7),
    "40e": FieldCoord(page=1, x=_P3_COL_E_X, y=316, width=_P3_W, alignment="right", font_size=7),

    # Line 41: Section 179 deductions
    "41a": FieldCoord(page=1, x=_P3_COL_A_X, y=304, width=_P3_W, alignment="right", font_size=7),
    "41b": FieldCoord(page=1, x=_P3_COL_B_X, y=304, width=_P3_W, alignment="right", font_size=7),
    "41c": FieldCoord(page=1, x=_P3_COL_C_X, y=304, width=_P3_W, alignment="right", font_size=7),
    "41d": FieldCoord(page=1, x=_P3_COL_D_X, y=304, width=_P3_W, alignment="right", font_size=7),
    "41e": FieldCoord(page=1, x=_P3_COL_E_X, y=304, width=_P3_W, alignment="right", font_size=7),

    # Line 42: Charitable contributions
    "42a": FieldCoord(page=1, x=_P3_COL_A_X, y=292, width=_P3_W, alignment="right", font_size=7),
    "42b": FieldCoord(page=1, x=_P3_COL_B_X, y=292, width=_P3_W, alignment="right", font_size=7),
    "42c": FieldCoord(page=1, x=_P3_COL_C_X, y=292, width=_P3_W, alignment="right", font_size=7),
    "42d": FieldCoord(page=1, x=_P3_COL_D_X, y=292, width=_P3_W, alignment="right", font_size=7),
    "42e": FieldCoord(page=1, x=_P3_COL_E_X, y=292, width=_P3_W, alignment="right", font_size=7),

    # Line 43: Investment interest expense
    "43a": FieldCoord(page=1, x=_P3_COL_A_X, y=280, width=_P3_W, alignment="right", font_size=7),
    "43b": FieldCoord(page=1, x=_P3_COL_B_X, y=280, width=_P3_W, alignment="right", font_size=7),
    "43c": FieldCoord(page=1, x=_P3_COL_C_X, y=280, width=_P3_W, alignment="right", font_size=7),
    "43d": FieldCoord(page=1, x=_P3_COL_D_X, y=280, width=_P3_W, alignment="right", font_size=7),
    "43e": FieldCoord(page=1, x=_P3_COL_E_X, y=280, width=_P3_W, alignment="right", font_size=7),

    # Line 44: Section 59(e)(2) expenditures
    "44a": FieldCoord(page=1, x=_P3_COL_A_X, y=268, width=_P3_W, alignment="right", font_size=7),
    "44b": FieldCoord(page=1, x=_P3_COL_B_X, y=268, width=_P3_W, alignment="right", font_size=7),
    "44c": FieldCoord(page=1, x=_P3_COL_C_X, y=268, width=_P3_W, alignment="right", font_size=7),
    "44d": FieldCoord(page=1, x=_P3_COL_D_X, y=268, width=_P3_W, alignment="right", font_size=7),
    "44e": FieldCoord(page=1, x=_P3_COL_E_X, y=268, width=_P3_W, alignment="right", font_size=7),

    # Line 45: Other deductions
    "45a": FieldCoord(page=1, x=_P3_COL_A_X, y=256, width=_P3_W, alignment="right", font_size=7),
    "45b": FieldCoord(page=1, x=_P3_COL_B_X, y=256, width=_P3_W, alignment="right", font_size=7),
    "45c": FieldCoord(page=1, x=_P3_COL_C_X, y=256, width=_P3_W, alignment="right", font_size=7),
    "45d": FieldCoord(page=1, x=_P3_COL_D_X, y=256, width=_P3_W, alignment="right", font_size=7),
    "45e": FieldCoord(page=1, x=_P3_COL_E_X, y=256, width=_P3_W, alignment="right", font_size=7),

    # Line 46: Foreign taxes paid or accrued
    "46a": FieldCoord(page=1, x=_P3_COL_A_X, y=244, width=_P3_W, alignment="right", font_size=7),
    "46b": FieldCoord(page=1, x=_P3_COL_B_X, y=244, width=_P3_W, alignment="right", font_size=7),
    "46c": FieldCoord(page=1, x=_P3_COL_C_X, y=244, width=_P3_W, alignment="right", font_size=7),
    "46d": FieldCoord(page=1, x=_P3_COL_D_X, y=244, width=_P3_W, alignment="right", font_size=7),
    "46e": FieldCoord(page=1, x=_P3_COL_E_X, y=244, width=_P3_W, alignment="right", font_size=7),

    # Line 47: Total (sum of 35-46 per column)
    "47a": FieldCoord(page=1, x=_P3_COL_A_X, y=221, width=_P3_W, alignment="right", font_size=7),
    "47b": FieldCoord(page=1, x=_P3_COL_B_X, y=221, width=_P3_W, alignment="right", font_size=7),
    "47c": FieldCoord(page=1, x=_P3_COL_C_X, y=221, width=_P3_W, alignment="right", font_size=7),
    "47d": FieldCoord(page=1, x=_P3_COL_D_X, y=221, width=_P3_W, alignment="right", font_size=7),
    "47e": FieldCoord(page=1, x=_P3_COL_E_X, y=221, width=_P3_W, alignment="right", font_size=7),
}
