"""
AcroForm field map for IRS Form 7203 — S Corporation Shareholder Stock
and Debt Basis Limitations (Rev. December 2024).

Maps our internal line_number / header keys to the AcroForm field names
in the official IRS fillable PDF (f7203.pdf).

Cross-referenced from:
    - resources/irs_forms/2025/f7203.fields.json (188 AcroForm fields)
    - server/apps/tts_forms/coordinates/f7203.py (our coordinate map)

AcroForm field naming convention:
    - Text fields: f{page}_{seq}  (e.g., f1_07 = page 1, field 7)
    - Checkboxes:  c{page}_{seq}  (e.g., c1_1 = page 1, checkbox 1)
    - Full names:  topmostSubform[0].Page{n}[0].{field}[{idx}]
    - Pages in the PDF are 1-indexed (Page1 = our page 0)

PDF page structure (2 pages):
    Page 0 (Page1): Header (shareholder name, SSN, corp name, EIN, stock block)
                    + Item D checkboxes
                    + Part I: Shareholder Stock Basis (lines 1-15)
                    + Part II Section A: Amount of Debt (lines 16-20, 4 cols)
    Page 1 (Page2): Part II Section B: Adjustments to Debt Basis (lines 21-31)
                    + Section C: Gain on Repayment (lines 32-34)
                    + Part III: Allowable Loss/Deduction Items (lines 35-47, 5 cols)

Part I has two amount columns:
    - Sub-column (lines 3a-3m, 8a-8c): narrower fields (~410-481)
    - Main column (lines 1, 2, 4-7, 9-15): wider fields (~504-576)

Part II has 4 debt columns: (a) Debt 1, (b) Debt 2, (c) Debt 3, (d) Total

Part III has 5 columns: (a) Current year, (b) Carryover from prior year,
    (c) Allowed from stock basis, (d) Allowed from debt basis,
    (e) Carryover to next year
"""

from . import AcroField, FieldMap

# Short aliases for page prefixes
_P1 = "topmostSubform[0].Page1[0]"
_P2 = "topmostSubform[0].Page2[0]"

# Table sub-paths (Part II Section A on page 1)
_SA = f"{_P1}.Table_SectionA[0]"
# Table sub-paths (Part II Section B / C on page 2)
_SB = f"{_P2}.Table_SectionB[0]"
_SC = f"{_P2}.Table_SectionC[0]"
# Table sub-path (Part III on page 2)
_P3 = f"{_P2}.Table_Part3[0]"


# ============================================================================
# HEADER_MAP — Shareholder and entity info at top of page 0
# ============================================================================

HEADER_MAP: FieldMap = {
    # Shareholder info
    "taxpayer_name": AcroField(f"{_P1}.f1_01[0]"),          # Shareholder's name
    "taxpayer_ssn": AcroField(f"{_P1}.f1_02[0]"),           # SSN or TIN

    # S Corporation info
    "entity_name": AcroField(f"{_P1}.f1_03[0]"),            # S corporation name
    "entity_ein": AcroField(f"{_P1}.f1_04[0]"),             # EIN

    # Item C — Stock block(s) acquired or disposed of during year
    "stock_block": AcroField(f"{_P1}.f1_05[0]"),

    # Item D — Checkboxes (filing status: Initial, Final, Amended, etc.)
    "item_d_1": AcroField(f"{_P1}.c1_1[0]", field_type="checkbox"),
    "item_d_2": AcroField(f"{_P1}.c1_2[0]", field_type="checkbox"),
    "item_d_3": AcroField(f"{_P1}.c1_3[0]", field_type="checkbox"),
    "item_d_4": AcroField(f"{_P1}.c1_4[0]", field_type="checkbox"),
    "item_d_5": AcroField(f"{_P1}.c1_5[0]", field_type="checkbox"),
    "item_d_text": AcroField(f"{_P1}.f1_06[0]"),            # Text next to checkboxes
    "item_d_6": AcroField(f"{_P1}.c1_6[0]", field_type="checkbox"),

    # Part II Section A header — debt type checkboxes
    # Each debt has 2 checkboxes: direct loan vs. back-to-back loan
    "debt1_direct": AcroField(
        f"{_SA}.Header[0].aDebt1[0].c1_7[0]", field_type="checkbox",
    ),
    "debt1_backtoback": AcroField(
        f"{_SA}.Header[0].aDebt1[0].c1_7[1]", field_type="checkbox",
    ),
    "debt2_direct": AcroField(
        f"{_SA}.Header[0].bDebt2[0].c1_8[0]", field_type="checkbox",
    ),
    "debt2_backtoback": AcroField(
        f"{_SA}.Header[0].bDebt2[0].c1_8[1]", field_type="checkbox",
    ),
    "debt3_direct": AcroField(
        f"{_SA}.Header[0].cDebt3[0].c1_9[0]", field_type="checkbox",
    ),
    "debt3_backtoback": AcroField(
        f"{_SA}.Header[0].cDebt3[0].c1_9[1]", field_type="checkbox",
    ),
}


# ============================================================================
# FIELD_MAP — All line items across both pages
# ============================================================================

FIELD_MAP: FieldMap = {

    # =========================================================================
    # Part I: Shareholder Stock Basis (page 0)
    # =========================================================================

    # Line 1: Stock basis at beginning of corporation's tax year
    "1": AcroField(f"{_P1}.f1_07[0]", format="currency"),

    # Line 2: Increases — capital contributions and additional stock acquired
    "2": AcroField(f"{_P1}.f1_08[0]", format="currency"),

    # Lines 3a-3m: Income and gain items from Schedule K-1 (sub-column)
    "3a": AcroField(f"{_P1}.f1_09[0]", format="currency"),   # Ordinary business income
    "3b": AcroField(f"{_P1}.f1_10[0]", format="currency"),   # Net rental real estate income
    "3c": AcroField(f"{_P1}.f1_11[0]", format="currency"),   # Other net rental income
    "3d": AcroField(f"{_P1}.f1_12[0]", format="currency"),   # Interest income
    "3e": AcroField(f"{_P1}.f1_13[0]", format="currency"),   # Ordinary dividends
    "3f": AcroField(f"{_P1}.f1_14[0]", format="currency"),   # Royalties
    "3g": AcroField(f"{_P1}.f1_15[0]", format="currency"),   # Net short-term capital gain
    "3h": AcroField(f"{_P1}.f1_16[0]", format="currency"),   # Net long-term capital gain
    "3i": AcroField(f"{_P1}.f1_17[0]", format="currency"),   # Net section 1231 gain
    "3j": AcroField(f"{_P1}.f1_18[0]", format="currency"),   # Other income
    "3k": AcroField(f"{_P1}.f1_19[0]", format="currency"),   # Section 1374(b)(2) net recognized built-in gain
    "3l": AcroField(f"{_P1}.f1_20[0]", format="currency"),   # Excess depletion
    "3m": AcroField(f"{_P1}.f1_21[0]", format="currency"),   # Other items that increase stock basis

    # Line 4: Total of lines 3a through 3m
    "4": AcroField(f"{_P1}.f1_22[0]", format="currency"),

    # Line 5: Stock basis before distributions (line 1 + 2 + 4)
    "5": AcroField(f"{_P1}.f1_23[0]", format="currency"),

    # Line 6: Distributions (other than dividend distributions)
    "6": AcroField(f"{_P1}.f1_24[0]", format="currency"),

    # Line 7: Stock basis after distributions (line 5 - line 6, not below zero)
    "7": AcroField(f"{_P1}.f1_25[0]", format="currency"),

    # Lines 8a-8c: Nondeductible/noncapital basis reduction items (sub-column)
    "8a": AcroField(f"{_P1}.f1_26[0]", format="currency"),   # Nondeductible expenses
    "8b": AcroField(f"{_P1}.f1_27[0]", format="currency"),   # Nonseparately stated depletion
    "8c": AcroField(f"{_P1}.f1_28[0]", format="currency"),   # Oil and gas depletion

    # Line 9: Total of lines 8a through 8c
    "9": AcroField(f"{_P1}.f1_29[0]", format="currency"),

    # Line 10: Stock basis before loss and deduction items (line 7 - line 9)
    "10": AcroField(f"{_P1}.f1_30[0]", format="currency"),

    # Line 11: Allowable loss and deduction items (from Part III, line 47, col c)
    "11": AcroField(f"{_P1}.f1_31[0]", format="currency"),

    # Line 12: Debt basis restoration (if applicable)
    "12": AcroField(f"{_P1}.f1_32[0]", format="currency"),

    # Line 13: Other items that decrease stock basis
    "13": AcroField(f"{_P1}.f1_33[0]", format="currency"),

    # Line 14: Total of lines 11 + 12 + 13
    "14": AcroField(f"{_P1}.f1_34[0]", format="currency"),

    # Line 15: Stock basis at end of year (line 10 - line 14)
    "15": AcroField(f"{_P1}.f1_35[0]", format="currency"),

    # =========================================================================
    # Part II Section A: Amount of Each Loan from S Corporation (page 0)
    # 4 columns: (a) Debt 1, (b) Debt 2, (c) Debt 3, (d) Total
    # =========================================================================

    # Line 16: Loan balance at beginning of corporation's tax year
    "16a": AcroField(f"{_SA}.Line16[0].f1_36[0]", format="currency"),
    "16b": AcroField(f"{_SA}.Line16[0].f1_37[0]", format="currency"),
    "16c": AcroField(f"{_SA}.Line16[0].f1_38[0]", format="currency"),
    "16d": AcroField(f"{_SA}.Line16[0].f2_39[0]", format="currency"),

    # Line 17: Additional loans to shareholder during year
    "17a": AcroField(f"{_SA}.Line17[0].f1_40[0]", format="currency"),
    "17b": AcroField(f"{_SA}.Line17[0].f1_41[0]", format="currency"),
    "17c": AcroField(f"{_SA}.Line17[0].f1_42[0]", format="currency"),
    "17d": AcroField(f"{_SA}.Line17[0].f1_43[0]", format="currency"),

    # Line 18: Loan balance before repayment (line 16 + line 17)
    "18a": AcroField(f"{_SA}.Line18[0].f1_44[0]", format="currency"),
    "18b": AcroField(f"{_SA}.Line18[0].f1_45[0]", format="currency"),
    "18c": AcroField(f"{_SA}.Line18[0].f1_46[0]", format="currency"),
    "18d": AcroField(f"{_SA}.Line18[0].f1_47[0]", format="currency"),

    # Line 19: Principal repayment during year
    "19a": AcroField(f"{_SA}.Line19[0].f1_48[0]", format="currency"),
    "19b": AcroField(f"{_SA}.Line19[0].f1_49[0]", format="currency"),
    "19c": AcroField(f"{_SA}.Line19[0].f1_50[0]", format="currency"),
    "19d": AcroField(f"{_SA}.Line19[0].f1_51[0]", format="currency"),

    # Line 20: Loan balance at end of year (line 18 - line 19)
    "20a": AcroField(f"{_SA}.Line20[0].f1_52[0]", format="currency"),
    "20b": AcroField(f"{_SA}.Line20[0].f1_53[0]", format="currency"),
    "20c": AcroField(f"{_SA}.Line20[0].f1_54[0]", format="currency"),
    "20d": AcroField(f"{_SA}.Line20[0].f1_55[0]", format="currency"),

    # =========================================================================
    # Part II Section B: Adjustments to Debt Basis (page 1, lines 21-31)
    # 4 columns: (a) Debt 1, (b) Debt 2, (c) Debt 3, (d) Total
    # =========================================================================

    # Line 21: Debt basis at beginning of corporation's tax year
    "21a": AcroField(f"{_SB}.Line21[0].f2_01[0]", format="currency"),
    "21b": AcroField(f"{_SB}.Line21[0].f2_02[0]", format="currency"),
    "21c": AcroField(f"{_SB}.Line21[0].f2_03[0]", format="currency"),
    "21d": AcroField(f"{_SB}.Line21[0].f2_04[0]", format="currency"),

    # Line 22: Additional loans (amount from line 17)
    "22a": AcroField(f"{_SB}.Line22[0].f2_05[0]", format="currency"),
    "22b": AcroField(f"{_SB}.Line22[0].f2_06[0]", format="currency"),
    "22c": AcroField(f"{_SB}.Line22[0].f2_07[0]", format="currency"),
    "22d": AcroField(f"{_SB}.Line22[0].f2_08[0]", format="currency"),

    # Line 23: Debt basis restoration
    "23a": AcroField(f"{_SB}.Line23[0].f2_09[0]", format="currency"),
    "23b": AcroField(f"{_SB}.Line23[0].f2_10[0]", format="currency"),
    "23c": AcroField(f"{_SB}.Line23[0].f2_11[0]", format="currency"),
    "23d": AcroField(f"{_SB}.Line23[0].f2_12[0]", format="currency"),

    # Line 24: Debt basis before repayment reduction (line 21 + 22 + 23)
    "24a": AcroField(f"{_SB}.Line24[0].f2_13[0]", format="currency"),
    "24b": AcroField(f"{_SB}.Line24[0].f2_14[0]", format="currency"),
    "24c": AcroField(f"{_SB}.Line24[0].f2_15[0]", format="currency"),
    "24d": AcroField(f"{_SB}.Line24[0].f2_16[0]", format="currency"),

    # Line 25: Divide line 24 by line 18 (ratio / percentage)
    "25a": AcroField(f"{_SB}.Line25[0].f2_17[0]", format="percentage"),
    "25b": AcroField(f"{_SB}.Line25[0].f2_18[0]", format="percentage"),
    "25c": AcroField(f"{_SB}.Line25[0].f2_19[0]", format="percentage"),
    "25d": AcroField(f"{_SB}.Line25[0].f2_20[0]", format="percentage"),

    # Line 26: Nontaxable portion of debt repayment (line 25 * line 19)
    "26a": AcroField(f"{_SB}.Line26[0].f2_21[0]", format="currency"),
    "26b": AcroField(f"{_SB}.Line26[0].f2_22[0]", format="currency"),
    "26c": AcroField(f"{_SB}.Line26[0].f2_23[0]", format="currency"),
    "26d": AcroField(f"{_SB}.Line26[0].f2_24[0]", format="currency"),

    # Line 27: Debt basis before nondeductible expenses (line 24 - line 26)
    "27a": AcroField(f"{_SB}.Line27[0].f2_25[0]", format="currency"),
    "27b": AcroField(f"{_SB}.Line27[0].f2_26[0]", format="currency"),
    "27c": AcroField(f"{_SB}.Line27[0].f2_27[0]", format="currency"),
    "27d": AcroField(f"{_SB}.Line27[0].f2_28[0]", format="currency"),

    # Line 28: Nondeductible expenses in excess of stock basis
    "28a": AcroField(f"{_SB}.Line28[0].f2_29[0]", format="currency"),
    "28b": AcroField(f"{_SB}.Line28[0].f2_30[0]", format="currency"),
    "28c": AcroField(f"{_SB}.Line28[0].f2_31[0]", format="currency"),
    "28d": AcroField(f"{_SB}.Line28[0].f2_32[0]", format="currency"),

    # Line 29: Debt basis before losses and deduction items (line 27 - line 28)
    "29a": AcroField(f"{_SB}.Line29[0].f2_33[0]", format="currency"),
    "29b": AcroField(f"{_SB}.Line29[0].f2_34[0]", format="currency"),
    "29c": AcroField(f"{_SB}.Line29[0].f2_35[0]", format="currency"),
    "29d": AcroField(f"{_SB}.Line29[0].f2_36[0]", format="currency"),

    # Line 30: Allowable losses in excess of stock basis (from Part III)
    "30a": AcroField(f"{_SB}.Line30[0].f2_37[0]", format="currency"),
    "30b": AcroField(f"{_SB}.Line30[0].f2_38[0]", format="currency"),
    "30c": AcroField(f"{_SB}.Line30[0].f2_39[0]", format="currency"),
    "30d": AcroField(f"{_SB}.Line30[0].f2_40[0]", format="currency"),

    # Line 31: Debt basis at end of year (line 29 - line 30)
    "31a": AcroField(f"{_SB}.Line31[0].f2_41[0]", format="currency"),
    "31b": AcroField(f"{_SB}.Line31[0].f2_42[0]", format="currency"),
    "31c": AcroField(f"{_SB}.Line31[0].f2_43[0]", format="currency"),
    "31d": AcroField(f"{_SB}.Line31[0].f2_44[0]", format="currency"),

    # =========================================================================
    # Part II Section C: Gain on Loan Repayment (page 1, lines 32-34)
    # 4 columns: (a) Debt 1, (b) Debt 2, (c) Debt 3, (d) Total
    # =========================================================================

    # Line 32: Debt repayment in excess of debt basis (line 19 - line 26)
    "32a": AcroField(f"{_SC}.Line32[0].f2_45[0]", format="currency"),
    "32b": AcroField(f"{_SC}.Line32[0].f2_46[0]", format="currency"),
    "32c": AcroField(f"{_SC}.Line32[0].f2_47[0]", format="currency"),
    "32d": AcroField(f"{_SC}.Line32[0].f2_48[0]", format="currency"),

    # Line 33: Face amount of loan(s) at beginning of year
    "33a": AcroField(f"{_SC}.Line33[0].f2_49[0]", format="currency"),
    "33b": AcroField(f"{_SC}.Line33[0].f2_50[0]", format="currency"),
    "33c": AcroField(f"{_SC}.Line33[0].f2_51[0]", format="currency"),
    "33d": AcroField(f"{_SC}.Line33[0].f2_52[0]", format="currency"),

    # Line 34: Gain recognized on loan repayment
    "34a": AcroField(f"{_SC}.Line34[0].f2_53[0]", format="currency"),
    "34b": AcroField(f"{_SC}.Line34[0].f2_54[0]", format="currency"),
    "34c": AcroField(f"{_SC}.Line34[0].f2_55[0]", format="currency"),
    "34d": AcroField(f"{_SC}.Line34[0].f2_56[0]", format="currency"),

    # =========================================================================
    # Part III: Shareholder Allowable Loss and Deduction Items (page 1)
    # 5 columns: (a) Current year losses, (b) Carryover from prior year,
    #            (c) Allowed from stock basis, (d) Allowed from debt basis,
    #            (e) Carryover to next year
    # =========================================================================

    # Line 35: Ordinary business loss
    "35a": AcroField(f"{_P3}.Line35[0].f2_57[0]", format="currency"),
    "35b": AcroField(f"{_P3}.Line35[0].f2_58[0]", format="currency"),
    "35c": AcroField(f"{_P3}.Line35[0].f2_59[0]", format="currency"),
    "35d": AcroField(f"{_P3}.Line35[0].f2_60[0]", format="currency"),
    "35e": AcroField(f"{_P3}.Line35[0].f2_61[0]", format="currency"),

    # Line 36: Net rental real estate loss
    "36a": AcroField(f"{_P3}.Line36[0].f2_62[0]", format="currency"),
    "36b": AcroField(f"{_P3}.Line36[0].f2_63[0]", format="currency"),
    "36c": AcroField(f"{_P3}.Line36[0].f2_64[0]", format="currency"),
    "36d": AcroField(f"{_P3}.Line36[0].f2_65[0]", format="currency"),
    "36e": AcroField(f"{_P3}.Line36[0].f2_66[0]", format="currency"),

    # Line 37: Other net rental loss
    "37a": AcroField(f"{_P3}.Line37[0].f2_67[0]", format="currency"),
    "37b": AcroField(f"{_P3}.Line37[0].f2_68[0]", format="currency"),
    "37c": AcroField(f"{_P3}.Line37[0].f2_69[0]", format="currency"),
    "37d": AcroField(f"{_P3}.Line37[0].f2_70[0]", format="currency"),
    "37e": AcroField(f"{_P3}.Line37[0].f2_71[0]", format="currency"),

    # Line 38: Net short-term capital loss
    "38a": AcroField(f"{_P3}.Line38[0].f2_72[0]", format="currency"),
    "38b": AcroField(f"{_P3}.Line38[0].f2_73[0]", format="currency"),
    "38c": AcroField(f"{_P3}.Line38[0].f2_74[0]", format="currency"),
    "38d": AcroField(f"{_P3}.Line38[0].f2_75[0]", format="currency"),
    "38e": AcroField(f"{_P3}.Line38[0].f2_76[0]", format="currency"),

    # Line 39: Net long-term capital loss
    "39a": AcroField(f"{_P3}.Line39[0].f2_77[0]", format="currency"),
    "39b": AcroField(f"{_P3}.Line39[0].f2_78[0]", format="currency"),
    "39c": AcroField(f"{_P3}.Line39[0].f2_79[0]", format="currency"),
    "39d": AcroField(f"{_P3}.Line39[0].f2_80[0]", format="currency"),
    "39e": AcroField(f"{_P3}.Line39[0].f2_81[0]", format="currency"),

    # Line 40: Net section 1231 loss
    "40a": AcroField(f"{_P3}.Line40[0].f2_82[0]", format="currency"),
    "40b": AcroField(f"{_P3}.Line40[0].f2_83[0]", format="currency"),
    "40c": AcroField(f"{_P3}.Line40[0].f2_84[0]", format="currency"),
    "40d": AcroField(f"{_P3}.Line40[0].f2_85[0]", format="currency"),
    "40e": AcroField(f"{_P3}.Line40[0].f2_86[0]", format="currency"),

    # Line 41: Other losses
    # Note: IRS PDF skips f2_89 in the field numbering
    "41a": AcroField(f"{_P3}.Line41[0].f2_87[0]", format="currency"),
    "41b": AcroField(f"{_P3}.Line41[0].f2_88[0]", format="currency"),
    "41c": AcroField(f"{_P3}.Line41[0].f2_90[0]", format="currency"),
    "41d": AcroField(f"{_P3}.Line41[0].f2_91[0]", format="currency"),
    "41e": AcroField(f"{_P3}.Line41[0].f2_92[0]", format="currency"),

    # Line 42: Section 179 deductions
    "42a": AcroField(f"{_P3}.Line42[0].f2_93[0]", format="currency"),
    "42b": AcroField(f"{_P3}.Line42[0].f2_94[0]", format="currency"),
    "42c": AcroField(f"{_P3}.Line42[0].f2_95[0]", format="currency"),
    "42d": AcroField(f"{_P3}.Line42[0].f2_96[0]", format="currency"),
    "42e": AcroField(f"{_P3}.Line42[0].f2_97[0]", format="currency"),

    # Line 43: Charitable contributions
    "43a": AcroField(f"{_P3}.Line43[0].f2_98[0]", format="currency"),
    "43b": AcroField(f"{_P3}.Line43[0].f2_99[0]", format="currency"),
    "43c": AcroField(f"{_P3}.Line43[0].f2_100[0]", format="currency"),
    "43d": AcroField(f"{_P3}.Line43[0].f2_101[0]", format="currency"),
    "43e": AcroField(f"{_P3}.Line43[0].f2_102[0]", format="currency"),

    # Line 44: Investment interest expense
    "44a": AcroField(f"{_P3}.Line44[0].f2_103[0]", format="currency"),
    "44b": AcroField(f"{_P3}.Line44[0].f2_104[0]", format="currency"),
    "44c": AcroField(f"{_P3}.Line44[0].f2_105[0]", format="currency"),
    "44d": AcroField(f"{_P3}.Line44[0].f2_106[0]", format="currency"),
    "44e": AcroField(f"{_P3}.Line44[0].f2_107[0]", format="currency"),

    # Line 45: Section 59(e)(2) expenditures
    "45a": AcroField(f"{_P3}.Line45[0].f2_108[0]", format="currency"),
    "45b": AcroField(f"{_P3}.Line45[0].f2_109[0]", format="currency"),
    "45c": AcroField(f"{_P3}.Line45[0].f2_110[0]", format="currency"),
    "45d": AcroField(f"{_P3}.Line45[0].f2_111[0]", format="currency"),
    "45e": AcroField(f"{_P3}.Line45[0].f2_112[0]", format="currency"),

    # Line 46: Foreign taxes paid or accrued
    "46a": AcroField(f"{_P3}.Line46[0].f2_113[0]", format="currency"),
    "46b": AcroField(f"{_P3}.Line46[0].f2_114[0]", format="currency"),
    "46c": AcroField(f"{_P3}.Line46[0].f2_115[0]", format="currency"),
    "46d": AcroField(f"{_P3}.Line46[0].f2_116[0]", format="currency"),
    "46e": AcroField(f"{_P3}.Line46[0].f2_117[0]", format="currency"),

    # Line 47: Total (sum of lines 35-46 per column)
    "47a": AcroField(f"{_P3}.Line47[0].f2_118[0]", format="currency"),
    "47b": AcroField(f"{_P3}.Line47[0].f2_119[0]", format="currency"),
    "47c": AcroField(f"{_P3}.Line47[0].f2_120[0]", format="currency"),
    "47d": AcroField(f"{_P3}.Line47[0].f2_121[0]", format="currency"),
    "47e": AcroField(f"{_P3}.Line47[0].f2_122[0]", format="currency"),
}
