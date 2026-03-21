"""
AcroForm field map for Form 8949 -- Sales and Other Dispositions of Capital Assets (2025).

Template: resources/irs_forms/2025/f8949.pdf (202 AcroForm fields, 2 pages)

Page 1 — Part I: Short-Term (held one year or less)
  Checkboxes A-F, then up to 11 transaction rows with 8 columns each:
  (a) Description, (b) Date acquired, (c) Date sold, (d) Proceeds,
  (e) Cost basis, (f) Code, (g) Adjustment, (h) Gain/Loss
  Totals line at bottom

Page 2 — Part II: Long-Term (held more than one year)
  Same structure as Part I
"""

from . import AcroField, FieldMap

_P1 = "topmostSubform[0].Page1[0]"
_P2 = "topmostSubform[0].Page2[0]"
_T1 = f"{_P1}.Table_Line1_Part1[0]"
_T2 = f"{_P2}.Table_Line1_Part2[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP -- Entity identification
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    "entity_name": AcroField(f"{_P1}.f1_01[0]"),
    "ein":         AcroField(f"{_P1}.f1_02[0]"),
}

# ---------------------------------------------------------------------------
# FIELD_MAP -- Checkboxes + per-row transactions + totals
# ---------------------------------------------------------------------------

# Build per-row mappings programmatically.
# Part I (Page 1): Rows 1-11, fields f1_03..f1_90 (8 fields per row)
# Part II (Page 2): Rows 1-11, fields f2_03..f2_90 (8 fields per row)
# Columns: (a) desc, (b) date_acquired, (c) date_sold, (d) proceeds,
#           (e) cost, (f) code, (g) adjustment, (h) gain_loss

FIELD_MAP: FieldMap = {
    # Part I checkboxes (which box on 1099-B)
    "F8949_P1_A": AcroField(f"{_P1}.c1_1[0]", field_type="checkbox", format="boolean"),
    "F8949_P1_B": AcroField(f"{_P1}.c1_1[1]", field_type="checkbox", format="boolean"),
    "F8949_P1_C": AcroField(f"{_P1}.c1_1[2]", field_type="checkbox", format="boolean"),

    # Part II checkboxes
    "F8949_P2_D": AcroField(f"{_P2}.c2_1[0]", field_type="checkbox", format="boolean"),
    "F8949_P2_E": AcroField(f"{_P2}.c2_1[1]", field_type="checkbox", format="boolean"),
    "F8949_P2_F": AcroField(f"{_P2}.c2_1[2]", field_type="checkbox", format="boolean"),

    # Part I totals (bottom of page 1)
    "F8949_P1_TOT_proceeds": AcroField(f"{_P1}.f1_91[0]", format="currency"),
    "F8949_P1_TOT_cost":     AcroField(f"{_P1}.f1_92[0]", format="currency"),
    "F8949_P1_TOT_code":     AcroField(f"{_P1}.f1_93[0]"),
    "F8949_P1_TOT_adj":      AcroField(f"{_P1}.f1_94[0]", format="currency"),
    "F8949_P1_TOT_gain":     AcroField(f"{_P1}.f1_95[0]", format="currency"),

    # Part II totals (bottom of page 2)
    "F8949_P2_TOT_proceeds": AcroField(f"{_P2}.f2_91[0]", format="currency"),
    "F8949_P2_TOT_cost":     AcroField(f"{_P2}.f2_92[0]", format="currency"),
    "F8949_P2_TOT_code":     AcroField(f"{_P2}.f2_93[0]"),
    "F8949_P2_TOT_adj":      AcroField(f"{_P2}.f2_94[0]", format="currency"),
    "F8949_P2_TOT_gain":     AcroField(f"{_P2}.f2_95[0]", format="currency"),
}

# Part I per-row fields (11 rows, 8 fields each: f1_03..f1_90)
_COLS = ("desc", "acquired", "sold", "proceeds", "cost", "code", "adj", "gain")
_field_num = 3
for row in range(1, 12):
    for col in _COLS:
        key = f"F8949_P1_R{row}_{col}"
        fmt = "currency" if col in ("proceeds", "cost", "adj", "gain") else None
        FIELD_MAP[key] = AcroField(
            f"{_T1}.Row{row}[0].f1_{_field_num:02d}[0]",
            format=fmt,
        )
        _field_num += 1

# Part II per-row fields (11 rows, 8 fields each: f2_03..f2_90)
_field_num = 3
for row in range(1, 12):
    for col in _COLS:
        key = f"F8949_P2_R{row}_{col}"
        fmt = "currency" if col in ("proceeds", "cost", "adj", "gain") else None
        FIELD_MAP[key] = AcroField(
            f"{_T2}.Row{row}[0].f2_{_field_num:02d}[0]",
            format=fmt,
        )
        _field_num += 1
