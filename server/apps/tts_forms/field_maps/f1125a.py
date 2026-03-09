"""
AcroForm field map for Form 1125-A — Cost of Goods Sold (Rev. November 2024).

Template: resources/irs_forms/2025/f1125a.pdf (25 AcroForm fields)

Single-page form (pages 2-3 are instructions only).
Attached to Form 1120, 1120-S, or 1065.

Lines 1-8: currency amounts (COGS computation)
Line 9a: inventory valuation method checkboxes (i-vi)
Line 9b-9c: single checkboxes
Line 9d: LIFO amounts
Line 9e-9f: Yes/No checkbox pairs
"""

from . import AcroField, FieldMap

_P = "topmostSubform[0].Page1[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP — Entity identification
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    "entity_name": AcroField(f"{_P}.f1_1[0]"),      # Name
    "ein": AcroField(f"{_P}.f1_2[0]"),               # EIN
}

# ---------------------------------------------------------------------------
# FIELD_MAP — Lines 1-8 amounts + Line 9 inventory questions
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {
    # Lines 1-8: COGS computation (currency amounts)
    "1": AcroField(f"{_P}.f1_3[0]", format="currency"),     # Inventory at beginning
    "2": AcroField(f"{_P}.f1_5[0]", format="currency"),     # Purchases
    "3": AcroField(f"{_P}.f1_7[0]", format="currency"),     # Cost of labor
    "4": AcroField(f"{_P}.f1_9[0]", format="currency"),     # Additional 263A costs
    "5": AcroField(f"{_P}.f1_11[0]", format="currency"),    # Other costs
    "6": AcroField(f"{_P}.f1_13[0]", format="currency"),    # Total (lines 1-5)
    "7": AcroField(f"{_P}.f1_15[0]", format="currency"),    # Inventory at end
    "8": AcroField(f"{_P}.f1_17[0]", format="currency"),    # COGS (line 6 - line 7)

    # Line 9a: Inventory valuation method checkboxes
    "9a_cost": AcroField(f"{_P}.c1_1[0]", field_type="checkbox"),       # (i) Cost
    "9a_lcm": AcroField(f"{_P}.c1_2[0]", field_type="checkbox"),        # (ii) Lower of cost or market
    "9a_other": AcroField(f"{_P}.c1_3[0]", field_type="checkbox"),      # (iii) Other
    "9a_other_desc": AcroField(f"{_P}.f1_19[0]"),                       # Other method description
    "9a_materials": AcroField(f"{_P}.c1_4[0]", field_type="checkbox"),   # (iv) Non-incidental materials
    "9a_afs": AcroField(f"{_P}.c1_5[0]", field_type="checkbox"),        # (v) AFS method
    "9a_non_afs": AcroField(f"{_P}.c1_6[0]", field_type="checkbox"),    # (vi) Non-AFS method

    # Line 9b: Writedown of subnormal goods
    "9b": AcroField(f"{_P}.c1_7[0]", field_type="checkbox"),

    # Line 9c: LIFO adopted this year
    "9c": AcroField(f"{_P}.c1_8[0]", field_type="checkbox"),

    # Line 9d: LIFO amounts
    "9d_i": AcroField(f"{_P}.f1_20[0]", format="currency"),    # 9d(i) closing LIFO inventory
    "9d_ii": AcroField(f"{_P}.f1_22[0]", format="currency"),   # 9d(ii) closing LIFO reserve

    # Line 9e: Section 263A applies? (Yes/No)
    "9e_yes": AcroField(f"{_P}.c1_9[0]", field_type="checkbox"),
    "9e_no": AcroField(f"{_P}.c1_9[1]", field_type="checkbox"),

    # Line 9f: Change in quantities/cost/valuations? (Yes/No)
    "9f_yes": AcroField(f"{_P}.c1_10[0]", field_type="checkbox"),
    "9f_no": AcroField(f"{_P}.c1_10[1]", field_type="checkbox"),
}
