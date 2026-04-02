"""
AcroForm field map for Form 8879-S — IRS e-file Signature Authorization
for Form 1120-S (Rev. 2021).

Template: resources/irs_forms/2025/f8879s.pdf (16 AcroForm fields)

Single-page form (page 2 is instructions only).
Used by S-Corps for e-file PIN-based signature authorization.

Layout:
    Header: Tax year dates, corp name, EIN
    Part I: Lines 1-5 (financial amounts from 1120-S)
    Part II: Officer PIN authorization (checkbox + ERO name + PIN)
    Part III: ERO EFIN/PIN certification
"""

from . import AcroField, FieldMap

_P = "topmostSubform[0].Page1[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP — Tax year + entity identification
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    # Tax year header
    "tax_year_begin": AcroField(f"{_P}.f1_01[0]"),          # Begin date
    "tax_year_end": AcroField(f"{_P}.f1_02[0]"),            # End date
    "tax_year_end_year": AcroField(f"{_P}.f1_03[0]"),       # End year (2-digit)
    # Entity info
    "entity_name": AcroField(f"{_P}.f1_04[0]"),             # Name of corporation
    "ein": AcroField(f"{_P}.f1_05[0]"),                     # EIN
}

# ---------------------------------------------------------------------------
# FIELD_MAP — Part I financial lines + Part II/III fields
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {
    # Part I — Tax Return Information (whole dollars only)
    "1": AcroField(f"{_P}.f1_06[0]", format="currency"),    # Gross receipts (1120-S line 1c)
    "2": AcroField(f"{_P}.f1_07[0]", format="currency"),    # Gross profit (line 3)
    "3": AcroField(f"{_P}.f1_08[0]", format="currency"),    # Ordinary business income (line 21)
    "4": AcroField(f"{_P}.f1_09[0]", format="currency"),    # Net rental real estate (Sched K line 2)
    "5": AcroField(f"{_P}.f1_10[0]", format="currency"),    # Income reconciliation (Sched K line 18)

    # Part II — Officer's PIN authorization
    "chk_authorize_ero": AcroField(f"{_P}.c1_1[0]", field_type="checkbox"),  # I authorize ERO
    "ero_firm_name": AcroField(f"{_P}.f1_11[0]"),           # ERO firm name
    "officer_pin": AcroField(f"{_P}.CombField1[0].f1_12[0]", is_comb=True, max_chars=5),  # Officer's 5-digit PIN
    "chk_officer_enters": AcroField(f"{_P}.c1_1[1]", field_type="checkbox"),  # Officer enters PIN

    # Part III — ERO EFIN/PIN
    "ero_efin_pin": AcroField(f"{_P}.f1_13[0]"),            # 11-digit EFIN+PIN

    # Officer signature fields
    "officer_date": AcroField(f"{_P}.CombField2[0].f1_14[0]", is_comb=True, max_chars=10),  # Date MM/DD/YYYY
}
