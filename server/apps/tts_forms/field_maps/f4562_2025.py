"""
AcroForm field map for Form 4562 -- Depreciation and Amortization (2025).

Template: resources/irs_forms/2025/f4562.pdf (277 AcroForm fields, 3 pages)

Part I: Election to Expense (Section 179)
Part II: Special Depreciation Allowance / Bonus (MACRS)
Part III: MACRS Depreciation
Part IV: Summary
Part V: Listed Property
Part VI: Amortization

TODO: Complete detailed line mappings once depreciation → 4562 flow is built.
"""

from . import AcroField, FieldMap

_P1 = "topmostSubform[0].Page1[0]"
_P2 = "topmostSubform[0].Page2[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP -- Entity identification
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    "entity_name":   AcroField(f"{_P1}.f1_1[0]"),
    "activity_desc": AcroField(f"{_P1}.f1_2[0]"),
    "ein":           AcroField(f"{_P1}.f1_3[0]"),
}

# ---------------------------------------------------------------------------
# FIELD_MAP -- Summary lines only (detailed row mapping TBD)
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {
    # Part I: Section 179
    "F4562_1":  AcroField(f"{_P1}.f1_4[0]", format="currency"),   # Line 1: Max deduction
    "F4562_2":  AcroField(f"{_P1}.f1_5[0]", format="currency"),   # Line 2: Total cost of 179 property
    "F4562_3":  AcroField(f"{_P1}.f1_6[0]", format="currency"),   # Line 3: Threshold
    "F4562_4":  AcroField(f"{_P1}.f1_7[0]", format="currency"),   # Line 4: Reduction
    "F4562_5":  AcroField(f"{_P1}.f1_8[0]", format="currency"),   # Line 5: Dollar limitation
    # Lines 6-7: Section 179 property detail rows (f1_9..f1_14)
    "F4562_8":  AcroField(f"{_P1}.f1_15[0]", format="currency"),   # Line 8: Total elected
    "F4562_9":  AcroField(f"{_P1}.f1_16[0]", format="currency"),   # Line 9: Tentative deduction
    "F4562_10": AcroField(f"{_P1}.f1_17[0]", format="currency"),   # Line 10: Carryover
    "F4562_11": AcroField(f"{_P1}.f1_18[0]", format="currency"),   # Line 11: Business income limit
    "F4562_12": AcroField(f"{_P1}.f1_19[0]", format="currency"),   # Line 12: Section 179 expense
    "F4562_13": AcroField(f"{_P1}.f1_20[0]", format="currency"),   # Line 13: Carryover to next year

    # Part II: Special Depreciation Allowance
    "F4562_14": AcroField(f"{_P1}.f1_21[0]", format="currency"),   # Line 14: Bonus depr property
    "F4562_15": AcroField(f"{_P1}.f1_22[0]", format="currency"),   # Line 15: Total bonus
    "F4562_16": AcroField(f"{_P1}.f1_23[0]", format="currency"),   # Line 16: MACRS subtotal
    "F4562_17": AcroField(f"{_P1}.f1_24[0]", format="currency"),   # Line 17: MACRS total

    # Part III + IV: Summary
    "F4562_21": AcroField(f"{_P1}.f1_25[0]", format="currency"),   # Line 21: Listed property total
    "F4562_22": AcroField(f"{_P2}.f2_1[0]",  format="currency"),   # Line 22: Total depreciation

    # Part V: Listed property (summary)
    "F4562_25": AcroField(f"{_P2}.f2_2[0]",  format="currency"),   # Line 25: total listed property
}
