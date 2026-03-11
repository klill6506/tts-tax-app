"""
AcroForm field map for Form 8949 -- Sales and Other Dispositions of Capital Assets (2025).

Template: resources/irs_forms/2025/f8949.pdf (202 AcroForm fields, 2 pages)

Page 1 — Part I: Short-Term (held one year or less)
  Checkboxes A-F, then up to 14 transaction rows with 8 columns each:
  (a) Description, (b) Date acquired, (c) Date sold, (d) Proceeds,
  (e) Cost basis, (f) Code, (g) Adjustment, (h) Gain/Loss
  Totals line at bottom

Page 2 — Part II: Long-Term (held more than one year)
  Same structure as Part I

TODO: Complete per-transaction row mappings once disposition → 8949 flow is built.
"""

from . import AcroField, FieldMap

_P1 = "topmostSubform[0].Page1[0]"
_P2 = "topmostSubform[0].Page2[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP -- Entity identification
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    "entity_name": AcroField(f"{_P1}.f1_01[0]"),
    "ein":         AcroField(f"{_P1}.f1_02[0]"),
}

# ---------------------------------------------------------------------------
# FIELD_MAP -- Checkboxes + totals (per-row detail TBD)
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {
    # Part I checkboxes (which box on 1099-B)
    "F8949_P1_A": AcroField(f"{_P1}.c1_1[0]", field_type="checkbox", format="boolean"),
    "F8949_P1_B": AcroField(f"{_P1}.c1_1[1]", field_type="checkbox", format="boolean"),
    "F8949_P1_C": AcroField(f"{_P1}.c1_1[2]", field_type="checkbox", format="boolean"),

    # Part II checkboxes
    "F8949_P2_D": AcroField(f"{_P2}.c2_1[0]", field_type="checkbox", format="boolean"),
    "F8949_P2_E": AcroField(f"{_P2}.c2_1[1]", field_type="checkbox", format="boolean"),
    "F8949_P2_F": AcroField(f"{_P2}.c2_1[2]", field_type="checkbox", format="boolean"),
}
