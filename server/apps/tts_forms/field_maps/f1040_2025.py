"""
AcroForm field map for IRS Form 1040 (2025 fillable PDF).

Maps our internal line_number / header keys to the AcroForm field names
in the official IRS fillable PDF (f1040.pdf).

PDF page structure (2 pages):
    Page 0 (Page1): Header + Filing Status + Dependents + Income (1-15)
    Page 1 (Page2): Tax + Credits + Payments + Refund/Owed + Signature

Field naming convention:
    - Text fields: f{page}_{seq}  (e.g., f1_47 = page 1, field 47)
    - Checkboxes:  c{page}_{seq}  (e.g., c1_5 = page 1, checkbox 5)
    - Full names:  topmostSubform[0].Page{n}[0].{field}[{idx}]

This is a rough-draft mapping — only essential fields for a simple return.
"""

from . import AcroField, FieldMap

# ============================================================================
# HEADER_MAP -- Taxpayer info, filing status, address
# ============================================================================
HEADER_MAP: FieldMap = {
    # First name and middle initial
    "first_name": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_01[0]",
    ),
    "last_name": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_02[0]",
    ),
    "ssn": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_03[0]",
    ),
    # Filing status checkboxes
    "fs_single": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_1[0]",
        field_type="checkbox", format="boolean",
    ),
    "fs_mfj": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_2[0]",
        field_type="checkbox", format="boolean",
    ),
    "fs_mfs": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_3[0]",
        field_type="checkbox", format="boolean",
    ),
    "mfs_spouse_name": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_05[0]",
    ),
    "spouse_first_name": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_06[0]",
    ),
    "spouse_last_name": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_07[0]",
    ),
    "spouse_ssn": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_08[0]",
    ),
    # Address
    "address_line1": AcroField(
        acro_name="topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_20[0]",
    ),
    "address_line2": AcroField(
        acro_name="topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_21[0]",
    ),
    "city": AcroField(
        acro_name="topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_22[0]",
    ),
    "state": AcroField(
        acro_name="topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_23[0]",
    ),
    "zip_code": AcroField(
        acro_name="topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_24[0]",
    ),
    # fs_hoh checkbox
    "fs_hoh": AcroField(
        acro_name="topmostSubform[0].Page1[0].Checkbox_ReadOrder[0].c1_8[0]",
        field_type="checkbox", format="boolean",
    ),
    # fs_qss checkbox
    "fs_qss": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_9[0]",
        field_type="checkbox", format="boolean",
    ),
    # Standard deduction checkbox
    "std_deduction_you": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_33[0]",
        field_type="checkbox", format="boolean",
    ),
    # Occupation (Page 2)
    "occupation": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_37[0]",
    ),
    "spouse_occupation": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_38[0]",
    ),
}


# ============================================================================
# FIELD_MAP -- Line numbers (income, deductions, tax, payments)
# ============================================================================
FIELD_MAP: FieldMap = {
    # ---- Page 1: Income ----
    # Line 1a — Wages
    "1a": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_47[0]",
        format="currency",
    ),
    # Line 1z — Total wages
    "1z": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_55[0]",
        format="currency",
    ),
    # Line 2a — Tax-exempt interest
    "2a": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_56[0]",
        format="currency",
    ),
    # Line 2b — Taxable interest
    "2b": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_57[0]",
        format="currency",
    ),
    # Line 8 — Other income
    "8": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_64[0]",
        format="currency",
    ),
    # Line 9 — Total income
    "9": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_65[0]",
        format="currency",
    ),
    # Line 10 — Adjustments
    "10": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_66[0]",
        format="currency",
    ),
    # Line 11 — AGI
    "11": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_67[0]",
        format="currency",
    ),
    # Line 12 — Standard deduction
    "12": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_68[0]",
        format="currency",
    ),
    # Line 13 — QBI deduction
    "13": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_69[0]",
        format="currency",
    ),
    # Line 14 — Total deductions
    "14": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_70[0]",
        format="currency",
    ),
    # Line 15 — Taxable income
    "15": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_71[0]",
        format="currency",
    ),

    # ---- Page 2: Tax and Credits ----
    # Line 16 — Tax
    "16": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_02[0]",
        format="currency",
    ),
    # Line 24 — Total tax
    "24": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_10[0]",
        format="currency",
    ),
    # Line 25a — W-2 withholding
    "25a": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_11[0]",
        format="currency",
    ),
    # Line 25d — Total withholding
    "25d": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_14[0]",
        format="currency",
    ),
    # Line 33 — Total payments
    "33": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_20[0]",
        format="currency",
    ),
    # Line 34 — Overpaid
    "34": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_21[0]",
        format="currency",
    ),
    # Line 37 — Amount owed
    "37": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_30[0]",
        format="currency",
    ),
}
