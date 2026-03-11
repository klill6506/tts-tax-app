"""
AcroForm field map for Form 1125-E -- Compensation of Officers (2025).

Template: resources/irs_forms/2025/f1125e.pdf (125 AcroForm fields)

Single-page form.
Attached to Form 1120, 1120-S, or 1065.

Header: Entity name + EIN
Line 1 table: Up to 20 officer rows, each with 6 columns:
    (a) Name, (b) SSN, (c) % Time devoted, (d) % Stock owned,
    (e) Compensation, (f) Amount from Form 5471
Line 2: Total compensation of officers
Line 3: Compensation claimed on other returns
Line 4: Total compensation deduction (Line 2 minus Line 3)
"""

from . import AcroField, FieldMap

_P = "topmostSubform[0].Page1[0]"
_T = f"{_P}.Line1Table[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP -- Entity identification
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    "entity_name": AcroField(f"{_P}.f1_1[0]"),      # Name
    "ein":         AcroField(f"{_P}.f1_2[0]"),       # EIN
}

# ---------------------------------------------------------------------------
# Helper to build officer row entries
# ---------------------------------------------------------------------------
# Each officer row has 6 AcroForm fields in sequence:
#   (a) Name, (b) SSN, (c) % Time devoted, (d) % Stock owned,
#   (e) Compensation, (f) Amount from Form 5471
#
# Row 1 = BodyRow1, fields f1_3..f1_8
# Row 2 = BodyRow2, fields f1_9..f1_14
# ...
# Row N = BodyRowN, fields f1_{3 + (N-1)*6} .. f1_{8 + (N-1)*6}


def _officer_row(row: int) -> dict[str, AcroField]:
    """Return FIELD_MAP entries for a single officer row (1-based)."""
    base = 3 + (row - 1) * 6  # f1_3 for row 1, f1_9 for row 2, etc.
    prefix = f"{_T}.BodyRow{row}[0]"
    tag = f"E1R{row}"
    return {
        f"{tag}_name":     AcroField(f"{prefix}.f1_{base}[0]",     format="text"),
        f"{tag}_ssn":      AcroField(f"{prefix}.f1_{base + 1}[0]", format="text"),
        f"{tag}_pct_time": AcroField(f"{prefix}.f1_{base + 2}[0]", format="text"),
        f"{tag}_pct_own":  AcroField(f"{prefix}.f1_{base + 3}[0]", format="text"),
        f"{tag}_comp":     AcroField(f"{prefix}.f1_{base + 4}[0]", format="currency"),
        f"{tag}_form5471": AcroField(f"{prefix}.f1_{base + 5}[0]", format="currency"),
    }


# ---------------------------------------------------------------------------
# FIELD_MAP -- Officer rows 1-20 + summary lines 2-4
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {}

# Officer rows 1-20
for _row in range(1, 21):
    FIELD_MAP.update(_officer_row(_row))

# Summary lines
FIELD_MAP.update({
    "E2": AcroField(f"{_P}.f1_123[0]", format="currency"),  # Line 2: Total compensation
    "E3": AcroField(f"{_P}.f1_124[0]", format="currency"),  # Line 3: Comp on other returns
    "E4": AcroField(f"{_P}.f1_125[0]", format="currency"),  # Line 4: Net deduction (L2 - L3)
})
