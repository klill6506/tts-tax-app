"""
AcroForm field map for Schedule K-1 (Form 1120-S) — 2025 IRS fillable PDF.

Template: resources/irs_forms/2025/f1120ssk.pdf (114 AcroForm fields)

Layout (single page):
    Left half:  Part I (Corporation info) + Part II (Shareholder info)
    Right half: Part III — Lines 1-12 (left column) + Lines 13-17 (right column)

Lines 10, 12, 13, 15, 16, 17 have multiple code+amount rows.
We map the first row of each coded section since render_k1() only fills one entry.

Multi-line fields (corp name/address, shareholder name/address) accept
newline-separated values — the filler draws each line from the top of the field.
"""

from . import AcroField, FieldMap

_P = "topmostSubform[0].Page1[0]"
_H = f"{_P}.Header[0].ForCalendarYear[0]"
_L = f"{_P}.LeftCol[0]"
_R1 = f"{_P}.RightCol[0].Lines1-12[0]"
_R2 = f"{_P}.RightCol[0].Lines13-17[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP — Part I (Corporation) + Part II (Shareholder) + tax year
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    # Tax year (calendar year header)
    "tax_year_begin_month": AcroField(f"{_H}.f1_01[0]"),
    "tax_year_begin_year": AcroField(f"{_H}.f1_02[0]"),
    "tax_year_end_month": AcroField(f"{_H}.f1_03[0]"),
    "tax_year_end_day": AcroField(f"{_H}.f1_04[0]"),
    "tax_year_end_year": AcroField(f"{_H}.f1_05[0]"),

    # Part I — Corporation Information
    "corp_ein": AcroField(f"{_L}.f1_06[0]"),           # A — EIN
    "corp_name_address": AcroField(f"{_L}.f1_07[0]"),   # B — Name + address (multi-line)
    "irs_center": AcroField(f"{_L}.f1_08[0]"),          # C — IRS Center
    "corp_shares_boy": AcroField(f"{_L}.f1_09[0]"),     # D — Total shares, beginning
    "corp_shares_eoy": AcroField(f"{_L}.f1_10[0]"),     # D — Total shares, ending

    # Part II — Shareholder Information
    "sh_ssn": AcroField(f"{_L}.f1_11[0]"),              # E — SSN/TIN
    "sh_name_address": AcroField(f"{_L}.f1_12[0]"),     # F — Name + address (multi-line)
    "sh_loan_pct": AcroField(f"{_L}.f1_13[0]"),         # G — Loan repayment %
    "sh_ownership_pct": AcroField(f"{_L}.f1_14[0]"),    # G — Current year allocation %
    "sh_tax_shelter": AcroField(f"{_L}.f1_15[0]"),      # G — Tax shelter registration
    "sh_shares_boy": AcroField(f"{_L}.f1_17[0]"),       # H — Shares, beginning
    "sh_shares_eoy": AcroField(f"{_L}.f1_18[0]"),       # H — Shares, ending
    "sh_loans_boy": AcroField(f"{_L}.f1_19[0]"),        # I — Loans, beginning
    "sh_loans_eoy": AcroField(f"{_L}.f1_20[0]"),        # I — Loans, ending

    # Checkboxes at bottom of left half
    "chk_final_k1": AcroField(f"{_P}.c1_01[0]", field_type="checkbox"),
    "chk_amended_k1": AcroField(f"{_P}.c1_02[0]", field_type="checkbox"),
}

# ---------------------------------------------------------------------------
# FIELD_MAP — Part III: Shareholder's Share of Income, Deductions, etc.
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {
    # ---- Lines 1-9: Simple amount fields (left column) ----
    "1": AcroField(f"{_R1}.f1_21[0]", format="currency"),    # Ordinary business income
    "2": AcroField(f"{_R1}.f1_22[0]", format="currency"),    # Net rental real estate
    "3": AcroField(f"{_R1}.f1_23[0]", format="currency"),    # Other net rental
    "4": AcroField(f"{_R1}.f1_24[0]", format="currency"),    # Interest income
    "5a": AcroField(f"{_R1}.f1_25[0]", format="currency"),   # Ordinary dividends
    "5b": AcroField(f"{_R1}.f1_26[0]", format="currency"),   # Qualified dividends
    "6": AcroField(f"{_R1}.f1_27[0]", format="currency"),    # Royalties
    "7": AcroField(f"{_R1}.f1_28[0]", format="currency"),    # Net short-term capital gain
    "8a": AcroField(f"{_R1}.f1_29[0]", format="currency"),   # Net long-term capital gain
    "8b": AcroField(f"{_R1}.f1_30[0]", format="currency"),   # Collectibles (28%)
    "8c": AcroField(f"{_R1}.f1_31[0]", format="currency"),   # Unrecaptured section 1250
    "9": AcroField(f"{_R1}.f1_32[0]", format="currency"),    # Net section 1231 gain

    # ---- Line 10: Other income — code + amount (5 rows, we use row 1) ----
    "10_code": AcroField(f"{_R1}.f1_33[0]"),
    "10": AcroField(f"{_R1}.f1_34[0]", format="currency"),
    # Rows 2-5 for additional line 10 entries
    "10_code_2": AcroField(f"{_R1}.f1_35[0]"),
    "10_amt_2": AcroField(f"{_R1}.f1_36[0]", format="currency"),
    "10_code_3": AcroField(f"{_R1}.f1_37[0]"),
    "10_amt_3": AcroField(f"{_R1}.f1_38[0]", format="currency"),
    "10_code_4": AcroField(f"{_R1}.f1_39[0]"),
    "10_amt_4": AcroField(f"{_R1}.f1_40[0]", format="currency"),
    "10_code_5": AcroField(f"{_R1}.f1_41[0]"),
    "10_amt_5": AcroField(f"{_R1}.f1_42[0]", format="currency"),

    # ---- Line 11: Section 179 deduction ----
    "11": AcroField(f"{_R1}.f1_43[0]", format="currency"),

    # ---- Line 12: Other deductions — code + amount (8 rows, we use row 1) ----
    "12_code": AcroField(f"{_R1}.f1_44[0]"),
    "12": AcroField(f"{_R1}.f1_45[0]", format="currency"),
    "12_code_2": AcroField(f"{_R1}.f1_46[0]"),
    "12_amt_2": AcroField(f"{_R1}.f1_47[0]", format="currency"),
    "12_code_3": AcroField(f"{_R1}.f1_48[0]"),
    "12_amt_3": AcroField(f"{_R1}.f1_49[0]", format="currency"),
    "12_code_4": AcroField(f"{_R1}.f1_50[0]"),
    "12_amt_4": AcroField(f"{_R1}.f1_51[0]", format="currency"),
    "12_code_5": AcroField(f"{_R1}.f1_52[0]"),
    "12_amt_5": AcroField(f"{_R1}.f1_53[0]", format="currency"),
    "12_code_6": AcroField(f"{_R1}.f1_54[0]"),
    "12_amt_6": AcroField(f"{_R1}.f1_55[0]", format="currency"),
    "12_code_7": AcroField(f"{_R1}.f1_56[0]"),
    "12_amt_7": AcroField(f"{_R1}.f1_57[0]", format="currency"),
    "12_code_8": AcroField(f"{_R1}.f1_58[0]"),
    "12_amt_8": AcroField(f"{_R1}.f1_59[0]", format="currency"),

    # ---- Line 13: Credits — code + amount (5 rows) ----
    "13_code": AcroField(f"{_R2}.f1_60[0]"),
    "13": AcroField(f"{_R2}.f1_61[0]", format="currency"),
    "13_code_2": AcroField(f"{_R2}.f1_62[0]"),
    "13_amt_2": AcroField(f"{_R2}.f1_63[0]", format="currency"),
    "13_code_3": AcroField(f"{_R2}.f1_64[0]"),
    "13_amt_3": AcroField(f"{_R2}.f1_65[0]", format="currency"),
    "13_code_4": AcroField(f"{_R2}.f1_66[0]"),
    "13_amt_4": AcroField(f"{_R2}.f1_67[0]", format="currency"),
    "13_code_5": AcroField(f"{_R2}.f1_68[0]"),
    "13_amt_5": AcroField(f"{_R2}.f1_69[0]", format="currency"),

    # ---- Line 14: Self-employment earnings checkbox ----
    "14_chk": AcroField(f"{_R2}.c1_03[0]", field_type="checkbox"),

    # ---- Line 15: Alternative minimum tax items — code + amount (6 rows) ----
    "15_code": AcroField(f"{_R2}.f1_70[0]"),
    "15": AcroField(f"{_R2}.f1_71[0]", format="currency"),
    "15_code_2": AcroField(f"{_R2}.f1_72[0]"),
    "15_amt_2": AcroField(f"{_R2}.f1_73[0]", format="currency"),
    "15_code_3": AcroField(f"{_R2}.f1_74[0]"),
    "15_amt_3": AcroField(f"{_R2}.f1_75[0]", format="currency"),
    "15_code_4": AcroField(f"{_R2}.f1_76[0]"),
    "15_amt_4": AcroField(f"{_R2}.f1_77[0]", format="currency"),
    "15_code_5": AcroField(f"{_R2}.f1_78[0]"),
    "15_amt_5": AcroField(f"{_R2}.f1_79[0]", format="currency"),
    "15_code_6": AcroField(f"{_R2}.f1_80[0]"),
    "15_amt_6": AcroField(f"{_R2}.f1_81[0]", format="currency"),

    # ---- Line 16: Items affecting shareholder basis — code + amount (6 rows) ----
    "16_code_1": AcroField(f"{_R2}.f1_82[0]"),
    "16_amt_1": AcroField(f"{_R2}.f1_83[0]", format="currency"),
    "16_code_2": AcroField(f"{_R2}.f1_84[0]"),
    "16_amt_2": AcroField(f"{_R2}.f1_85[0]", format="currency"),
    "16_code_3": AcroField(f"{_R2}.f1_86[0]"),
    "16_amt_3": AcroField(f"{_R2}.f1_87[0]", format="currency"),
    "16_code_4": AcroField(f"{_R2}.f1_88[0]"),
    "16_amt_4": AcroField(f"{_R2}.f1_89[0]", format="currency"),
    "16_code_5": AcroField(f"{_R2}.f1_90[0]"),
    "16_amt_5": AcroField(f"{_R2}.f1_91[0]", format="currency"),
    "16_code_6": AcroField(f"{_R2}.f1_92[0]"),
    "16_amt_6": AcroField(f"{_R2}.f1_93[0]", format="currency"),

    # ---- Line 17: Other information — code + amount (8 rows) ----
    "17_code_1": AcroField(f"{_R2}.f1_94[0]"),
    "17_amt_1": AcroField(f"{_R2}.f1_95[0]", format="currency"),
    "17_code_2": AcroField(f"{_R2}.f1_96[0]"),
    "17_amt_2": AcroField(f"{_R2}.f1_97[0]", format="currency"),
    "17_code_3": AcroField(f"{_R2}.f1_98[0]"),
    "17_amt_3": AcroField(f"{_R2}.f1_99[0]", format="currency"),
    "17_code_4": AcroField(f"{_R2}.f1_100[0]"),
    "17_amt_4": AcroField(f"{_R2}.f1_101[0]", format="currency"),
    "17_code_5": AcroField(f"{_R2}.f1_102[0]"),
    "17_amt_5": AcroField(f"{_R2}.f1_103[0]", format="currency"),
    "17_code_6": AcroField(f"{_R2}.f1_104[0]"),
    "17_amt_6": AcroField(f"{_R2}.f1_105[0]", format="currency"),
    "17_code_7": AcroField(f"{_R2}.f1_106[0]"),
    "17_amt_7": AcroField(f"{_R2}.f1_107[0]", format="currency"),
    "17_code_8": AcroField(f"{_R2}.f1_108[0]"),
    "17_amt_8": AcroField(f"{_R2}.f1_109[0]", format="currency"),

    # Bottom-of-form checkboxes (right column)
    "chk_qualified_opportunity": AcroField(
        f"{_P}.RightCol[0].c1_04[0]", field_type="checkbox",
    ),
    "chk_at_risk": AcroField(
        f"{_P}.RightCol[0].c1_05[0]", field_type="checkbox",
    ),
}
