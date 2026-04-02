"""
AcroForm field map for Schedule F (Form 1040) — Profit or Loss From Farming (2025).

Template: resources/irs_forms/2025/f1040sf.pdf (100 AcroForm fields, 2 pages)

Page 1: Header (Lines A-G), Part I (Lines 1-9), Part II (Lines 10-34)
Page 2: Part III (Lines 37-50, accrual method) — not used for S-Corp cash-method farms

Seed line numbers use F-prefix (F1a, F2, F10, etc.) matching seed_1120s.py sched_f section.
"""

from . import AcroField, FieldMap

_P1 = "topmostSubform[0].Page1[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP — Entity identification
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    "entity_name": AcroField(f"{_P1}.f1_1[0]"),    # Name of proprietor
    "ein":         AcroField(f"{_P1}.f1_2[0]"),     # SSN (we use for EIN)
}

# ---------------------------------------------------------------------------
# FIELD_MAP — Header fields, Part I income, Part II expenses
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {
    # --- Header fields (Lines A-G) ---
    "FH_CROP":  AcroField(f"{_P1}.f1_3[0]"),                                             # A: Principal crop
    "FH_CODE":  AcroField(f"{_P1}.CombField_LineB[0].f1_4[0]", font_size=7),               # B: Activity code (small comb box)
    "FH_EIN":   AcroField(f"{_P1}.CombField_LineD[0].f1_5[0]"),                           # D: EIN
    # C: Accounting method checkboxes (Cash / Accrual)
    "FH_METHOD_CASH":    AcroField(f"{_P1}.LineC_ReadOrder[0].c1_1[0]", field_type="checkbox"),
    "FH_METHOD_ACCRUAL": AcroField(f"{_P1}.LineC_ReadOrder[0].c1_1[1]", field_type="checkbox"),
    # E: Material participation (Yes / No)
    "FH_PARTICIPATION_YES": AcroField(f"{_P1}.c1_2[0]", field_type="checkbox"),
    "FH_PARTICIPATION_NO":  AcroField(f"{_P1}.c1_2[1]", field_type="checkbox"),
    # F: Did you make payments requiring 1099? (Yes / No)
    "FH_1099_RECEIVED_YES": AcroField(f"{_P1}.c1_3[0]", field_type="checkbox"),
    "FH_1099_RECEIVED_NO":  AcroField(f"{_P1}.c1_3[1]", field_type="checkbox"),
    # G: Did you file required 1099s? (Yes / No)
    "FH_1099_FILED_YES": AcroField(f"{_P1}.c1_4[0]", field_type="checkbox"),
    "FH_1099_FILED_NO":  AcroField(f"{_P1}.c1_4[1]", field_type="checkbox"),

    # --- Part I: Farm Income (Lines 1-9) ---
    "F1a": AcroField(f"{_P1}.f1_6[0]", format="currency"),     # 1a: Sales of purchased livestock
    "F1b": AcroField(f"{_P1}.f1_7[0]", format="currency"),     # 1b: Cost/basis of purchased livestock
    "F1c": AcroField(f"{_P1}.f1_8[0]", format="currency"),     # 1c: Subtract 1b from 1a
    "F2":  AcroField(f"{_P1}.f1_9[0]", format="currency"),     # 2: Sales of livestock raised
    "F3":  AcroField(f"{_P1}.f1_11[0]", format="currency"),    # 3b: Cooperative distributions (taxable)
    "F4":  AcroField(f"{_P1}.f1_13[0]", format="currency"),    # 4b: Agricultural program payments (taxable)
    "F5":  AcroField(f"{_P1}.f1_14[0]", format="currency"),    # 5a: CCC loans reported under election
    "F6":  AcroField(f"{_P1}.f1_18[0]", format="currency"),    # 6b: Crop insurance proceeds (taxable)
    "F7":  AcroField(f"{_P1}.f1_19[0]", format="currency"),    # 7: Custom hire income
    "F8":  AcroField(f"{_P1}.f1_20[0]", format="currency"),    # 8: Other income
    "F9":  AcroField(f"{_P1}.f1_22[0]", format="currency"),    # 9: Gross income

    # --- Part II: Farm Expenses (Lines 10-34) ---
    # Left column (Lines 10-22)
    "F10":  AcroField(f"{_P1}.Lines10-22[0].f1_23[0]", format="currency"),  # 10: Car and truck
    "F11":  AcroField(f"{_P1}.Lines10-22[0].f1_24[0]", format="currency"),  # 11: Chemicals
    "F12":  AcroField(f"{_P1}.Lines10-22[0].f1_25[0]", format="currency"),  # 12: Conservation
    "F13":  AcroField(f"{_P1}.Lines10-22[0].f1_26[0]", format="currency"),  # 13: Custom hire
    "F14":  AcroField(f"{_P1}.Lines10-22[0].f1_27[0]", format="currency"),  # 14: Depreciation / §179
    "F15":  AcroField(f"{_P1}.Lines10-22[0].f1_28[0]", format="currency"),  # 15: Employee benefits
    "F16":  AcroField(f"{_P1}.Lines10-22[0].f1_29[0]", format="currency"),  # 16: Feed
    "F17":  AcroField(f"{_P1}.Lines10-22[0].f1_30[0]", format="currency"),  # 17: Fertilizers and lime
    "F18":  AcroField(f"{_P1}.Lines10-22[0].f1_31[0]", format="currency"),  # 18: Freight and trucking
    "F19":  AcroField(f"{_P1}.Lines10-22[0].f1_32[0]", format="currency"),  # 19: Gasoline, fuel, oil
    "F20":  AcroField(f"{_P1}.Lines10-22[0].f1_33[0]", format="currency"),  # 20: Insurance
    "F21a": AcroField(f"{_P1}.Lines10-22[0].f1_34[0]", format="currency"),  # 21a: Interest — Mortgage
    "F21b": AcroField(f"{_P1}.Lines10-22[0].f1_35[0]", format="currency"),  # 21b: Interest — Other
    "F22":  AcroField(f"{_P1}.Lines10-22[0].f1_36[0]", format="currency"),  # 22: Labor hired

    # Right column (Lines 23-32)
    "F23":  AcroField(f"{_P1}.f1_37[0]", format="currency"),   # 23: Pension/profit-sharing
    "F24a": AcroField(f"{_P1}.f1_38[0]", format="currency"),   # 24a: Rent — vehicles/machinery
    "F24b": AcroField(f"{_P1}.f1_39[0]", format="currency"),   # 24b: Rent — other
    "F25":  AcroField(f"{_P1}.f1_40[0]", format="currency"),   # 25: Repairs and maintenance
    "F26":  AcroField(f"{_P1}.f1_41[0]", format="currency"),   # 26: Seeds and plants
    "F27":  AcroField(f"{_P1}.f1_42[0]", format="currency"),   # 27: Storage and warehousing
    "F28":  AcroField(f"{_P1}.f1_43[0]", format="currency"),   # 28: Supplies
    "F29":  AcroField(f"{_P1}.f1_44[0]", format="currency"),   # 29: Taxes
    "F30":  AcroField(f"{_P1}.f1_45[0]", format="currency"),   # 30: Utilities
    "F31":  AcroField(f"{_P1}.f1_46[0]", format="currency"),   # 31: Vet, breeding, medicine
    "F32":  AcroField(f"{_P1}.f1_48[0]", format="currency"),   # 32a: Other expenses (amount)

    # Summary
    "F33":  AcroField(f"{_P1}.f1_59[0]", format="currency"),   # 33: Total expenses
    "F34":  AcroField(f"{_P1}.f1_60[0]", format="currency"),   # 34: Net farm profit/(loss)

    # Line 36 checkboxes (at-risk)
    "F36a": AcroField(f"{_P1}.c1_6[0]", field_type="checkbox"),  # All investment at risk
    "F36b": AcroField(f"{_P1}.c1_6[1]", field_type="checkbox"),  # Some not at risk
}
