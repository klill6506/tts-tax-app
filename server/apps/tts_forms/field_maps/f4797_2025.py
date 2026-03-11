"""
AcroForm field map for Form 4797 -- Sales of Business Property (2025).

Template: resources/irs_forms/2025/f4797.pdf (182 AcroForm fields, 2 pages)

Part I: Sales or Exchanges of Property Used in a Trade or Business (Section 1231)
Part II: Ordinary Gains and Losses (Lines 10-18)
Part III: Gain from Disposition of Property Under Sections 1245, 1250, etc. (Lines 19-25b)
Part IV: Recapture Amounts (Lines 26-29)

TODO: Complete field map with all line mappings once disposition flow is built.
"""

from . import AcroField, FieldMap

_P1 = "topmostSubform[0].Page1[0]"
_P2 = "topmostSubform[0].Page2[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP -- Entity identification
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    "entity_name": AcroField(f"{_P1}.f1_1[0]"),
    "ein":         AcroField(f"{_P1}.f1_2[0]"),
}

# ---------------------------------------------------------------------------
# FIELD_MAP -- Summary lines only (detailed row mapping TBD)
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {
    # Part I summary lines
    "P4797_3":  AcroField(f"{_P1}.f1_34[0]", format="currency"),   # Line 3: gain if any
    "P4797_4":  AcroField(f"{_P1}.f1_35[0]", format="currency"),   # Line 4: Section 1231 gain
    "P4797_5":  AcroField(f"{_P1}.f1_36[0]", format="currency"),   # Line 5
    "P4797_6":  AcroField(f"{_P1}.f1_37[0]", format="currency"),   # Line 6: gain
    "P4797_7":  AcroField(f"{_P1}.f1_38[0]", format="currency"),   # Line 7: net gain

    # Part II summary lines
    "P4797_13": AcroField(f"{_P1}.f1_39[0]", format="currency"),   # Line 13: gain from Form 4684
    "P4797_15": AcroField(f"{_P1}.f1_40[0]", format="currency"),   # Line 15: total
    "P4797_17": AcroField(f"{_P1}.f1_76[0]", format="currency"),   # Line 17: ordinary gain
    "P4797_18": AcroField(f"{_P1}.f1_77[0]", format="currency"),   # Line 18: recombine
}
