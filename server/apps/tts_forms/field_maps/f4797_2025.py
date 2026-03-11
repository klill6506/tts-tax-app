"""
AcroForm field map for Form 4797 -- Sales of Business Property (2025).

Template: resources/irs_forms/2025/f4797.pdf (182 AcroForm fields, 2 pages)

Part I: Sales or Exchanges of Property Used in a Trade or Business (Section 1231)
Part II: Ordinary Gains and Losses (Lines 10-18)
Part III: Gain from Disposition of Property Under Sections 1245, 1250, etc.
Part IV: Recapture Amounts Under Sections 179 and 280F(b)(2)
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
# Helpers for row-based tables
# ---------------------------------------------------------------------------

_TBL2 = f"{_P1}.TableLine2[0]"    # Part I, Line 2 table
_TBL10 = f"{_P1}.TableLine10[0]"  # Part II, Line 10 table
_PT3T1 = f"{_P2}.PartIIITable1[0]"  # Part III header table (Lines 19)
_PT3T2 = f"{_P2}.PartIIITable2[0]"  # Part III detail table (Lines 20-29)
_PT4 = f"{_P2}.PartIVTable[0]"      # Part IV table (Lines 33-35)


def _part1_row(row: int) -> dict[str, AcroField]:
    """Part I Line 2 table: 4 rows x 7 cols.
    (a) Description, (b) Date acquired, (c) Date sold,
    (d) Gross sales price, (e) Depreciation allowed,
    (f) Cost or basis, (g) Gain or (loss).
    Row 1: f1_6..f1_12, Row 2: f1_13..f1_19, Row 3: f1_20..f1_26, Row 4: f1_27..f1_33
    """
    base = 6 + (row - 1) * 7
    prefix = f"{_TBL2}.Row{row}[0]"
    tag = f"P1_2R{row}"
    return {
        f"{tag}_desc":     AcroField(f"{prefix}.f1_{base}[0]"),
        f"{tag}_acquired": AcroField(f"{prefix}.f1_{base + 1}[0]"),
        f"{tag}_sold":     AcroField(f"{prefix}.f1_{base + 2}[0]"),
        f"{tag}_gross":    AcroField(f"{prefix}.f1_{base + 3}[0]", format="currency"),
        f"{tag}_depr":     AcroField(f"{prefix}.f1_{base + 4}[0]", format="currency"),
        f"{tag}_cost":     AcroField(f"{prefix}.f1_{base + 5}[0]", format="currency"),
        f"{tag}_gain":     AcroField(f"{prefix}.f1_{base + 6}[0]", format="currency"),
    }


def _part2_row(row: int) -> dict[str, AcroField]:
    """Part II Line 10 table: 4 rows x 7 cols (same layout as Part I).
    Row 1: f1_41..f1_47, Row 2: f1_48..f1_54, Row 3: f1_55..f1_61, Row 4: f1_62..f1_68
    """
    base = 41 + (row - 1) * 7
    prefix = f"{_TBL10}.Row{row}[0]"
    tag = f"P2_10R{row}"
    return {
        f"{tag}_desc":     AcroField(f"{prefix}.f1_{base}[0]"),
        f"{tag}_acquired": AcroField(f"{prefix}.f1_{base + 1}[0]"),
        f"{tag}_sold":     AcroField(f"{prefix}.f1_{base + 2}[0]"),
        f"{tag}_gross":    AcroField(f"{prefix}.f1_{base + 3}[0]", format="currency"),
        f"{tag}_depr":     AcroField(f"{prefix}.f1_{base + 4}[0]", format="currency"),
        f"{tag}_cost":     AcroField(f"{prefix}.f1_{base + 5}[0]", format="currency"),
        f"{tag}_gain":     AcroField(f"{prefix}.f1_{base + 6}[0]", format="currency"),
    }


def _part3_header_row(row: int) -> dict[str, AcroField]:
    """Part III Table 1 (Lines 19): 4 rows x 3 cols.
    (a) Description, (b) Date acquired, (c) Date sold.
    Row 1: f2_1..f2_3, Row 2: f2_4..f2_6, Row 3: f2_7..f2_9, Row 4: f2_10..f2_12
    """
    base = 1 + (row - 1) * 3
    prefix = f"{_PT3T1}.Row{row}[0]"
    tag = f"P3_19R{row}"
    return {
        f"{tag}_desc":     AcroField(f"{prefix}.f2_{base}[0]"),
        f"{tag}_acquired": AcroField(f"{prefix}.f2_{base + 1}[0]"),
        f"{tag}_sold":     AcroField(f"{prefix}.f2_{base + 2}[0]"),
    }


# ---------------------------------------------------------------------------
# FIELD_MAP
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {}

# Part I header lines
FIELD_MAP.update({
    "P4797_1": AcroField(f"{_P1}.f1_3[0]", format="currency"),  # Line 1: Gain from Form 6252
    "P4797_4": AcroField(f"{_P1}.f1_4[0]", format="currency"),  # Line 4: Section 1231 gain from installment
    "P4797_5": AcroField(f"{_P1}.f1_5[0]", format="currency"),  # Line 5: Like-kind exchange gain
})

# Part I Line 2 detail table (4 rows)
for _row in range(1, 5):
    FIELD_MAP.update(_part1_row(_row))

# Part I summary lines
FIELD_MAP.update({
    "P4797_3":  AcroField(f"{_P1}.f1_34[0]", format="currency"),  # Line 3: Gain if any from line 2
    "P4797_6":  AcroField(f"{_P1}.f1_35[0]", format="currency"),  # Line 6: Gain
    "P4797_6b": AcroField(f"{_P1}.f1_36[0]", format="currency"),  # Line 6b
    "P4797_6c": AcroField(f"{_P1}.f1_37[0]", format="currency"),  # Line 6c
    "P4797_7":  AcroField(f"{_P1}.f1_38[0]", format="currency"),  # Line 7: Net section 1231 gain (loss)
})

# Part II header lines
FIELD_MAP.update({
    "P4797_9":  AcroField(f"{_P1}.f1_39[0]", format="currency"),  # Line 9: Losses from casualties
    "P4797_11": AcroField(f"{_P1}.f1_40[0]", format="currency"),  # Line 11: Loss from Form 4797
})

# Part II Line 10 detail table (4 rows)
for _row in range(1, 5):
    FIELD_MAP.update(_part2_row(_row))

# Part II summary lines
FIELD_MAP.update({
    "P4797_12": AcroField(f"{_P1}.f1_69[0]", format="currency"),  # Line 12: skip line
    "P4797_13": AcroField(f"{_P1}.f1_70[0]", format="currency"),  # Line 13: Gain from Form 4684
    "P4797_14": AcroField(f"{_P1}.f1_71[0]", format="currency"),  # Line 14: Net gain
    "P4797_15": AcroField(f"{_P1}.f1_72[0]", format="currency"),  # Line 15: Add lines 12-14
    "P4797_16a": AcroField(f"{_P1}.f1_73[0]", format="currency"), # Line 16a
    "P4797_16b": AcroField(f"{_P1}.f1_74[0]", format="currency"), # Line 16b
    "P4797_16c": AcroField(f"{_P1}.f1_75[0]", format="currency"), # Line 16c
    "P4797_17": AcroField(f"{_P1}.f1_76[0]", format="currency"),  # Line 17: Ordinary gains
    "P4797_18": AcroField(f"{_P1}.f1_77[0]", format="currency"),  # Line 18: combined
})

# Part III: Section 1245/1250 Recapture
# Header table (Lines 19a-d: property descriptions)
for _row in range(1, 5):
    FIELD_MAP.update(_part3_header_row(_row))

# Part III detail table (Lines 20-29, 4 property columns a-d)
# Each line has 4 fields (one per property column)
_PT3_LINES = {
    "20": ("f2_13", "f2_14", "f2_15", "f2_16"),   # Line 20: Gross sales price
    "21": ("f2_17", "f2_18", "f2_19", "f2_20"),   # Line 21: Cost or basis + expenses
    "22": ("f2_21", "f2_22", "f2_23", "f2_24"),   # Line 22: Depreciation allowed
    "23": ("f2_25", "f2_26", "f2_27", "f2_28"),   # Line 23: Adjusted basis (L21 - L22)
    "24": ("f2_29", "f2_30", "f2_31", "f2_32"),   # Line 24: Total gain (L20 - L23)
    "25a": ("f2_33", "f2_34", "f2_35", "f2_36"),  # Line 25a: Section 1245 property
    "25b": ("f2_37", "f2_38", "f2_39", "f2_40"),  # Line 25b: Section 1250 property
    "26a": ("f2_41", "f2_42", "f2_43", "f2_44"),  # Line 26a
    "26b": ("f2_45", "f2_46", "f2_47", "f2_48"),  # Line 26b
    "26c": ("f2_49", "f2_50", "f2_51", "f2_52"),  # Line 26c
    "26d": ("f2_53", "f2_54", "f2_55", "f2_56"),  # Line 26d
    "26e": ("f2_57", "f2_58", "f2_59", "f2_60"),  # Line 26e
    "26f": ("f2_61", "f2_62", "f2_63", "f2_64"),  # Line 26f
    "26g": ("f2_65", "f2_66", "f2_67", "f2_68"),  # Line 26g
    "27a": ("f2_69", "f2_70", "f2_71", "f2_72"),  # Line 27a
    "27b": ("f2_73", "f2_74", "f2_75", "f2_76"),  # Line 27b
    "27c": ("f2_77", "f2_78", "f2_79", "f2_80"),  # Line 27c
    "28a": ("f2_81", "f2_82", "f2_83", "f2_84"),  # Line 28a
    "28b": ("f2_85", "f2_86", "f2_87", "f2_88"),  # Line 28b
    "29a": ("f2_89", "f2_90", "f2_91", "f2_92"),  # Line 29a: Section 1231 gain
    "29b": ("f2_93", "f2_94", "f2_95", "f2_96"),  # Line 29b
}

for line, (fa, fb, fc, fd) in _PT3_LINES.items():
    row_name = f"Row{line}"
    FIELD_MAP[f"P3_{line}_a"] = AcroField(f"{_PT3T2}.{row_name}[0].{fa}[0]", format="currency")
    FIELD_MAP[f"P3_{line}_b"] = AcroField(f"{_PT3T2}.{row_name}[0].{fb}[0]", format="currency")
    FIELD_MAP[f"P3_{line}_c"] = AcroField(f"{_PT3T2}.{row_name}[0].{fc}[0]", format="currency")
    FIELD_MAP[f"P3_{line}_d"] = AcroField(f"{_PT3T2}.{row_name}[0].{fd}[0]", format="currency")

# Part III summary
FIELD_MAP.update({
    "P4797_30": AcroField(f"{_P2}.f2_97[0]", format="currency"),   # Line 30: Total gains
    "P4797_31": AcroField(f"{_P2}.f2_98[0]", format="currency"),   # Line 31
    "P4797_32": AcroField(f"{_P2}.f2_99[0]", format="currency"),   # Line 32
})

# Part IV: Recapture Amounts (Lines 33-35, 2 columns each)
FIELD_MAP.update({
    "P4797_33a": AcroField(f"{_PT4}.Row33[0].f2_100[0]", format="currency"),
    "P4797_33b": AcroField(f"{_PT4}.Row33[0].f2_101[0]", format="currency"),
    "P4797_34a": AcroField(f"{_PT4}.Row34[0].f2_102[0]", format="currency"),
    "P4797_34b": AcroField(f"{_PT4}.Row34[0].f2_103[0]", format="currency"),
    "P4797_35a": AcroField(f"{_PT4}.Row35[0].f2_104[0]", format="currency"),
    "P4797_35b": AcroField(f"{_PT4}.Row35[0].f2_105[0]", format="currency"),
})
