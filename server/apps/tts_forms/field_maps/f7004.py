"""
AcroForm field map for Form 7004 — Application for Automatic Extension
of Time To File (Rev. December 2025).

Template: resources/irs_forms/2025/f7004.pdf (26 AcroForm fields)

Single-page form. Used for S-Corps (code 25), partnerships (code 09),
C-Corps (code 12), and other entity types.
"""

from . import AcroField, FieldMap

_P = "topmostSubform[0].Page1[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP — Entity information at top of form
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    "entity_name": AcroField(f"{_P}.f1_1[0]"),                # Name
    "ein": AcroField(f"{_P}.f1_2[0]"),                        # EIN
    "address_street": AcroField(f"{_P}.f1_3[0]"),             # Street address
    "address_room": AcroField(f"{_P}.f1_4[0]"),               # Room/suite
    "address_city": AcroField(f"{_P}.f1_5[0]"),               # City
    "address_state": AcroField(f"{_P}.f1_6[0]"),              # State
    "address_zip": AcroField(f"{_P}.f1_7[0]"),                # ZIP code
    "address_country": AcroField(f"{_P}.f1_8[0]"),            # Foreign country
}

# ---------------------------------------------------------------------------
# FIELD_MAP — Form body fields
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {
    # Line 1: 2-digit form code (split into two single-digit fields)
    "1a": AcroField(f"{_P}.f1_9[0]"),        # First digit
    "1b": AcroField(f"{_P}.f1_10[0]"),       # Second digit

    # Part II checkboxes (Lines 2-4)
    "2": AcroField(f"{_P}.c1_1[0]", field_type="checkbox"),   # Box 2
    "3": AcroField(f"{_P}.c1_2[0]", field_type="checkbox"),   # Box 3
    "4": AcroField(f"{_P}.c1_3[0]", field_type="checkbox"),   # Box 4

    # Line 5a: Tax year dates
    "5a_year": AcroField(f"{_P}.f1_11[0]"),           # Calendar year
    "5a_begin": AcroField(f"{_P}.f1_12[0]"),          # Begin date (mm/dd)
    "5a_begin_year": AcroField(f"{_P}.f1_13[0]"),     # Begin year (yy)
    "5a_end": AcroField(f"{_P}.f1_14[0]"),            # End date (mm/dd)
    "5a_end_year": AcroField(f"{_P}.f1_15[0]"),       # End year (yy)

    # Line 5b: Short tax year reason checkboxes
    # These are all c1_4 with different array indices
    "5b_initial": AcroField(f"{_P}.c1_4[0]", field_type="checkbox"),
    "5b_final": AcroField(f"{_P}.c1_4[1]", field_type="checkbox"),
    "5b_change": AcroField(f"{_P}.c1_4[2]", field_type="checkbox"),
    "5b_consolidated": AcroField(f"{_P}.c1_4[3]", field_type="checkbox"),
    "5b_other": AcroField(f"{_P}.c1_4[4]", field_type="checkbox"),

    # Lines 6-8: Financial amounts
    "6": AcroField(f"{_P}.f1_16[0]", format="currency"),  # Tentative total tax
    "7": AcroField(f"{_P}.f1_17[0]", format="currency"),  # Total payments/credits
    "8": AcroField(f"{_P}.f1_18[0]", format="currency"),  # Balance due
}
