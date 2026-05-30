"""
AcroForm field map for IRS Form 1040 (2025 fillable PDF).

Maps our internal line_number / header keys to the AcroForm field names
in the official IRS fillable PDF (f1040.pdf).

2025 IRS Form 1040 redesign (OBBBA-driven) — page layout
========================================================
    Page 0 (Page1): Header + Filing Status + Dependents + Income
                    Lines 1a through 11a (AGI).
    Page 1 (Page2): AGI carry (11b) + Deductions (12a-12e, 13a-13b) +
                    Lines 14-38 (taxable income, tax, credits, payments,
                    refund/owed, signature).

Notable 2025 changes from earlier years:
    - Line 11 is now labeled "11a" on page 1, with "11b" on page 2
      carrying the same AGI value to the tax/credits section.
    - Line 12 is now labeled "12e" — the actual standard or itemized
      deduction amount. 12a-12d are checkboxes (dependent on another
      return, blind, born before, spouse blind).
    - Line 13 splits into 13a (QBI deduction from Form 8995/8995-A)
      and 13b (new OBBBA Senior Bonus Deduction from Schedule 1-A).
    - Lines 14-15 moved from page 1 (in older returns) to page 2.

Semantic key convention
========================
Our seed_1040 + compute pipeline pre-date this redesign and use simple
integer-style keys ("11", "12", "13", …). The keys here preserve
that convention and point at the 2025 widget that holds the same
semantic value:
    "11" → 11a widget (AGI)
    "12" → 12e widget (std or itemized deduction amount)
    "13" → 13a widget (QBI deduction only — 13b OBBBA Senior Bonus
            Deduction is NOT yet wired into compute or seed; out-of-
            scope for the 2026-05-29 field-map audit).

Field naming convention
=======================
    - Text fields: f{page}_{seq}  (e.g., f1_47 = page 1, widget 47)
    - Checkboxes:  c{page}_{seq}  (e.g., c1_5 = page 1, checkbox 5)
    - Full names:  topmostSubform[0].Page{n}[0].{field}[{idx}]

Provenance: each widget name was verified against the 2025 PDF by
position (label-y-band ± 6px, value column at x≈540 for right column
or x≈446 for middle column). See scripts/inspect_1040_full.py for the
audit run and tests/test_f1040_2025_field_map_audit.py for the locked-
in render assertions.
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
    # Line 1a — Wages (p1, y=456, right col)
    "1a": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_47[0]",
        format="currency",
    ),
    # Line 1z — Total income from W-2 box 1 + 1b through 1i (p1, y=564, right col)
    "1z": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_57[0]",
        format="currency",
    ),
    # Line 2a — Tax-exempt interest (p1, y=576, middle col x=288)
    "2a": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_58[0]",
        format="currency",
    ),
    # Line 2b — Taxable interest (p1, y=576, right col x=540)
    "2b": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_59[0]",
        format="currency",
    ),
    # Line 8 — Other income from Schedule 1, line 10 (p1, y=720, right col)
    "8": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_72[0]",
        format="currency",
    ),
    # Line 9 — Total income (p1, y=732, right col)
    "9": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_73[0]",
        format="currency",
    ),
    # Line 10 — Adjustments to income from Schedule 1 (p1, y=744, right col)
    "10": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_74[0]",
        format="currency",
    ),
    # Line 11 — Adjusted Gross Income (IRS 2025 label: "11a", p1, y=756, right col)
    "11": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_75[0]",
        format="currency",
    ),
    # Line 12 — Standard / itemized deduction amount
    # (IRS 2025 label: "12e" — moved to page 2 in the OBBBA redesign,
    # p2, y=102, right col)
    "12": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_02[0]",
        format="currency",
    ),
    # Line 13 — QBI deduction (IRS 2025 label: "13a"; OBBBA also added
    # "13b" Senior Bonus Deduction which is NOT wired here, p2, y=114,
    # right col)
    "13": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_03[0]",
        format="currency",
    ),
    # Line 14 — Add lines 12e, 13a, 13b (p2, y=138, right col)
    "14": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_05[0]",
        format="currency",
    ),
    # Line 15 — Taxable income = line 11b − line 14 (p2, y=150, right col)
    "15": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_06[0]",
        format="currency",
    ),

    # ---- Page 2: Tax and Credits ----
    # Line 16 — Tax (p2, y=162, right col)
    "16": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_08[0]",
        format="currency",
    ),
    # Line 19 — Child tax credit + Credit for other dependents (from
    # Schedule 8812 Line 14, p2, y=198, right col). Verified Session K
    # Part 2.
    "19": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_11[0]",
        format="currency",
    ),
    # Line 24 — Total tax (p2, y=258, right col)
    "24": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_16[0]",
        format="currency",
    ),
    # Line 25a — Federal income tax withheld from W-2 (p2, y=282,
    # middle col x=446)
    "25a": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_17[0]",
        format="currency",
    ),
    # Line 25d — Total federal withholding (p2, y=318, right col)
    "25d": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_20[0]",
        format="currency",
    ),
    # Line 28 — Additional Child Tax Credit, refundable (from
    # Schedule 8812 Line 27, p2, y=414, middle col x=446). Verified
    # Session K Part 2.
    "28": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_24[0]",
        format="currency",
    ),
    # Line 33 — Total payments (p2, y=474, right col)
    "33": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_29[0]",
        format="currency",
    ),
    # Line 34 — Amount overpaid (p2, y=486, right col)
    "34": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_30[0]",
        format="currency",
    ),
    # Line 37 — Amount you owe (p2, y=552, right col)
    "37": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_35[0]",
        format="currency",
    ),
}
