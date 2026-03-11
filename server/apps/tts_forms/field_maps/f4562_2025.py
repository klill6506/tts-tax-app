"""
AcroForm field map for Form 4562 -- Depreciation and Amortization (2025).

Template: resources/irs_forms/2025/f4562.pdf (277 AcroForm fields, 3 pages)

Part I: Election to Expense (Section 179)
Part II: Special Depreciation Allowance / Bonus (MACRS)
Part III: MACRS Depreciation (Section B: GDS, Section C: ADS)
Part IV: Summary
Part V: Listed Property
Part VI: Amortization
"""

from . import AcroField, FieldMap

_P1 = "topmostSubform[0].Page1[0]"
_P2 = "topmostSubform[0].Page2[0]"
_P3 = "topmostSubform[0].Page3[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP -- Entity identification
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    "entity_name":   AcroField(f"{_P1}.f1_1[0]"),
    "activity_desc": AcroField(f"{_P1}.f1_2[0]"),
    "ein":           AcroField(f"{_P1}.f1_3[0]"),
}

# ---------------------------------------------------------------------------
# Helpers for row-based tables
# ---------------------------------------------------------------------------

_SEC_B = f"{_P1}.SectionBTable[0]"
_SEC_C = f"{_P1}.SectionCTable[0]"
_LP26 = f"{_P2}.Table_Ln26[0]"
_LP27 = f"{_P2}.Table_Ln27[0]"
_AMORT = f"{_P3}.PartVITable[0]"


def _sec179_row(row: int) -> dict[str, AcroField]:
    """Section 179 property detail (Lines 6-7), 2 rows x 3 cols."""
    # Row 1: f1_9, f1_10, f1_11 (Table_Ln6 BodyRow1)
    # Row 2: f1_12, f1_13, f1_14 (Table_Ln6 BodyRow2)
    base = 9 + (row - 1) * 3
    prefix = f"{_P1}.Table_Ln6[0].BodyRow{row}[0]"
    tag = f"L6R{row}"
    return {
        f"{tag}_desc":    AcroField(f"{prefix}.f1_{base}[0]"),
        f"{tag}_cost":    AcroField(f"{prefix}.f1_{base + 1}[0]", format="currency"),
        f"{tag}_elected": AcroField(f"{prefix}.f1_{base + 2}[0]", format="currency"),
    }


def _secB_row(letter: str, field_start: int, container: str) -> dict[str, AcroField]:
    """Part III Section B row (Lines 19a-19f): 6 cols per row.
    Cols: (b) Month/year placed, (c) Basis, (d) Recovery period,
          (e) Convention, (f) Method, (g) Depreciation deduction.
    """
    tag = f"L19{letter}"
    p = f"{_SEC_B}.Line19{letter}[0]"
    return {
        f"{tag}_placed":     AcroField(f"{p}.f1_{field_start}[0]"),
        f"{tag}_basis":      AcroField(f"{p}.f1_{field_start + 1}[0]", format="currency"),
        f"{tag}_period":     AcroField(f"{p}.f1_{field_start + 2}[0]"),
        f"{tag}_convention": AcroField(f"{p}.f1_{field_start + 3}[0]"),
        f"{tag}_method":     AcroField(f"{p}.f1_{field_start + 4}[0]"),
        f"{tag}_depr":       AcroField(f"{p}.f1_{field_start + 5}[0]", format="currency"),
    }


def _secC_row(letter: str, field_start: int) -> dict[str, AcroField]:
    """Part III Section C row (Lines 20a-20e): 6 cols per row.
    Same column layout as Section B.
    Note: some rows have narrow 1px spacer fields — mapped only the usable ones.
    """
    tag = f"L20{letter}"
    p = f"{_SEC_C}.Line20{letter}[0]"
    return {
        f"{tag}_placed":     AcroField(f"{p}.f1_{field_start}[0]"),
        f"{tag}_basis":      AcroField(f"{p}.f1_{field_start + 1}[0]", format="currency"),
        # Fields after basis vary — the convention/method columns may have
        # 1px spacers. Map the depr column as the last full-width field.
        f"{tag}_depr":       AcroField(f"{p}.f1_{field_start + 5}[0]", format="currency"),
    }


def _listed_property_row(row: int) -> dict[str, AcroField]:
    """Part V Line 26 table: 3 rows x 9 cols."""
    # Row 1: f2_6..f2_14, Row 2: f2_15..f2_23, Row 3: f2_24..f2_32
    base = 6 + (row - 1) * 9
    prefix = f"{_LP26}.BodyRow{row}[0]"
    tag = f"LP26R{row}"
    return {
        f"{tag}_desc":    AcroField(f"{prefix}.f2_{base}[0]"),
        f"{tag}_placed":  AcroField(f"{prefix}.f2_{base + 1}[0]"),
        f"{tag}_buspct":  AcroField(f"{prefix}.f2_{base + 2}[0]"),
        f"{tag}_cost":    AcroField(f"{prefix}.f2_{base + 3}[0]", format="currency"),
        f"{tag}_basis":   AcroField(f"{prefix}.f2_{base + 4}[0]", format="currency"),
        f"{tag}_period":  AcroField(f"{prefix}.f2_{base + 5}[0]"),
        f"{tag}_method":  AcroField(f"{prefix}.f2_{base + 6}[0]"),
        f"{tag}_depr":    AcroField(f"{prefix}.f2_{base + 7}[0]", format="currency"),
        f"{tag}_elect":   AcroField(f"{prefix}.f2_{base + 8}[0]", format="currency"),
    }


def _vehicle_row(row: int) -> dict[str, AcroField]:
    """Part V Line 27 table (vehicles): 3 rows x 8 cols."""
    # Row 1: f2_33..f2_40, Row 2: f2_41..f2_48, Row 3: f2_49..f2_56
    base = 33 + (row - 1) * 8
    prefix = f"{_LP27}.BodyRow{row}[0]"
    tag = f"VH27R{row}"
    return {
        f"{tag}_desc":      AcroField(f"{prefix}.f2_{base}[0]"),
        f"{tag}_placed":    AcroField(f"{prefix}.f2_{base + 1}[0]"),
        f"{tag}_buspct":    AcroField(f"{prefix}.f2_{base + 2}[0]"),
        f"{tag}_cost":      AcroField(f"{prefix}.f2_{base + 3}[0]", format="currency"),
        f"{tag}_basis":     AcroField(f"{prefix}.f2_{base + 4}[0]", format="currency"),
        f"{tag}_period":    AcroField(f"{prefix}.f2_{base + 5}[0]"),
        f"{tag}_method":    AcroField(f"{prefix}.f2_{base + 6}[0]"),
        f"{tag}_depr":      AcroField(f"{prefix}.f2_{base + 7}[0]", format="currency"),
    }


def _amortization_row(row: int) -> dict[str, AcroField]:
    """Part VI amortization table: 2 rows x 6 cols."""
    # Row 1: f3_1..f3_6, Row 2: f3_7..f3_12
    base = 1 + (row - 1) * 6
    prefix = f"{_AMORT}.BodyRow{row}[0]"
    tag = f"AM42R{row}"
    return {
        f"{tag}_desc":      AcroField(f"{prefix}.f3_{base}[0]"),
        f"{tag}_date":      AcroField(f"{prefix}.f3_{base + 1}[0]"),
        f"{tag}_amount":    AcroField(f"{prefix}.f3_{base + 2}[0]", format="currency"),
        f"{tag}_code":      AcroField(f"{prefix}.f3_{base + 3}[0]"),
        f"{tag}_period":    AcroField(f"{prefix}.f3_{base + 4}[0]"),
        f"{tag}_deduction": AcroField(f"{prefix}.f3_{base + 5}[0]", format="currency"),
    }


# ---------------------------------------------------------------------------
# FIELD_MAP
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {}

# Part I: Section 179 (Lines 1-13)
FIELD_MAP.update({
    "F4562_1":  AcroField(f"{_P1}.f1_4[0]", format="currency"),   # Line 1: Max deduction ($2,500,000)
    "F4562_2":  AcroField(f"{_P1}.f1_5[0]", format="currency"),   # Line 2: Total cost of 179 property
    "F4562_3":  AcroField(f"{_P1}.f1_6[0]", format="currency"),   # Line 3: Threshold ($4,000,000)
    "F4562_4":  AcroField(f"{_P1}.f1_7[0]", format="currency"),   # Line 4: Reduction in limitation
    "F4562_5":  AcroField(f"{_P1}.f1_8[0]", format="currency"),   # Line 5: Dollar limitation
})

# Lines 6-7: Section 179 property detail (2 rows)
for _row in range(1, 3):
    FIELD_MAP.update(_sec179_row(_row))

FIELD_MAP.update({
    "F4562_8":  AcroField(f"{_P1}.f1_15[0]", format="currency"),  # Line 8: Total elected (sum 6-7 col c)
    "F4562_9":  AcroField(f"{_P1}.f1_16[0]", format="currency"),  # Line 9: Tentative deduction
    "F4562_10": AcroField(f"{_P1}.f1_17[0]", format="currency"),  # Line 10: Carryover from prior year
    "F4562_11": AcroField(f"{_P1}.f1_18[0]", format="currency"),  # Line 11: Business income limitation
    "F4562_12": AcroField(f"{_P1}.f1_19[0]", format="currency"),  # Line 12: Section 179 expense deduction
    "F4562_13": AcroField(f"{_P1}.f1_20[0]", format="currency"),  # Line 13: Carryover to next year
})

# Part II: Special Depreciation Allowance (Lines 14-16)
FIELD_MAP.update({
    "F4562_14": AcroField(f"{_P1}.f1_21[0]", format="currency"),  # Line 14: SDA/Bonus depr
    "F4562_15": AcroField(f"{_P1}.f1_22[0]", format="currency"),  # Line 15: Property subject to 168(f)(1)
    "F4562_16": AcroField(f"{_P1}.f1_23[0]", format="currency"),  # Line 16: Add lines 14 and 15
})

# Part III: MACRS Depreciation
FIELD_MAP.update({
    "F4562_17": AcroField(f"{_P1}.f1_24[0]", format="currency"),  # Line 17: MACRS deductions (prior years)
})

# Line 18 checkbox: election to group
FIELD_MAP.update({
    "F4562_18": AcroField(f"{_P1}.c1_1[0]", field_type="checkbox", format="boolean"),
})

# Section B: GDS MACRS (Lines 19a-19f, 6 standard rows)
FIELD_MAP.update(_secB_row("a", 26, ""))   # 3-year: f1_26..f1_31
FIELD_MAP.update(_secB_row("b", 32, ""))   # 5-year: f1_32..f1_37
FIELD_MAP.update(_secB_row("c", 38, ""))   # 7-year: f1_38..f1_43
FIELD_MAP.update(_secB_row("d", 44, ""))   # 10-year: f1_44..f1_49
FIELD_MAP.update(_secB_row("e", 50, ""))   # 15-year: f1_50..f1_55
FIELD_MAP.update(_secB_row("f", 56, ""))   # 20-year: f1_56..f1_61

# Lines 19g (25-year) — has some narrow spacer fields
# f1_62=placed, f1_63=basis, f1_64=1px spacer, f1_65=convention, f1_66=1px spacer, f1_67=depr
FIELD_MAP.update({
    "L19g_placed":     AcroField(f"{_SEC_B}.Line19g[0].f1_62[0]"),
    "L19g_basis":      AcroField(f"{_SEC_B}.Line19g[0].f1_63[0]", format="currency"),
    "L19g_convention": AcroField(f"{_SEC_B}.Line19g[0].f1_65[0]"),
    "L19g_depr":       AcroField(f"{_SEC_B}.Line19g[0].f1_67[0]", format="currency"),
})

# Lines 19h (27.5-year residential rental)
# f1_68=placed, f1_69=basis, f1_70=1px, f1_71=1px, f1_72=1px, f1_73=depr
FIELD_MAP.update({
    "L19h_placed": AcroField(f"{_SEC_B}.Line19h[0].f1_68[0]"),
    "L19h_basis":  AcroField(f"{_SEC_B}.Line19h[0].f1_69[0]", format="currency"),
    "L19h_depr":   AcroField(f"{_SEC_B}.Line19h[0].f1_73[0]", format="currency"),
})

# Lines 19i (39-year nonresidential real property) — 2 sub-rows
# Sub-row 1: f1_74..f1_79 (Line19i_1)
FIELD_MAP.update({
    "L19i_placed": AcroField(f"{_SEC_B}.Line19i_1[0].f1_74[0]"),
    "L19i_basis":  AcroField(f"{_SEC_B}.Line19i_1[0].f1_75[0]", format="currency"),
    "L19i_depr":   AcroField(f"{_SEC_B}.Line19i_1[0].f1_79[0]", format="currency"),
})

# Section C: ADS MACRS (Lines 20a-20e)
# Each row has potential spacer fields; map placed, basis, and depr
FIELD_MAP.update({
    "L20a_placed": AcroField(f"{_SEC_C}.Line20a[0].f1_98[0]"),
    "L20a_basis":  AcroField(f"{_SEC_C}.Line20a[0].f1_99[0]", format="currency"),
    "L20a_depr":   AcroField(f"{_SEC_C}.Line20a[0].f1_103[0]", format="currency"),
    "L20b_placed": AcroField(f"{_SEC_C}.Line20b[0].f1_104[0]"),
    "L20b_basis":  AcroField(f"{_SEC_C}.Line20b[0].f1_105[0]", format="currency"),
    "L20b_depr":   AcroField(f"{_SEC_C}.Line20b[0].f1_109[0]", format="currency"),
})

# Part IV Summary
FIELD_MAP.update({
    "F4562_21": AcroField(f"{_P1}.f1_25[0]", format="currency"),  # Line 21: Listed property (from Part V)
    "F4562_22": AcroField(f"{_P2}.f2_1[0]",  format="currency"),  # Line 22: Total depreciation
    "F4562_23": AcroField(f"{_P2}.f2_2[0]",  format="currency"),  # Line 23: For assets shown above
})

# Part V: Listed Property
FIELD_MAP.update({
    "F4562_25": AcroField(f"{_P2}.f2_5[0]", format="currency"),  # Line 25: auto expense total
})

# Line 26 table (3 rows x 9 cols)
for _row in range(1, 4):
    FIELD_MAP.update(_listed_property_row(_row))

# Line 27 table (vehicles, 3 rows x 8 cols)
for _row in range(1, 4):
    FIELD_MAP.update(_vehicle_row(_row))

FIELD_MAP.update({
    "F4562_28": AcroField(f"{_P2}.f2_57[0]", format="currency"),  # Line 28: total col (h)
    "F4562_29": AcroField(f"{_P2}.f2_58[0]", format="currency"),  # Line 29: total col (i)
})

# Part VI: Amortization
for _row in range(1, 3):
    FIELD_MAP.update(_amortization_row(_row))

FIELD_MAP.update({
    "F4562_44": AcroField(f"{_P3}.f3_13[0]", format="currency"),  # Line 44: Total amortization
    "F4562_45": AcroField(f"{_P3}.f3_14[0]", format="currency"),  # Line 45: Total (L42 + L44)
})
