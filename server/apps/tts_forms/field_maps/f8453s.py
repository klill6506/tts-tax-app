"""
AcroForm field map for Form 8453-S — U.S. S Corporation Income Tax
Declaration for an IRS e-file Return (Rev. 2021).

Template: resources/irs_forms/2025/f8453s.pdf (28 AcroForm fields)

Single-page form (page 2 is instructions only).
Used by S-Corps when not using PIN-based signing (8879-S).

Layout:
    Header: Tax year dates, corp name, EIN
    Part I: Lines 1-5 (financial amounts from 1120-S)
    Part II: Declaration of Officer (checkboxes 6a/6b/6c + signature)
    Part III: ERO and Paid Preparer declaration
"""

from . import AcroField, FieldMap

_P = "topmostSubform[0].Page1[0]"

# ---------------------------------------------------------------------------
# HEADER_MAP — Tax year + entity identification
# ---------------------------------------------------------------------------

HEADER_MAP: FieldMap = {
    # Tax year header
    "tax_year_begin": AcroField(f"{_P}.PgHeader[0].f1_1[0]"),   # Begin date
    "tax_year_end": AcroField(f"{_P}.PgHeader[0].f1_2[0]"),     # End date
    "tax_year_end_year": AcroField(f"{_P}.PgHeader[0].f1_3[0]"),  # End year (2-digit)
    # Entity info
    "entity_name": AcroField(f"{_P}.f1_4[0]"),                  # Name of corporation
    "ein": AcroField(f"{_P}.f1_5[0]"),                          # EIN
}

# ---------------------------------------------------------------------------
# FIELD_MAP — Part I financial lines + Part II/III fields
# ---------------------------------------------------------------------------

FIELD_MAP: FieldMap = {
    # Part I — Tax Return Information (whole dollars only)
    "1": AcroField(f"{_P}.f1_6[0]", format="currency"),     # Gross receipts (1120-S line 1c)
    "2": AcroField(f"{_P}.f1_7[0]", format="currency"),     # Gross profit (line 3)
    "3": AcroField(f"{_P}.f1_8[0]", format="currency"),     # Ordinary business income (line 21)
    "4": AcroField(f"{_P}.f1_9[0]", format="currency"),     # Net rental real estate (Sched K line 2)
    "5": AcroField(f"{_P}.f1_10[0]", format="currency"),    # Income reconciliation (Sched K line 18)

    # Part II — Declaration of Officer (checkboxes)
    "6a": AcroField(f"{_P}.c1_1[0]", field_type="checkbox"),  # Direct deposit consent
    "6b": AcroField(f"{_P}.c1_1[1]", field_type="checkbox"),  # No direct deposit
    "6c": AcroField(f"{_P}.c1_1[2]", field_type="checkbox"),  # EFW authorization

    # Officer signature date field
    "officer_date": AcroField(f"{_P}.f1_11[0]"),             # Date

    # Part III — ERO section
    "chk_paid_preparer": AcroField(f"{_P}.c1_2[0]", field_type="checkbox"),  # Check if also paid preparer
    "chk_self_employed": AcroField(f"{_P}.c1_3[0]", field_type="checkbox"),  # Check if self-employed
    "ero_ssn_ptin": AcroField(f"{_P}.f1_12[0]"),            # ERO's SSN or PTIN
    "ero_firm_name": AcroField(f"{_P}.f1_13[0]"),           # Firm name line 1
    "ero_firm_address": AcroField(f"{_P}.f1_14[0]"),        # Firm address
    "ero_ein": AcroField(f"{_P}.f1_15[0]"),                 # Firm EIN
    "ero_phone": AcroField(f"{_P}.f1_16[0]"),               # Firm phone

    # Paid Preparer section
    "preparer_name": AcroField(f"{_P}.f1_17[0]"),           # Preparer's name
    "preparer_self_employed": AcroField(f"{_P}.c1_4[0]", field_type="checkbox"),
    "preparer_ptin": AcroField(f"{_P}.f1_18[0]"),           # Preparer PTIN
    "preparer_firm_name": AcroField(f"{_P}.f1_19[0]"),      # Firm name
    "preparer_firm_address": AcroField(f"{_P}.f1_20[0]"),   # Firm address
    "preparer_firm_ein": AcroField(f"{_P}.f1_21[0]"),       # Firm EIN
    "preparer_phone": AcroField(f"{_P}.f1_22[0]"),          # Phone
}
