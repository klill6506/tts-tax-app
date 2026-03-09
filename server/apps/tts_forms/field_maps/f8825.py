"""
AcroForm field map for Form 8825 — Rental Real Estate Income and Expenses
of a Partnership or an S Corporation (2025 fillable PDF).

Template: resources/irs_forms/2025/f8825.pdf (221 AcroForm fields, 2 pages)

Page 1: Properties A-D — descriptors (line 1) + expenses (lines 2-19) + summary (20-23)
Page 2: Properties E-H — descriptors (line 1) + expenses (lines 2-19)

Key naming convention:
    Property descriptors: 1_{slot}_desc, 1_{slot}_addr, 1_{slot}_type, etc.
    Expense lines:        {line}_{slot}  (e.g., "2a_A", "3_B", "14_C")
    Summary lines:        20a, 20b, 21, 22a, 22b_desc_1, 22b_amt_1, 23

IMPORTANT: f1_99 appears twice in the PDF (Line 14 col A and Line 19 col A).
Full AcroForm paths are used throughout to disambiguate.
"""

from . import AcroField, FieldMap

# ---------------------------------------------------------------------------
# Path prefixes
# ---------------------------------------------------------------------------
_P1 = "topmostSubform[0].Page1[0]"
_T1 = f"{_P1}.Table_Line1[0]"      # Property descriptors A-D
_E1 = f"{_P1}.Table_Lines2-17[0]"   # Expense lines, properties A-D

_P2 = "topmostSubform[0].Page2[0]"
_T2 = f"{_P2}.Table_Line1[0]"      # Property descriptors E-H
_E2 = f"{_P2}.Table_Lines2-17[0]"   # Expense lines, properties E-H

# ---------------------------------------------------------------------------
# HEADER_MAP — Entity identification (page 1 top)
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    "entity_name": AcroField(f"{_P1}.f1_1[0]"),   # Name of entity
    "ein": AcroField(f"{_P1}.f1_2[0]"),            # EIN
}

# ---------------------------------------------------------------------------
# FIELD_MAP — All 219 remaining fields
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {
    # ===================================================================
    # PAGE 1 — Properties A-D
    # ===================================================================

    # -------------------------------------------------------------------
    # Line 1: Property descriptors (Table_Line1, rows A-D)
    # Each row: description, address, type, fair rental days, personal days
    # -------------------------------------------------------------------

    # Row A (f1_3 through f1_7)
    "1_A_desc": AcroField(f"{_T1}.RowA[0].Col_a[0].f1_3[0]"),                     # (a) Address
    "1_A_addr": AcroField(f"{_T1}.RowA[0].Col_b[0].f1_4[0]"),                     # (b) Type code 1-8
    "1_A_type": AcroField(f"{_T1}.RowA[0].Col_c[0].f1_5[0]"),                     # (c) Type code A-I
    "1_A_fair_days": AcroField(f"{_T1}.RowA[0].Col_d[0].f1_6[0]", format="integer"),   # (d) Fair rental days
    "1_A_personal_days": AcroField(f"{_T1}.RowA[0].Col_e[0].f1_7[0]", format="integer"),  # (e) Personal use days

    # Row B (f1_8 through f1_12)
    "1_B_desc": AcroField(f"{_T1}.RowB[0].Col_a[0].f1_8[0]"),
    "1_B_addr": AcroField(f"{_T1}.RowB[0].Col_b[0].f1_9[0]"),
    "1_B_type": AcroField(f"{_T1}.RowB[0].Col_c[0].f1_10[0]"),
    "1_B_fair_days": AcroField(f"{_T1}.RowB[0].Col_d[0].f1_11[0]", format="integer"),
    "1_B_personal_days": AcroField(f"{_T1}.RowB[0].Col_e[0].f1_12[0]", format="integer"),

    # Row C (f1_13 through f1_17)
    "1_C_desc": AcroField(f"{_T1}.RowC[0].Col_a[0].f1_13[0]"),
    "1_C_addr": AcroField(f"{_T1}.RowC[0].Col_b[0].f1_14[0]"),
    "1_C_type": AcroField(f"{_T1}.RowC[0].Col_c[0].f1_15[0]"),
    "1_C_fair_days": AcroField(f"{_T1}.RowC[0].Col_d[0].f1_16[0]", format="integer"),
    "1_C_personal_days": AcroField(f"{_T1}.RowC[0].Col_e[0].f1_17[0]", format="integer"),

    # Row D (f1_18 through f1_22)
    "1_D_desc": AcroField(f"{_T1}.RowD[0].Col_a[0].f1_18[0]"),
    "1_D_addr": AcroField(f"{_T1}.RowD[0].Col_b[0].f1_19[0]"),
    "1_D_type": AcroField(f"{_T1}.RowD[0].Col_c[0].f1_20[0]"),
    "1_D_fair_days": AcroField(f"{_T1}.RowD[0].Col_d[0].f1_21[0]", format="integer"),
    "1_D_personal_days": AcroField(f"{_T1}.RowD[0].Col_e[0].f1_22[0]", format="integer"),

    # -------------------------------------------------------------------
    # Lines 2-19: Expense amounts for properties A-D (4 cols each)
    # -------------------------------------------------------------------

    # Line 2a — Advertising (f1_23 through f1_26)
    "2a_A": AcroField(f"{_E1}.Line2a[0].f1_23[0]", format="currency"),
    "2a_B": AcroField(f"{_E1}.Line2a[0].f1_24[0]", format="currency"),
    "2a_C": AcroField(f"{_E1}.Line2a[0].f1_25[0]", format="currency"),
    "2a_D": AcroField(f"{_E1}.Line2a[0].f1_26[0]", format="currency"),

    # Line 2b — Auto and travel (f1_27 through f1_30)
    "2b_A": AcroField(f"{_E1}.Line2b[0].f1_27[0]", format="currency"),
    "2b_B": AcroField(f"{_E1}.Line2b[0].f1_28[0]", format="currency"),
    "2b_C": AcroField(f"{_E1}.Line2b[0].f1_29[0]", format="currency"),
    "2b_D": AcroField(f"{_E1}.Line2b[0].f1_30[0]", format="currency"),

    # Line 2c — Cleaning and maintenance (f1_31 through f1_34)
    "2c_A": AcroField(f"{_E1}.Line2c[0].f1_31[0]", format="currency"),
    "2c_B": AcroField(f"{_E1}.Line2c[0].f1_32[0]", format="currency"),
    "2c_C": AcroField(f"{_E1}.Line2c[0].f1_33[0]", format="currency"),
    "2c_D": AcroField(f"{_E1}.Line2c[0].f1_34[0]", format="currency"),

    # Line 3 — Commissions (f1_35 through f1_38)
    "3_A": AcroField(f"{_E1}.Line3[0].f1_35[0]", format="currency"),
    "3_B": AcroField(f"{_E1}.Line3[0].f1_36[0]", format="currency"),
    "3_C": AcroField(f"{_E1}.Line3[0].f1_37[0]", format="currency"),
    "3_D": AcroField(f"{_E1}.Line3[0].f1_38[0]", format="currency"),

    # Line 4 — Insurance (f1_39 through f1_42)
    "4_A": AcroField(f"{_E1}.Line4[0].f1_39[0]", format="currency"),
    "4_B": AcroField(f"{_E1}.Line4[0].f1_40[0]", format="currency"),
    "4_C": AcroField(f"{_E1}.Line4[0].f1_41[0]", format="currency"),
    "4_D": AcroField(f"{_E1}.Line4[0].f1_42[0]", format="currency"),

    # Line 5 — Legal and other professional fees (f1_43 through f1_46)
    "5_A": AcroField(f"{_E1}.Line5[0].f1_43[0]", format="currency"),
    "5_B": AcroField(f"{_E1}.Line5[0].f1_44[0]", format="currency"),
    "5_C": AcroField(f"{_E1}.Line5[0].f1_45[0]", format="currency"),
    "5_D": AcroField(f"{_E1}.Line5[0].f1_46[0]", format="currency"),

    # Line 6 — Interest (f1_47 through f1_50)
    "6_A": AcroField(f"{_E1}.Line6[0].f1_47[0]", format="currency"),
    "6_B": AcroField(f"{_E1}.Line6[0].f1_48[0]", format="currency"),
    "6_C": AcroField(f"{_E1}.Line6[0].f1_49[0]", format="currency"),
    "6_D": AcroField(f"{_E1}.Line6[0].f1_50[0]", format="currency"),

    # Line 7 — Repairs (f1_51 through f1_54)
    "7_A": AcroField(f"{_E1}.Line7[0].f1_51[0]", format="currency"),
    "7_B": AcroField(f"{_E1}.Line7[0].f1_52[0]", format="currency"),
    "7_C": AcroField(f"{_E1}.Line7[0].f1_53[0]", format="currency"),
    "7_D": AcroField(f"{_E1}.Line7[0].f1_54[0]", format="currency"),

    # Line 8 — Taxes (f1_55 through f1_58)
    "8_A": AcroField(f"{_E1}.Line8[0].f1_55[0]", format="currency"),
    "8_B": AcroField(f"{_E1}.Line8[0].f1_56[0]", format="currency"),
    "8_C": AcroField(f"{_E1}.Line8[0].f1_57[0]", format="currency"),
    "8_D": AcroField(f"{_E1}.Line8[0].f1_58[0]", format="currency"),

    # Line 9 — Utilities (f1_59 through f1_62)
    "9_A": AcroField(f"{_E1}.Line9[0].f1_59[0]", format="currency"),
    "9_B": AcroField(f"{_E1}.Line9[0].f1_60[0]", format="currency"),
    "9_C": AcroField(f"{_E1}.Line9[0].f1_61[0]", format="currency"),
    "9_D": AcroField(f"{_E1}.Line9[0].f1_62[0]", format="currency"),

    # Line 10 — Wages and salaries (f1_63 through f1_66)
    "10_A": AcroField(f"{_E1}.Line10[0].f1_63[0]", format="currency"),
    "10_B": AcroField(f"{_E1}.Line10[0].f1_64[0]", format="currency"),
    "10_C": AcroField(f"{_E1}.Line10[0].f1_65[0]", format="currency"),
    "10_D": AcroField(f"{_E1}.Line10[0].f1_66[0]", format="currency"),

    # Line 11 — Depreciation (f1_67 through f1_70)
    "11_A": AcroField(f"{_E1}.Line11[0].f1_67[0]", format="currency"),
    "11_B": AcroField(f"{_E1}.Line11[0].f1_68[0]", format="currency"),
    "11_C": AcroField(f"{_E1}.Line11[0].f1_69[0]", format="currency"),
    "11_D": AcroField(f"{_E1}.Line11[0].f1_70[0]", format="currency"),

    # Line 12 — Other (describe) (f1_71 through f1_74)
    "12_A": AcroField(f"{_E1}.Line12[0].f1_71[0]", format="currency"),
    "12_B": AcroField(f"{_E1}.Line12[0].f1_72[0]", format="currency"),
    "12_C": AcroField(f"{_E1}.Line12[0].f1_73[0]", format="currency"),
    "12_D": AcroField(f"{_E1}.Line12[0].f1_74[0]", format="currency"),

    # Line 13 — Total expenses for each property (f1_75 through f1_78)
    "13_A": AcroField(f"{_E1}.Line13[0].f1_75[0]", format="currency"),
    "13_B": AcroField(f"{_E1}.Line13[0].f1_76[0]", format="currency"),
    "13_C": AcroField(f"{_E1}.Line13[0].f1_77[0]", format="currency"),
    "13_D": AcroField(f"{_E1}.Line13[0].f1_78[0]", format="currency"),

    # Line 14 — Rents received for each property
    # NOTE: f1_99 is duplicated in the PDF. Use full path to disambiguate.
    "14_A": AcroField(f"{_E1}.Line14[0].f1_99[0]", format="currency"),
    "14_B": AcroField(f"{_E1}.Line14[0].f1_80[0]", format="currency"),
    "14_C": AcroField(f"{_E1}.Line14[0].f1_81[0]", format="currency"),
    "14_D": AcroField(f"{_E1}.Line14[0].f1_82[0]", format="currency"),

    # Line 15 — Net rent income/loss (14 minus 13) (f1_83 through f1_86)
    "15_A": AcroField(f"{_E1}.Line15[0].f1_83[0]", format="currency"),
    "15_B": AcroField(f"{_E1}.Line15[0].f1_84[0]", format="currency"),
    "15_C": AcroField(f"{_E1}.Line15[0].f1_85[0]", format="currency"),
    "15_D": AcroField(f"{_E1}.Line15[0].f1_86[0]", format="currency"),

    # Line 16 — Deductible rental real estate loss after limitation (f1_87 through f1_90)
    "16_A": AcroField(f"{_E1}.Line16[0].f1_87[0]", format="currency"),
    "16_B": AcroField(f"{_E1}.Line16[0].f1_88[0]", format="currency"),
    "16_C": AcroField(f"{_E1}.Line16[0].f1_89[0]", format="currency"),
    "16_D": AcroField(f"{_E1}.Line16[0].f1_90[0]", format="currency"),

    # Line 17 — Net income/loss (combine 15 and 16) (f1_91 through f1_94)
    "17_A": AcroField(f"{_E1}.Line17[0].f1_91[0]", format="currency"),
    "17_B": AcroField(f"{_E1}.Line17[0].f1_92[0]", format="currency"),
    "17_C": AcroField(f"{_E1}.Line17[0].f1_93[0]", format="currency"),
    "17_D": AcroField(f"{_E1}.Line17[0].f1_94[0]", format="currency"),

    # Line 18 — Deductible rental real estate loss (f1_95 through f1_98)
    "18_A": AcroField(f"{_E1}.Line18[0].f1_95[0]", format="currency"),
    "18_B": AcroField(f"{_E1}.Line18[0].f1_96[0]", format="currency"),
    "18_C": AcroField(f"{_E1}.Line18[0].f1_97[0]", format="currency"),
    "18_D": AcroField(f"{_E1}.Line18[0].f1_98[0]", format="currency"),

    # Line 19 — Net income/loss (combine 17 and 18)
    # NOTE: f1_99 second occurrence — use full path to disambiguate.
    "19_A": AcroField(f"{_E1}.Line19[0].f1_99[0]", format="currency"),
    "19_B": AcroField(f"{_E1}.Line19[0].f1_100[0]", format="currency"),
    "19_C": AcroField(f"{_E1}.Line19[0].f1_101[0]", format="currency"),
    "19_D": AcroField(f"{_E1}.Line19[0].f1_102[0]", format="currency"),

    # -------------------------------------------------------------------
    # Summary lines (single-column, page 1 bottom)
    # -------------------------------------------------------------------
    "20a": AcroField(f"{_P1}.f1_103[0]", format="currency"),   # Total gross rents
    "20b": AcroField(f"{_P1}.f1_104[0]", format="currency"),   # Total expenses
    "21": AcroField(f"{_P1}.f1_105[0]", format="currency"),    # Net income/loss
    "22a": AcroField(f"{_P1}.f1_106[0]", format="currency"),   # QBI

    # Line 22b — Items of income/expense not included on 22a (3 pairs)
    "22b_desc_1": AcroField(f"{_P1}.Table_Line22b[0].Item1[0].f1_107[0]"),
    "22b_amt_1": AcroField(f"{_P1}.Table_Line22b[0].Item1[0].f1_108[0]", format="currency"),
    "22b_desc_2": AcroField(f"{_P1}.Table_Line22b[0].Item2[0].f1_109[0]"),
    "22b_amt_2": AcroField(f"{_P1}.Table_Line22b[0].Item2[0].f1_110[0]", format="currency"),
    "22b_desc_3": AcroField(f"{_P1}.Table_Line22b[0].Item3[0].f1_111[0]"),
    "22b_amt_3": AcroField(f"{_P1}.Table_Line22b[0].Item3[0].f1_112[0]", format="currency"),

    "23": AcroField(f"{_P1}.f1_113[0]", format="currency"),    # Total line 22b

    # ===================================================================
    # PAGE 2 — Properties E-H
    # ===================================================================

    # -------------------------------------------------------------------
    # Line 1: Property descriptors (Table_Line1, rows 1-4)
    # Each row: letter, description, address, type, fair rental days, personal days
    # -------------------------------------------------------------------

    # Row 1 / Property E (f2_1 through f2_6)
    "1_E_letter": AcroField(f"{_T2}.Row1[0].f2_1[0]"),                              # Property letter
    "1_E_desc": AcroField(f"{_T2}.Row1[0].Col_a[0].f2_2[0]"),                       # (a) Address
    "1_E_addr": AcroField(f"{_T2}.Row1[0].Col_b[0].f2_3[0]"),                       # (b) Type code 1-8
    "1_E_type": AcroField(f"{_T2}.Row1[0].Col_c[0].f2_4[0]"),                       # (c) Type code A-I
    "1_E_fair_days": AcroField(f"{_T2}.Row1[0].Col_d[0].f2_5[0]", format="integer"),  # (d) Fair rental days
    "1_E_personal_days": AcroField(f"{_T2}.Row1[0].Col_e[0].f2_6[0]", format="integer"),  # (e) Personal use days

    # Row 2 / Property F (f2_7 through f2_12)
    "1_F_letter": AcroField(f"{_T2}.Row2[0].f2_7[0]"),
    "1_F_desc": AcroField(f"{_T2}.Row2[0].Col_a[0].f2_8[0]"),
    "1_F_addr": AcroField(f"{_T2}.Row2[0].Col_b[0].f2_9[0]"),
    "1_F_type": AcroField(f"{_T2}.Row2[0].Col_c[0].f2_10[0]"),
    "1_F_fair_days": AcroField(f"{_T2}.Row2[0].Col_d[0].f2_11[0]", format="integer"),
    "1_F_personal_days": AcroField(f"{_T2}.Row2[0].Col_e[0].f2_12[0]", format="integer"),

    # Row 3 / Property G (f2_13 through f2_18)
    "1_G_letter": AcroField(f"{_T2}.Row3[0].f2_13[0]"),
    "1_G_desc": AcroField(f"{_T2}.Row3[0].Col_a[0].f2_14[0]"),
    "1_G_addr": AcroField(f"{_T2}.Row3[0].Col_b[0].f2_15[0]"),
    "1_G_type": AcroField(f"{_T2}.Row3[0].Col_c[0].f2_16[0]"),
    "1_G_fair_days": AcroField(f"{_T2}.Row3[0].Col_d[0].f2_17[0]", format="integer"),
    "1_G_personal_days": AcroField(f"{_T2}.Row3[0].Col_e[0].f2_18[0]", format="integer"),

    # Row 4 / Property H (f2_19 through f2_24)
    "1_H_letter": AcroField(f"{_T2}.Row4[0].f2_19[0]"),
    "1_H_desc": AcroField(f"{_T2}.Row4[0].Col_a[0].f2_20[0]"),
    "1_H_addr": AcroField(f"{_T2}.Row4[0].Col_b[0].f2_21[0]"),
    "1_H_type": AcroField(f"{_T2}.Row4[0].Col_c[0].f2_22[0]"),
    "1_H_fair_days": AcroField(f"{_T2}.Row4[0].Col_d[0].f2_23[0]", format="integer"),
    "1_H_personal_days": AcroField(f"{_T2}.Row4[0].Col_e[0].f2_24[0]", format="integer"),

    # -------------------------------------------------------------------
    # Column headers (page 2) — property letters above the expense grid
    # -------------------------------------------------------------------
    "p2_col_header_E": AcroField(f"{_E2}.HeaderRow[0].f2_25[0]"),
    "p2_col_header_F": AcroField(f"{_E2}.HeaderRow[0].f2_26[0]"),
    "p2_col_header_G": AcroField(f"{_E2}.HeaderRow[0].f2_27[0]"),
    "p2_col_header_H": AcroField(f"{_E2}.HeaderRow[0].f2_28[0]"),

    # -------------------------------------------------------------------
    # Lines 2-19: Expense amounts for properties E-H (4 cols each)
    # -------------------------------------------------------------------

    # Line 2a — Advertising (f2_29 through f2_32)
    "2a_E": AcroField(f"{_E2}.Line2a[0].f2_29[0]", format="currency"),
    "2a_F": AcroField(f"{_E2}.Line2a[0].f2_30[0]", format="currency"),
    "2a_G": AcroField(f"{_E2}.Line2a[0].f2_31[0]", format="currency"),
    "2a_H": AcroField(f"{_E2}.Line2a[0].f2_32[0]", format="currency"),

    # Line 2b — Auto and travel (f2_33 through f2_36)
    "2b_E": AcroField(f"{_E2}.Line2b[0].f2_33[0]", format="currency"),
    "2b_F": AcroField(f"{_E2}.Line2b[0].f2_34[0]", format="currency"),
    "2b_G": AcroField(f"{_E2}.Line2b[0].f2_35[0]", format="currency"),
    "2b_H": AcroField(f"{_E2}.Line2b[0].f2_36[0]", format="currency"),

    # Line 2c — Cleaning and maintenance (f2_37 through f2_40)
    "2c_E": AcroField(f"{_E2}.Line2c[0].f2_37[0]", format="currency"),
    "2c_F": AcroField(f"{_E2}.Line2c[0].f2_38[0]", format="currency"),
    "2c_G": AcroField(f"{_E2}.Line2c[0].f2_39[0]", format="currency"),
    "2c_H": AcroField(f"{_E2}.Line2c[0].f2_40[0]", format="currency"),

    # Line 3 — Commissions (f2_41 through f2_44)
    "3_E": AcroField(f"{_E2}.Line3[0].f2_41[0]", format="currency"),
    "3_F": AcroField(f"{_E2}.Line3[0].f2_42[0]", format="currency"),
    "3_G": AcroField(f"{_E2}.Line3[0].f2_43[0]", format="currency"),
    "3_H": AcroField(f"{_E2}.Line3[0].f2_44[0]", format="currency"),

    # Line 4 — Insurance (f2_45 through f2_48)
    "4_E": AcroField(f"{_E2}.Line4[0].f2_45[0]", format="currency"),
    "4_F": AcroField(f"{_E2}.Line4[0].f2_46[0]", format="currency"),
    "4_G": AcroField(f"{_E2}.Line4[0].f2_47[0]", format="currency"),
    "4_H": AcroField(f"{_E2}.Line4[0].f2_48[0]", format="currency"),

    # Line 5 — Legal and other professional fees (f2_49 through f2_52)
    "5_E": AcroField(f"{_E2}.Line5[0].f2_49[0]", format="currency"),
    "5_F": AcroField(f"{_E2}.Line5[0].f2_50[0]", format="currency"),
    "5_G": AcroField(f"{_E2}.Line5[0].f2_51[0]", format="currency"),
    "5_H": AcroField(f"{_E2}.Line5[0].f2_52[0]", format="currency"),

    # Line 6 — Interest (f2_53 through f2_56)
    "6_E": AcroField(f"{_E2}.Line6[0].f2_53[0]", format="currency"),
    "6_F": AcroField(f"{_E2}.Line6[0].f2_54[0]", format="currency"),
    "6_G": AcroField(f"{_E2}.Line6[0].f2_55[0]", format="currency"),
    "6_H": AcroField(f"{_E2}.Line6[0].f2_56[0]", format="currency"),

    # Line 7 — Repairs (f2_57 through f2_60)
    "7_E": AcroField(f"{_E2}.Line7[0].f2_57[0]", format="currency"),
    "7_F": AcroField(f"{_E2}.Line7[0].f2_58[0]", format="currency"),
    "7_G": AcroField(f"{_E2}.Line7[0].f2_59[0]", format="currency"),
    "7_H": AcroField(f"{_E2}.Line7[0].f2_60[0]", format="currency"),

    # Line 8 — Taxes (f2_61 through f2_64)
    "8_E": AcroField(f"{_E2}.Line8[0].f2_61[0]", format="currency"),
    "8_F": AcroField(f"{_E2}.Line8[0].f2_62[0]", format="currency"),
    "8_G": AcroField(f"{_E2}.Line8[0].f2_63[0]", format="currency"),
    "8_H": AcroField(f"{_E2}.Line8[0].f2_64[0]", format="currency"),

    # Line 9 — Utilities (f2_65 through f2_68)
    "9_E": AcroField(f"{_E2}.Line9[0].f2_65[0]", format="currency"),
    "9_F": AcroField(f"{_E2}.Line9[0].f2_66[0]", format="currency"),
    "9_G": AcroField(f"{_E2}.Line9[0].f2_67[0]", format="currency"),
    "9_H": AcroField(f"{_E2}.Line9[0].f2_68[0]", format="currency"),

    # Line 10 — Wages and salaries (f2_69 through f2_72)
    "10_E": AcroField(f"{_E2}.Line10[0].f2_69[0]", format="currency"),
    "10_F": AcroField(f"{_E2}.Line10[0].f2_70[0]", format="currency"),
    "10_G": AcroField(f"{_E2}.Line10[0].f2_71[0]", format="currency"),
    "10_H": AcroField(f"{_E2}.Line10[0].f2_72[0]", format="currency"),

    # Line 11 — Depreciation (f2_73 through f2_76)
    "11_E": AcroField(f"{_E2}.Line11[0].f2_73[0]", format="currency"),
    "11_F": AcroField(f"{_E2}.Line11[0].f2_74[0]", format="currency"),
    "11_G": AcroField(f"{_E2}.Line11[0].f2_75[0]", format="currency"),
    "11_H": AcroField(f"{_E2}.Line11[0].f2_76[0]", format="currency"),

    # Line 12 — Other (describe) (f2_77 through f2_80)
    "12_E": AcroField(f"{_E2}.Line12[0].f2_77[0]", format="currency"),
    "12_F": AcroField(f"{_E2}.Line12[0].f2_78[0]", format="currency"),
    "12_G": AcroField(f"{_E2}.Line12[0].f2_79[0]", format="currency"),
    "12_H": AcroField(f"{_E2}.Line12[0].f2_80[0]", format="currency"),

    # Line 13 — Total expenses for each property (f2_81 through f2_84)
    "13_E": AcroField(f"{_E2}.Line13[0].f2_81[0]", format="currency"),
    "13_F": AcroField(f"{_E2}.Line13[0].f2_82[0]", format="currency"),
    "13_G": AcroField(f"{_E2}.Line13[0].f2_83[0]", format="currency"),
    "13_H": AcroField(f"{_E2}.Line13[0].f2_84[0]", format="currency"),

    # Line 14 — Rents received for each property (f2_85 through f2_88)
    "14_E": AcroField(f"{_E2}.Line14[0].f2_85[0]", format="currency"),
    "14_F": AcroField(f"{_E2}.Line14[0].f2_86[0]", format="currency"),
    "14_G": AcroField(f"{_E2}.Line14[0].f2_87[0]", format="currency"),
    "14_H": AcroField(f"{_E2}.Line14[0].f2_88[0]", format="currency"),

    # Line 15 — Net rent income/loss (14 minus 13) (f2_89 through f2_92)
    "15_E": AcroField(f"{_E2}.Line15[0].f2_89[0]", format="currency"),
    "15_F": AcroField(f"{_E2}.Line15[0].f2_90[0]", format="currency"),
    "15_G": AcroField(f"{_E2}.Line15[0].f2_91[0]", format="currency"),
    "15_H": AcroField(f"{_E2}.Line15[0].f2_92[0]", format="currency"),

    # Line 16 — Deductible rental real estate loss after limitation (f2_93 through f2_96)
    "16_E": AcroField(f"{_E2}.Line16[0].f2_93[0]", format="currency"),
    "16_F": AcroField(f"{_E2}.Line16[0].f2_94[0]", format="currency"),
    "16_G": AcroField(f"{_E2}.Line16[0].f2_95[0]", format="currency"),
    "16_H": AcroField(f"{_E2}.Line16[0].f2_96[0]", format="currency"),

    # Line 17 — Net income/loss (combine 15 and 16) (f2_97 through f2_100)
    "17_E": AcroField(f"{_E2}.Line17[0].f2_97[0]", format="currency"),
    "17_F": AcroField(f"{_E2}.Line17[0].f2_98[0]", format="currency"),
    "17_G": AcroField(f"{_E2}.Line17[0].f2_99[0]", format="currency"),
    "17_H": AcroField(f"{_E2}.Line17[0].f2_100[0]", format="currency"),

    # Line 18 — Deductible rental real estate loss (f2_101 through f2_104)
    "18_E": AcroField(f"{_E2}.Line18[0].f2_101[0]", format="currency"),
    "18_F": AcroField(f"{_E2}.Line18[0].f2_102[0]", format="currency"),
    "18_G": AcroField(f"{_E2}.Line18[0].f2_103[0]", format="currency"),
    "18_H": AcroField(f"{_E2}.Line18[0].f2_104[0]", format="currency"),

    # Line 19 — Net income/loss (combine 17 and 18) (f2_105 through f2_108)
    "19_E": AcroField(f"{_E2}.Line19[0].f2_105[0]", format="currency"),
    "19_F": AcroField(f"{_E2}.Line19[0].f2_106[0]", format="currency"),
    "19_G": AcroField(f"{_E2}.Line19[0].f2_107[0]", format="currency"),
    "19_H": AcroField(f"{_E2}.Line19[0].f2_108[0]", format="currency"),
}
