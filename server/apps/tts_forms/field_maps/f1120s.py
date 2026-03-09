"""
AcroForm field map for IRS Form 1120-S (2025 fillable PDF).

Maps our internal line_number / header keys to the AcroForm field names
in the official IRS fillable PDF (f1120s_fillable.pdf).

Cross-referenced from:
    - resources/irs_forms/2025/f1120s_fillable.fields.json (390 AcroForm fields)
    - server/apps/tts_forms/coordinates/f1120s.py (our coordinate map)

AcroForm field naming convention:
    - Text fields: f{page}_{seq}  (e.g., f1_17 = page 1, field 17)
    - Checkboxes:  c{page}_{seq}  (e.g., c1_3 = page 1, checkbox 3)
    - Full names:  topmostSubform[0].Page{n}[0].{field}[{idx}]
    - Pages in the PDF are 1-indexed (Page1 = our page 0)

PDF page structure (5 pages):
    Page 0 (Page1): Header + Income (1a-6) + Deductions (7-21) + Tax (22-28) + Preparer
    Page 1 (Page2): Schedule B -- Other Information (yes/no questions)
    Page 2 (Page3): Schedule B continued (top) + Schedule K lines 1-16 (bottom)
    Page 3 (Page4): Schedule K continued (17-18) + Schedule L balance sheet
    Page 4 (Page5): Schedule M-1 + Schedule M-2
"""

from . import AcroField, FieldMap

# ============================================================================
# HEADER_MAP -- Entity info, checkboxes, and preparer section (page 0)
# ============================================================================
HEADER_MAP: FieldMap = {
    # -------------------------------------------------------------------
    # Tax Year / Calendar Year header (very top of form)
    # -------------------------------------------------------------------
    # f1_1: "For calendar year" date range left part (e.g., "2025")
    "tax_year_begin": AcroField(
        acro_name="topmostSubform[0].Page1[0].Date_Name_ReadOrder[0].f1_1[0]",
        field_type="text", format="text",
    ),
    # f1_2: "or tax year beginning" date
    "tax_year_end_month": AcroField(
        acro_name="topmostSubform[0].Page1[0].Date_Name_ReadOrder[0].f1_2[0]",
        field_type="text", format="text",
    ),
    # f1_3: ", ending" year
    "tax_year_end_year": AcroField(
        acro_name="topmostSubform[0].Page1[0].Date_Name_ReadOrder[0].f1_3[0]",
        field_type="text", format="text",
    ),

    # -------------------------------------------------------------------
    # Entity info -- left side (A, B, C)
    # -------------------------------------------------------------------
    # A -- Name of corporation
    "entity_name": AcroField(
        acro_name="topmostSubform[0].Page1[0].Date_Name_ReadOrder[0].f1_4[0]",
        field_type="text", format="text",
    ),
    # B -- Number, street, and room or suite no.
    "address_street": AcroField(
        acro_name="topmostSubform[0].Page1[0].Date_Name_ReadOrder[0].f1_5[0]",
        field_type="text", format="text",
    ),
    # B continued -- suite number area (right of street)
    "address_suite": AcroField(
        acro_name="topmostSubform[0].Page1[0].Date_Name_ReadOrder[0].f1_6[0]",
        field_type="text", format="text",
    ),
    # C -- City or town
    "address_city": AcroField(
        acro_name="topmostSubform[0].Page1[0].Date_Name_ReadOrder[0].f1_7[0]",
        field_type="text", format="text",
    ),
    # C -- State
    "address_state": AcroField(
        acro_name="topmostSubform[0].Page1[0].Date_Name_ReadOrder[0].f1_8[0]",
        field_type="text", format="text",
    ),
    # C -- Country (for foreign addresses; IRS order is City, State, Country, ZIP)
    "address_country": AcroField(
        acro_name="topmostSubform[0].Page1[0].Date_Name_ReadOrder[0].f1_9[0]",
        field_type="text", format="text",
    ),
    # C -- ZIP code (rightmost field on line C)
    "address_zip": AcroField(
        acro_name="topmostSubform[0].Page1[0].Date_Name_ReadOrder[0].f1_10[0]",
        field_type="text", format="text",
    ),

    # -------------------------------------------------------------------
    # Left sidebar -- A, B fields
    # -------------------------------------------------------------------
    # A -- S election effective date
    "s_election_date": AcroField(
        acro_name="topmostSubform[0].Page1[0].ABC[0].f1_11[0]",
        field_type="text", format="text",
    ),
    # B -- Business activity code number
    "business_activity_code": AcroField(
        acro_name="topmostSubform[0].Page1[0].ABC[0].f1_12[0]",
        field_type="text", format="text",
    ),
    # Checkbox next to B -- "Check if Sch. M-3 attached"
    "chk_s_election": AcroField(
        acro_name="topmostSubform[0].Page1[0].ABC[0].c1_1[0]",
        field_type="checkbox", format="boolean",
    ),

    # -------------------------------------------------------------------
    # Entity info -- right side (D, E, F)
    # -------------------------------------------------------------------
    # D -- Employer identification number (EIN)
    "ein": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_13[0]",
        field_type="text", format="text",
    ),
    # E -- Date incorporated
    "date_incorporated": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_14[0]",
        field_type="text", format="text",
    ),
    # F -- Total assets (end of tax year)
    "total_assets": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_15[0]",
        field_type="text", format="currency",
    ),

    # -------------------------------------------------------------------
    # Line G -- Type of return (checkboxes)
    # c1_2[0] = Initial return, c1_2[1] = Final return
    # (these share the same short_name but different indices)
    # -------------------------------------------------------------------
    "chk_initial_return": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_2[0]",
        field_type="checkbox", format="boolean",
    ),
    "chk_final_return_g": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_2[1]",
        field_type="checkbox", format="boolean",
    ),

    # -------------------------------------------------------------------
    # Line H -- Check boxes (final return, name change, etc.)
    # -------------------------------------------------------------------
    "chk_final_return": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_3[0]",
        field_type="checkbox", format="boolean",
    ),
    "chk_name_change": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_4[0]",
        field_type="checkbox", format="boolean",
    ),
    "chk_address_change": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_5[0]",
        field_type="checkbox", format="boolean",
    ),
    "chk_amended_return": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_6[0]",
        field_type="checkbox", format="boolean",
    ),
    # S election termination or revocation checkbox
    "chk_s_election_termination": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_7[0]",
        field_type="checkbox", format="boolean",
    ),

    # f1_16: number of shareholders (text field right of H checkboxes)
    "number_of_shareholders": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_16[0]",
        field_type="text", format="integer",
    ),

    # -------------------------------------------------------------------
    # Line I -- Check if entity electing to be an S corporation
    # c1_8[0] = Cash method, c1_8[1] = Accrual method
    # -------------------------------------------------------------------
    "chk_accounting_cash": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_8[0]",
        field_type="checkbox", format="boolean",
    ),
    "chk_accounting_accrual": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_8[1]",
        field_type="checkbox", format="boolean",
    ),

    # -------------------------------------------------------------------
    # Sign Here / Third Party Designee (bottom of page 0)
    # -------------------------------------------------------------------
    # Third party designee name
    "designee_name": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_56[0]",
        field_type="text", format="text",
    ),
    # May IRS discuss with preparer? Yes / No
    "chk_discuss_yes": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_11[0]",
        field_type="checkbox", format="boolean",
    ),
    "chk_discuss_no": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_11[1]",
        field_type="checkbox", format="boolean",
    ),

    # -------------------------------------------------------------------
    # Paid Preparer Use Only (very bottom of page 0)
    # -------------------------------------------------------------------
    # Preparer's self-employed checkbox
    "preparer_self_employed": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_12[0]",
        field_type="checkbox", format="boolean",
    ),
    # Preparer's name
    "preparer_name": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_57[0]",
        field_type="text", format="text",
    ),
    # Preparer's PTIN
    "preparer_ptin": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_58[0]",
        field_type="text", format="text",
    ),
    # Firm's name
    "firm_name": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_59[0]",
        field_type="text", format="text",
    ),
    # Firm's EIN
    "firm_ein": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_60[0]",
        field_type="text", format="text",
    ),
    # Firm's address
    "firm_address": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_61[0]",
        field_type="text", format="text",
    ),
    # Firm's phone number
    "firm_phone": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_62[0]",
        field_type="text", format="text",
    ),

    # -------------------------------------------------------------------
    # Direct deposit / Electronic funds withdrawal (lines 24d area)
    # -------------------------------------------------------------------
    # Routing number
    "routing_number": AcroField(
        acro_name="topmostSubform[0].Page1[0].Routing_Number[0].f1_54[0]",
        field_type="text", format="text",
    ),
    # Account type: Checking / Savings
    "chk_account_checking": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_10[0]",
        field_type="checkbox", format="boolean",
    ),
    "chk_account_savings": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_10[1]",
        field_type="checkbox", format="boolean",
    ),
    # Account number
    "account_number": AcroField(
        acro_name="topmostSubform[0].Page1[0].Account_Number[0].f1_55[0]",
        field_type="text", format="text",
    ),

    # -------------------------------------------------------------------
    # Schedule B Line 2 (page 2) -- business activity / product or service
    # These are entity-level fields, not FormFieldValue-based, so they
    # live in HEADER_MAP and are populated from _build_header_data().
    # -------------------------------------------------------------------
    "B2_business_activity": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_1[0]",
        field_type="text", format="text",
    ),
    "B2_product_service": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_2[0]",
        field_type="text", format="text",
    ),
}


# ============================================================================
# FIELD_MAP -- All form line values (income, deductions, tax, schedules)
# ============================================================================
FIELD_MAP: FieldMap = {

    # ======================================================================
    # PAGE 0 -- Income (Lines 1a through 6)
    # ======================================================================
    # Line 1a -- Gross receipts or sales (sub-column, left)
    "1a": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_17[0]",
        field_type="text", format="currency",
    ),
    # Line 1b -- Returns and allowances (sub-column, middle)
    "1b": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_18[0]",
        field_type="text", format="currency",
    ),
    # Line 1c -- Balance (main column)
    "1c": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_19[0]",
        field_type="text", format="currency",
    ),
    # Line 2 -- Cost of goods sold (attach Form 1125-A)
    "2": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_20[0]",
        field_type="text", format="currency",
    ),
    # Line 3 -- Gross profit
    "3": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_21[0]",
        field_type="text", format="currency",
    ),
    # Line 4 -- Net gain (loss) from Form 4797
    "4": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_22[0]",
        field_type="text", format="currency",
    ),
    # Line 5 -- Other income (loss)
    "5": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_23[0]",
        field_type="text", format="currency",
    ),
    # Line 6 -- Total income (loss)
    "6": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_24[0]",
        field_type="text", format="currency",
    ),

    # ======================================================================
    # PAGE 0 -- Deductions (Lines 7 through 21)
    # ======================================================================
    # Line 7 -- Compensation of officers
    "7": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_25[0]",
        field_type="text", format="currency",
    ),
    # Line 8 -- Salaries and wages
    "8": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_26[0]",
        field_type="text", format="currency",
    ),
    # Line 9 -- Repairs and maintenance
    "9": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_27[0]",
        field_type="text", format="currency",
    ),
    # Line 10 -- Bad debts
    "10": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_28[0]",
        field_type="text", format="currency",
    ),
    # Line 11 -- Rents
    "11": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_29[0]",
        field_type="text", format="currency",
    ),
    # Line 12 -- Taxes and licenses
    "12": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_30[0]",
        field_type="text", format="currency",
    ),
    # Line 13 -- Interest
    "13": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_31[0]",
        field_type="text", format="currency",
    ),
    # Line 14 -- Depreciation
    "14": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_32[0]",
        field_type="text", format="currency",
    ),
    # Line 15 -- Depletion
    "15": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_33[0]",
        field_type="text", format="currency",
    ),
    # Line 16 -- Advertising
    "16": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_34[0]",
        field_type="text", format="currency",
    ),
    # Line 17 -- Pension, profit-sharing, etc. plans
    "17": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_35[0]",
        field_type="text", format="currency",
    ),
    # Line 18 -- Employee benefit programs
    "18": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_36[0]",
        field_type="text", format="currency",
    ),
    # Line 19 -- Other deductions (attach statement)
    "19": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_37[0]",
        field_type="text", format="currency",
    ),
    # Line 20 -- Total deductions
    "20": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_38[0]",
        field_type="text", format="currency",
    ),
    # Line 21 -- Ordinary business income (loss)
    "21": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_39[0]",
        field_type="text", format="currency",
    ),

    # ======================================================================
    # PAGE 0 -- Tax and Payments (Lines 22 through 28)
    # ======================================================================
    # Line 22 -- Excess net passive income or LIFO recapture tax
    "22": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_40[0]",
        field_type="text", format="currency",
    ),
    # Line 23a -- Tax from Schedule D (sub-column)
    "23a": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_41[0]",
        field_type="text", format="currency",
    ),
    # Line 23b -- Built-in gains tax (sub-column)
    "23b": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_42[0]",
        field_type="text", format="currency",
    ),
    # Line 23c -- Add lines 23a and 23b (main column)
    "23c": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_43[0]",
        field_type="text", format="currency",
    ),
    # Line 24 -- 2025 estimated tax payments (sub-column)
    "24": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_44[0]",
        field_type="text", format="currency",
    ),
    # Line 24b -- Tax deposited with Form 7004 (sub-column)
    "24b": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_45[0]",
        field_type="text", format="currency",
    ),
    # Line 24c -- Credit for federal tax paid on fuels (sub-column)
    "24c": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_46[0]",
        field_type="text", format="currency",
    ),
    # Line 24d -- Total payments (add 24a through 24c) (sub-column total)
    "24d": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_47[0]",
        field_type="text", format="currency",
    ),
    # Line 25 -- Estimated tax penalty (main column)
    "25": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_48[0]",
        field_type="text", format="currency",
    ),
    # c1_9 -- Form 2220 attached checkbox (near line 25)
    "chk_form_2220": AcroField(
        acro_name="topmostSubform[0].Page1[0].c1_9[0]",
        field_type="checkbox", format="boolean",
    ),
    # Line 26 -- Amount owed
    "26": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_49[0]",
        field_type="text", format="currency",
    ),
    # Line 27 -- Overpayment
    "27": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_50[0]",
        field_type="text", format="currency",
    ),
    # Line 28 -- Overpayment: credited to next year est. tax (left part)
    "28_credited": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_52[0]",
        field_type="text", format="currency",
    ),
    # Line 28 -- Overpayment: refunded (right part, main column)
    "28": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_51[0]",
        field_type="text", format="currency",
    ),
    # Line 28 continued -- refund amount (main column)
    "28_refunded": AcroField(
        acro_name="topmostSubform[0].Page1[0].f1_53[0]",
        field_type="text", format="currency",
    ),

    # ======================================================================
    # PAGES 1-2 -- Schedule B (Other Information, yes/no questions)
    #
    # The IRS fillable uses paired checkboxes for yes/no:
    #   [0] = "Yes" (on_state="1"), [1] = "No" (on_state="2")
    # ======================================================================

    # --- Page 1 (PDF page 2) ---

    # Schedule B Line 1 -- accounting method (checkboxes at top of page)
    # c2_1[0] = Cash, c2_1[1] = Accrual, c2_1[2] = Other
    "B1_cash": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_1[0]",
        field_type="checkbox", format="boolean",
    ),
    "B1_accrual": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_1[1]",
        field_type="checkbox", format="boolean",
    ),
    "B1_other": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_1[2]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 2 -- B2_business_activity and B2_product_service
    # moved to HEADER_MAP (populated from entity/return model, not FormFieldValues)

    # Schedule B Line 3 -- yes/no
    "B3_yes": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_2[0]",
        field_type="checkbox", format="boolean",
    ),
    "B3_no": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_2[1]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 4a -- yes/no (shareholder owns 25% or more)
    "B4a_yes": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_3[0]",
        field_type="checkbox", format="boolean",
    ),
    "B4a_no": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_3[1]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 4a -- shareholder table (4 rows x 5 columns)
    # Row 1
    "B4a_r1_name": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow1[0].f2_4[0]",
        field_type="text", format="text",
    ),
    "B4a_r1_ssn": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow1[0].f2_5[0]",
        field_type="text", format="text",
    ),
    "B4a_r1_country": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow1[0].f2_6[0]",
        field_type="text", format="text",
    ),
    "B4a_r1_pct": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow1[0].f2_7[0]",
        field_type="text", format="percentage",
    ),
    "B4a_r1_tax_yr_end": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow1[0].f2_8[0]",
        field_type="text", format="text",
    ),
    # Row 2
    "B4a_r2_name": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow2[0].f2_9[0]",
        field_type="text", format="text",
    ),
    "B4a_r2_ssn": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow2[0].f2_10[0]",
        field_type="text", format="text",
    ),
    "B4a_r2_country": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow2[0].f2_11[0]",
        field_type="text", format="text",
    ),
    "B4a_r2_pct": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow2[0].f2_12[0]",
        field_type="text", format="percentage",
    ),
    "B4a_r2_tax_yr_end": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow2[0].f2_13[0]",
        field_type="text", format="text",
    ),
    # Row 3
    "B4a_r3_name": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow3[0].f2_14[0]",
        field_type="text", format="text",
    ),
    "B4a_r3_ssn": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow3[0].f2_15[0]",
        field_type="text", format="text",
    ),
    "B4a_r3_country": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow3[0].f2_16[0]",
        field_type="text", format="text",
    ),
    "B4a_r3_pct": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow3[0].f2_17[0]",
        field_type="text", format="percentage",
    ),
    "B4a_r3_tax_yr_end": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow3[0].f2_18[0]",
        field_type="text", format="text",
    ),
    # Row 4
    "B4a_r4_name": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow4[0].f2_19[0]",
        field_type="text", format="text",
    ),
    "B4a_r4_ssn": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow4[0].f2_20[0]",
        field_type="text", format="text",
    ),
    "B4a_r4_country": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow4[0].f2_21[0]",
        field_type="text", format="text",
    ),
    "B4a_r4_pct": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow4[0].f2_22[0]",
        field_type="text", format="percentage",
    ),
    "B4a_r4_tax_yr_end": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4a[0].BodyRow4[0].f2_23[0]",
        field_type="text", format="text",
    ),

    # Schedule B Line 4b -- yes/no (entity owns 25% or more)
    "B4b_yes": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_4[0]",
        field_type="checkbox", format="boolean",
    ),
    "B4b_no": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_4[1]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 4b -- entity table (4 rows x 5 columns)
    # Row 1
    "B4b_r1_name": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow1[0].f2_24[0]",
        field_type="text", format="text",
    ),
    "B4b_r1_ein": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow1[0].f2_25[0]",
        field_type="text", format="text",
    ),
    "B4b_r1_country": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow1[0].f2_26[0]",
        field_type="text", format="text",
    ),
    "B4b_r1_pct": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow1[0].f2_27[0]",
        field_type="text", format="percentage",
    ),
    "B4b_r1_activity": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow1[0].f2_28[0]",
        field_type="text", format="text",
    ),
    # Row 2
    "B4b_r2_name": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow2[0].f2_29[0]",
        field_type="text", format="text",
    ),
    "B4b_r2_ein": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow2[0].f2_30[0]",
        field_type="text", format="text",
    ),
    "B4b_r2_country": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow2[0].f2_31[0]",
        field_type="text", format="text",
    ),
    "B4b_r2_pct": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow2[0].f2_32[0]",
        field_type="text", format="percentage",
    ),
    "B4b_r2_activity": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow2[0].f2_33[0]",
        field_type="text", format="text",
    ),
    # Row 3
    "B4b_r3_name": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow3[0].f2_34[0]",
        field_type="text", format="text",
    ),
    "B4b_r3_ein": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow3[0].f2_35[0]",
        field_type="text", format="text",
    ),
    "B4b_r3_country": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow3[0].f2_36[0]",
        field_type="text", format="text",
    ),
    "B4b_r3_pct": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow3[0].f2_37[0]",
        field_type="text", format="percentage",
    ),
    "B4b_r3_activity": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow3[0].f2_38[0]",
        field_type="text", format="text",
    ),
    # Row 4
    "B4b_r4_name": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow4[0].f2_39[0]",
        field_type="text", format="text",
    ),
    "B4b_r4_ein": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow4[0].f2_40[0]",
        field_type="text", format="text",
    ),
    "B4b_r4_country": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow4[0].f2_41[0]",
        field_type="text", format="text",
    ),
    "B4b_r4_pct": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow4[0].f2_42[0]",
        field_type="text", format="percentage",
    ),
    "B4b_r4_activity": AcroField(
        acro_name="topmostSubform[0].Page2[0].Table_Line4b[0].BodyRow4[0].f2_43[0]",
        field_type="text", format="text",
    ),

    # Schedule B Line 5a -- yes/no
    "B5a_yes": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_5[0]",
        field_type="checkbox", format="boolean",
    ),
    "B5a_no": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_5[1]",
        field_type="checkbox", format="boolean",
    ),
    # Line 5a text fields
    "B5a_percentage": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_44[0]",
        field_type="text", format="text",
    ),
    "B5a_date": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_45[0]",
        field_type="text", format="text",
    ),

    # Schedule B Line 5b -- yes/no
    "B5b_yes": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_6[0]",
        field_type="checkbox", format="boolean",
    ),
    "B5b_no": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_6[1]",
        field_type="checkbox", format="boolean",
    ),
    # Line 5b text fields
    "B5b_percentage": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_46[0]",
        field_type="text", format="text",
    ),
    "B5b_date": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_47[0]",
        field_type="text", format="text",
    ),

    # Schedule B Line 6 -- yes/no
    "B6_yes": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_7[0]",
        field_type="checkbox", format="boolean",
    ),
    "B6_no": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_7[1]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 7 -- single checkbox ("Check this box if ...")
    "B7_yes": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_8[0]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 8 -- currency amount (net unrealized built-in gain)
    "B8": AcroField(
        acro_name="topmostSubform[0].Page2[0].f2_48[0]",
        field_type="text", format="currency",
    ),

    # Schedule B Line 9 -- yes/no
    "B9_yes": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_9[0]",
        field_type="checkbox", format="boolean",
    ),
    "B9_no": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_9[1]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 10 -- yes/no
    "B10_yes": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_10[0]",
        field_type="checkbox", format="boolean",
    ),
    "B10_no": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_10[1]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 11 -- yes/no
    "B11_yes": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_11[0]",
        field_type="checkbox", format="boolean",
    ),
    "B11_no": AcroField(
        acro_name="topmostSubform[0].Page2[0].c2_11[1]",
        field_type="checkbox", format="boolean",
    ),

    # --- Page 2 (PDF page 3) -- Schedule B continued ---

    # Schedule B Line 12 -- yes/no
    "B12_yes": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_1[0]",
        field_type="checkbox", format="boolean",
    ),
    "B12_no": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_1[1]",
        field_type="checkbox", format="boolean",
    ),
    # Line 12 text amount field
    "B12_amount": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_1[0]",
        field_type="text", format="currency",
    ),

    # Schedule B Line 13 -- yes/no
    "B13_yes": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_2[0]",
        field_type="checkbox", format="boolean",
    ),
    "B13_no": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_2[1]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 14a -- yes/no
    "B14a_yes": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_3[0]",
        field_type="checkbox", format="boolean",
    ),
    "B14a_no": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_3[1]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 14b -- yes/no
    "B14b_yes": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_4[0]",
        field_type="checkbox", format="boolean",
    ),
    "B14b_no": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_4[1]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 15 -- yes/no
    "B15_yes": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_5[0]",
        field_type="checkbox", format="boolean",
    ),
    "B15_no": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_5[1]",
        field_type="checkbox", format="boolean",
    ),
    # Line 15 text amount field
    "B15_amount": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_2[0]",
        field_type="text", format="currency",
    ),

    # Schedule B Line 16 -- yes/no
    "B16_yes": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_6[0]",
        field_type="checkbox", format="boolean",
    ),
    "B16_no": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_6[1]",
        field_type="checkbox", format="boolean",
    ),

    # Schedule B Line 16 continued (second pair of yes/no)
    "B16_cont_yes": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_7[0]",
        field_type="checkbox", format="boolean",
    ),
    "B16_cont_no": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_7[1]",
        field_type="checkbox", format="boolean",
    ),

    # ======================================================================
    # PAGE 2 -- Schedule K (Shareholders' Pro Rata Share Items)
    # Lines 1-16 on lower portion of page 2
    # ======================================================================
    # Line 1 -- Ordinary business income (loss)
    "K1": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_3[0]",
        field_type="text", format="currency",
    ),
    # Line 2 -- Net rental real estate income (loss)
    "K2": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_4[0]",
        field_type="text", format="currency",
    ),
    # Line 3a -- Other gross rental income (sub-column)
    "K3a": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_5[0]",
        field_type="text", format="currency",
    ),
    # Line 3b -- Expenses from other rental activities (sub-column)
    "K3b": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_6[0]",
        field_type="text", format="currency",
    ),
    # Line 3c -- Other net rental income (loss) (main column)
    "K3c": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_7[0]",
        field_type="text", format="currency",
    ),
    # Line 4 -- Interest income
    "K4": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_8[0]",
        field_type="text", format="currency",
    ),
    # Line 5a -- Ordinary dividends
    "K5a": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_9[0]",
        field_type="text", format="currency",
    ),
    # Line 5b -- Qualified dividends (sub-column)
    "K5b": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_10[0]",
        field_type="text", format="currency",
    ),
    # Line 6 -- Royalties
    "K6": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_11[0]",
        field_type="text", format="currency",
    ),
    # Line 7 -- Net short-term capital gain (loss)
    "K7": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_12[0]",
        field_type="text", format="currency",
    ),
    # Line 8a -- Net long-term capital gain (loss)
    "K8a": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_13[0]",
        field_type="text", format="currency",
    ),
    # Line 8b -- Collectibles (28%) gain (loss) (sub-column)
    "K8b": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_14[0]",
        field_type="text", format="currency",
    ),
    # Line 8c -- Unrecaptured section 1250 gain (sub-column)
    "K8c": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_15[0]",
        field_type="text", format="currency",
    ),
    # Line 9 -- Net section 1231 gain (loss)
    "K9": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_16[0]",
        field_type="text", format="currency",
    ),
    # Line 10 -- Other income (loss) -- code field + amount
    "K10_code": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_17[0]",
        field_type="text", format="text",
    ),
    "K10": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_18[0]",
        field_type="text", format="currency",
    ),
    # Line 11 -- Section 179 deduction
    "K11": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_19[0]",
        field_type="text", format="currency",
    ),
    # Line 12a -- Charitable contributions
    "K12a": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_20[0]",
        field_type="text", format="currency",
    ),
    # Line 12b -- Investment interest expense
    "K12b": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_21[0]",
        field_type="text", format="currency",
    ),
    # Line 12c -- Section 59(e)(2) expenditures -- code field + amount
    "K12c_code": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_23[0]",
        field_type="text", format="text",
    ),
    "K12c": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_22[0]",
        field_type="text", format="currency",
    ),
    # Line 12d -- Other deductions -- code field + amount
    "K12d_code": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_25[0]",
        field_type="text", format="text",
    ),
    "K12d": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_24[0]",
        field_type="text", format="currency",
    ),
    # Line 13a -- Low-income housing credit (section 42(j)(5))
    "K13a": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_26[0]",
        field_type="text", format="currency",
    ),
    # Line 13b -- Low-income housing credit (other)
    "K13b": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_27[0]",
        field_type="text", format="currency",
    ),
    # Line 13c -- Qualified rehabilitation expenditures (rental RE)
    "K13c": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_28[0]",
        field_type="text", format="currency",
    ),
    # Line 13d -- Other rental real estate credits -- code + amount
    "K13d_code": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_30[0]",
        field_type="text", format="text",
    ),
    "K13d": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_29[0]",
        field_type="text", format="currency",
    ),
    # Line 13e -- Other rental credits -- code + amount
    "K13e_code": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_32[0]",
        field_type="text", format="text",
    ),
    "K13e": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_31[0]",
        field_type="text", format="currency",
    ),
    # Line 13f -- Biofuel producer credit
    "K13f": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_33[0]",
        field_type="text", format="currency",
    ),
    # Line 13g -- Other credits -- code + amount
    "K13g_code": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_35[0]",
        field_type="text", format="text",
    ),
    "K13g": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_34[0]",
        field_type="text", format="currency",
    ),
    # Lines 14a-14c -- self-employment checkboxes (on page 2 lower)
    "K14a": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_7[2]",
        field_type="checkbox", format="boolean",
    ),
    "K14b": AcroField(
        acro_name="topmostSubform[0].Page3[0].c3_8[0]",
        field_type="checkbox", format="boolean",
    ),
    # Line 15a -- Net earnings from self-employment
    "K15a": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_37[0]",
        field_type="text", format="currency",
    ),
    # Line 15b -- Gross farming or fishing income
    "K15b": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_38[0]",
        field_type="text", format="currency",
    ),
    # Line 15c -- Gross nonfarm income
    "K15c": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_39[0]",
        field_type="text", format="currency",
    ),
    # Line 15d -- Foreign transactions -- (various items)
    "K15d": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_40[0]",
        field_type="text", format="currency",
    ),
    # Lines 15e-15h -- Additional foreign transaction items
    "K15e": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_41[0]",
        field_type="text", format="currency",
    ),
    "K15f": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_42[0]",
        field_type="text", format="currency",
    ),
    # Line 16a -- Tax-exempt interest income
    "K16a": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_43[0]",
        field_type="text", format="currency",
    ),
    # Line 16b -- Other tax-exempt income
    "K16b": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_44[0]",
        field_type="text", format="currency",
    ),
    # Line 16c -- Nondeductible expenses
    "K16c": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_45[0]",
        field_type="text", format="currency",
    ),
    # Line 16d -- Distributions
    "K16d": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_46[0]",
        field_type="text", format="currency",
    ),
    # Line 16e -- Repayment of loans from shareholders
    "K16e": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_47[0]",
        field_type="text", format="currency",
    ),
    # Line 16f -- other items (last K field on page 2)
    "K16f": AcroField(
        acro_name="topmostSubform[0].Page3[0].f3_48[0]",
        field_type="text", format="currency",
    ),

    # ======================================================================
    # PAGE 3 -- Schedule K continued (Lines 17-18, top of page)
    # ======================================================================
    # Line 17a -- Investment income
    "K17a": AcroField(
        acro_name="topmostSubform[0].Page4[0].f4_1[0]",
        field_type="text", format="currency",
    ),
    # Line 17b -- Investment expenses
    "K17b": AcroField(
        acro_name="topmostSubform[0].Page4[0].f4_2[0]",
        field_type="text", format="currency",
    ),
    # Line 17c -- Net investment income
    "K17c": AcroField(
        acro_name="topmostSubform[0].Page4[0].f4_3[0]",
        field_type="text", format="currency",
    ),
    # Line 18 -- Income/loss reconciliation
    "K18": AcroField(
        acro_name="topmostSubform[0].Page4[0].f4_4[0]",
        field_type="text", format="currency",
    ),

    # ======================================================================
    # PAGE 3 -- Schedule L (Balance Sheets per Books)
    #
    # Four columns per row: (a) BOY gross, (b) BOY net, (c) EOY gross, (d) EOY net
    # AcroForm column positions:
    #   col a: x=259.2-337.6 (f4_XX at offset 0)
    #   col b: x=338.4-416.9 (f4_XX at offset 1)
    #   col c: x=417.6-496.0 (f4_XX at offset 2)
    #   col d: x=496.8-576.0 (f4_XX at offset 3)
    #
    # Lines 2b, 10b, 11b, 13b have indented col a (x=263.2) and col c (x=421.6)
    # ======================================================================

    # --- Assets ---
    # Line 1 -- Cash (simple line: BOY in col b, EOY in col d)
    "L1a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line1[0].f4_6[0]", field_type="text", format="currency"),
    "L1d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line1[0].f4_8[0]", field_type="text", format="currency"),

    # Line 2a -- Trade notes and accounts receivable (gross)
    "L2a_a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line2a[0].f4_9[0]", field_type="text", format="currency"),
    "L2a_b": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line2a[0].f4_10[0]", field_type="text", format="currency"),
    "L2a_c": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line2a[0].f4_11[0]", field_type="text", format="currency"),
    "L2a_d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line2a[0].f4_12[0]", field_type="text", format="currency"),

    # Line 2b -- Less allowance for bad debts
    "L2b_a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line2b[0].f4_13[0]", field_type="text", format="currency"),
    "L2b_b": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line2b[0].f4_14[0]", field_type="text", format="currency"),
    "L2b_c": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line2b[0].f4_15[0]", field_type="text", format="currency"),
    "L2b_d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line2b[0].f4_16[0]", field_type="text", format="currency"),

    # Line 3 -- Inventories (simple line: BOY in col b, EOY in col d)
    "L3a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line3[0].f4_18[0]", field_type="text", format="currency"),
    "L3d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line3[0].f4_20[0]", field_type="text", format="currency"),

    # Line 4 -- U.S. government obligations (simple line: BOY col b, EOY col d)
    "L4a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line4[0].f4_22[0]", field_type="text", format="currency"),
    "L4d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line4[0].f4_24[0]", field_type="text", format="currency"),

    # Line 5 -- Tax-exempt securities (simple line: BOY col b, EOY col d)
    "L5a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line5[0].f4_26[0]", field_type="text", format="currency"),
    "L5d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line5[0].f4_28[0]", field_type="text", format="currency"),

    # Line 6 -- Other current assets (simple line: BOY col b, EOY col d)
    "L6a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line6[0].f4_30[0]", field_type="text", format="currency"),
    "L6d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line6[0].f4_32[0]", field_type="text", format="currency"),

    # Line 7 -- Loans to shareholders (simple line: BOY col b, EOY col d)
    "L7a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line7[0].f4_34[0]", field_type="text", format="currency"),
    "L7d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line7[0].f4_36[0]", field_type="text", format="currency"),

    # Line 8 -- Mortgage and real estate loans (simple line: BOY col b, EOY col d)
    "L8a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line8[0].f4_38[0]", field_type="text", format="currency"),
    "L8d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line8[0].f4_40[0]", field_type="text", format="currency"),

    # Line 9 -- Other investments (simple line: BOY col b, EOY col d)
    "L9a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line9[0].f4_42[0]", field_type="text", format="currency"),
    "L9d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line9[0].f4_44[0]", field_type="text", format="currency"),

    # Line 10a -- Buildings and other depreciable assets (gross)
    "L10a_a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line10a[0].f4_45[0]", field_type="text", format="currency"),
    "L10a_b": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line10a[0].f4_46[0]", field_type="text", format="currency"),
    "L10a_c": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line10a[0].f4_47[0]", field_type="text", format="currency"),
    "L10a_d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line10a[0].f4_48[0]", field_type="text", format="currency"),

    # Line 10b -- Less accumulated depreciation
    "L10b_a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line10b[0].f4_49[0]", field_type="text", format="currency"),
    "L10b_b": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line10b[0].f4_50[0]", field_type="text", format="currency"),
    "L10b_c": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line10b[0].f4_51[0]", field_type="text", format="currency"),
    "L10b_d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line10b[0].f4_52[0]", field_type="text", format="currency"),

    # Line 11a -- Depletable assets (gross)
    "L11a_a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line11a[0].f4_53[0]", field_type="text", format="currency"),
    "L11a_b": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line11a[0].f4_54[0]", field_type="text", format="currency"),
    "L11a_c": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line11a[0].f4_55[0]", field_type="text", format="currency"),
    "L11a_d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line11a[0].f4_56[0]", field_type="text", format="currency"),

    # Line 11b -- Less accumulated depletion
    "L11b_a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line11b[0].f4_57[0]", field_type="text", format="currency"),
    "L11b_b": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line11b[0].f4_58[0]", field_type="text", format="currency"),
    "L11b_c": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line11b[0].f4_59[0]", field_type="text", format="currency"),
    "L11b_d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line11b[0].f4_60[0]", field_type="text", format="currency"),

    # Line 12 -- Land (net of any amortization) (simple line: BOY col b, EOY col d)
    "L12a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line12[0].f4_62[0]", field_type="text", format="currency"),
    "L12d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line12[0].f4_64[0]", field_type="text", format="currency"),

    # Line 13a -- Intangible assets (amortizable only, gross)
    "L13a_a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line13a[0].f4_65[0]", field_type="text", format="currency"),
    "L13a_b": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line13a[0].f4_66[0]", field_type="text", format="currency"),
    "L13a_c": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line13a[0].f4_67[0]", field_type="text", format="currency"),
    "L13a_d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line13a[0].f4_68[0]", field_type="text", format="currency"),

    # Line 13b -- Less accumulated amortization
    "L13b_a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line13b[0].f4_69[0]", field_type="text", format="currency"),
    "L13b_b": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line13b[0].f4_70[0]", field_type="text", format="currency"),
    "L13b_c": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line13b[0].f4_71[0]", field_type="text", format="currency"),
    "L13b_d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line13b[0].f4_72[0]", field_type="text", format="currency"),

    # Line 14 -- Other assets (simple line: BOY col b, EOY col d)
    "L14a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line14[0].f4_74[0]", field_type="text", format="currency"),
    "L14d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line14[0].f4_76[0]", field_type="text", format="currency"),

    # Line 15 -- Total assets (simple line: BOY col b, EOY col d)
    "L15a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line15[0].f4_78[0]", field_type="text", format="currency"),
    "L15d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Assets[0].Line15[0].f4_80[0]", field_type="text", format="currency"),

    # --- Liabilities and Shareholders' Equity ---
    # All liability lines are simple: BOY in col (b), EOY in col (d)

    # Line 16 -- Accounts payable
    "L16a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line16[0].f4_82[0]", field_type="text", format="currency"),
    "L16d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line16[0].f4_84[0]", field_type="text", format="currency"),

    # Line 17 -- Mortgages, notes, bonds payable in less than 1 year
    "L17a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line17[0].f4_86[0]", field_type="text", format="currency"),
    "L17d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line17[0].f4_88[0]", field_type="text", format="currency"),

    # Line 18 -- Other current liabilities
    "L18a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line18[0].f4_90[0]", field_type="text", format="currency"),
    "L18d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line18[0].f4_92[0]", field_type="text", format="currency"),

    # Line 19 -- Loans from shareholders
    "L19a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line19[0].f4_94[0]", field_type="text", format="currency"),
    "L19d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line19[0].f4_96[0]", field_type="text", format="currency"),

    # Line 20 -- Mortgages, notes, bonds payable in 1 year or more
    "L20a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line20[0].f4_98[0]", field_type="text", format="currency"),
    "L20d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line20[0].f4_100[0]", field_type="text", format="currency"),

    # Line 21 -- Other liabilities
    "L21a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line21[0].f4_102[0]", field_type="text", format="currency"),
    "L21d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line21[0].f4_104[0]", field_type="text", format="currency"),

    # Line 22 -- Capital stock
    "L22a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line22[0].f4_106[0]", field_type="text", format="currency"),
    "L22d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line22[0].f4_108[0]", field_type="text", format="currency"),

    # Line 23 -- Additional paid-in capital
    "L23a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line23[0].f4_110[0]", field_type="text", format="currency"),
    "L23d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line23[0].f4_112[0]", field_type="text", format="currency"),

    # Line 24 -- Retained earnings
    "L24a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line24[0].f4_114[0]", field_type="text", format="currency"),
    "L24d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line24[0].f4_116[0]", field_type="text", format="currency"),

    # Line 25 -- Adjustments to shareholders' equity
    "L25a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line25[0].f4_118[0]", field_type="text", format="currency"),
    "L25d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line25[0].f4_120[0]", field_type="text", format="currency"),

    # Line 26 -- Less cost of treasury stock
    "L26a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line26[0].f4_122[0]", field_type="text", format="currency"),
    "L26d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line26[0].f4_124[0]", field_type="text", format="currency"),

    # Line 27 -- Total liabilities and shareholders' equity
    "L27a": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line27[0].f4_126[0]", field_type="text", format="currency"),
    "L27d": AcroField(acro_name="topmostSubform[0].Page4[0].Table_Liabilities[0].Line27[0].f4_128[0]", field_type="text", format="currency"),

    # ======================================================================
    # PAGE 4 -- Schedule M-1 (Reconciliation of Income/Loss)
    #
    # Left column: Lines 1-4 (additions)
    # Right column: Lines 5-8 (subtractions)
    # ======================================================================

    # --- M-1 Left column ---
    # Line 1 -- Net income (loss) per books
    "M1_1": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Left[0].f5_1[0]",
        field_type="text", format="currency",
    ),
    # Line 2 -- Income included on Schedule K not on books (sub-field + amount)
    "M1_2_desc": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Left[0].f5_2[0]",
        field_type="text", format="text",
    ),
    "M1_2": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Left[0].f5_4[0]",
        field_type="text", format="currency",
    ),
    # Line 3a -- Guaranteed payments (sub-amount)
    "M1_3a": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Left[0].f5_5[0]",
        field_type="text", format="currency",
    ),
    # Line 3a description (expenses on books not on return)
    "M1_3a_desc": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Left[0].f5_6[0]",
        field_type="text", format="text",
    ),
    # Line 3b -- Travel/entertainment sub-amount
    "M1_3b": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Left[0].f5_7[0]",
        field_type="text", format="currency",
    ),
    # Line 3 other description + amount (f5_8 desc, f5_9 amount)
    "M1_3c_desc": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Left[0].f5_8[0]",
        field_type="text", format="text",
    ),
    "M1_3c": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Left[0].f5_9[0]",
        field_type="text", format="currency",
    ),
    # Line 4 -- Add lines 1 through 3 (bottom of left column)
    "M1_4": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Left[0].f5_10[0]",
        field_type="text", format="currency",
    ),
    # Line 3 description text (between 2 and 3a)
    "M1_3_desc": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Left[0].f5_3[0]",
        field_type="text", format="text",
    ),

    # --- M-1 Right column ---
    # Line 5 -- Income recorded on books not on Schedule K
    "M1_5_desc": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Right[0].f5_11[0]",
        field_type="text", format="text",
    ),
    "M1_5_desc2": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Right[0].f5_12[0]",
        field_type="text", format="text",
    ),
    "M1_5": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Right[0].f5_13[0]",
        field_type="text", format="currency",
    ),
    # Line 6 -- Deductions included on Schedule K not charged against book income
    # f5_14 is description text, f5_16 is the amount (at x=496-576)
    "M1_6_desc": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Right[0].f5_14[0]",
        field_type="text", format="text",
    ),
    "M1_6": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Right[0].f5_16[0]",
        field_type="text", format="currency",
    ),
    # Line 7 description (f5_15)
    "M1_7_desc": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Right[0].f5_15[0]",
        field_type="text", format="text",
    ),
    # Line 7 -- Add lines 5 and 6 (amount at f5_17)
    "M1_7": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Right[0].f5_17[0]",
        field_type="text", format="currency",
    ),
    # Line 8 -- Income (loss) (Schedule K, line 18). Line 4 less line 7.
    "M1_8": AcroField(
        acro_name="topmostSubform[0].Page5[0].SchM-1_Right[0].f5_18[0]",
        field_type="text", format="currency",
    ),

    # ======================================================================
    # PAGE 4 -- Schedule M-2 (Analysis of AAA, OAA, Shareholders' Undistributed
    #           Taxable Income Previously Taxed, and Accumulated E&P)
    #
    # Four columns: (a) AAA, (b) OAA, (c) Shareholders' undist., (d) Accum. E&P
    # AcroForm columns:
    #   col a: x=259.2-337.6 (f5_XX at offset 0)
    #   col b: x=338.4-416.9 (f5_XX at offset 1)
    #   col c: x=417.6-496.0 (f5_XX at offset 2)
    #   col d: x=496.8-576.0 (f5_XX at offset 3)
    # ======================================================================

    # Line 1 -- Balance at beginning of tax year
    "M2_1a": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line1[0].f5_19[0]", field_type="text", format="currency"),
    "M2_1b": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line1[0].f5_20[0]", field_type="text", format="currency"),
    "M2_1c": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line1[0].f5_21[0]", field_type="text", format="currency"),
    "M2_1d": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line1[0].f5_22[0]", field_type="text", format="currency"),

    # Line 2 -- Ordinary income from page 1, line 21
    "M2_2a": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line2[0].f5_23[0]", field_type="text", format="currency"),
    "M2_2b": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line2[0].f5_24[0]", field_type="text", format="currency"),
    "M2_2c": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line2[0].f5_25[0]", field_type="text", format="currency"),
    "M2_2d": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line2[0].f5_26[0]", field_type="text", format="currency"),

    # Line 3 -- Other additions
    "M2_3a": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line3[0].f5_27[0]", field_type="text", format="currency"),
    "M2_3b": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line3[0].f5_28[0]", field_type="text", format="currency"),
    "M2_3c": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line3[0].f5_29[0]", field_type="text", format="currency"),
    "M2_3d": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line3[0].f5_30[0]", field_type="text", format="currency"),

    # Line 4 -- Loss from page 1, line 21
    "M2_4a": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line4[0].f5_31[0]", field_type="text", format="currency"),
    "M2_4b": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line4[0].f5_32[0]", field_type="text", format="currency"),
    "M2_4c": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line4[0].f5_33[0]", field_type="text", format="currency"),
    "M2_4d": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line4[0].f5_34[0]", field_type="text", format="currency"),

    # Line 5 -- Other reductions
    "M2_5a": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line5[0].f5_35[0]", field_type="text", format="currency"),
    "M2_5b": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line5[0].f5_36[0]", field_type="text", format="currency"),
    "M2_5c": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line5[0].f5_37[0]", field_type="text", format="currency"),
    "M2_5d": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line5[0].f5_38[0]", field_type="text", format="currency"),

    # Line 6 -- Combine lines 1 through 5
    "M2_6a": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line6[0].f5_39[0]", field_type="text", format="currency"),
    "M2_6b": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line6[0].f5_40[0]", field_type="text", format="currency"),
    "M2_6c": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line6[0].f5_41[0]", field_type="text", format="currency"),
    "M2_6d": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line6[0].f5_42[0]", field_type="text", format="currency"),

    # Line 7 -- Distributions
    "M2_7a": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line7[0].f5_43[0]", field_type="text", format="currency"),
    "M2_7b": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line7[0].f5_44[0]", field_type="text", format="currency"),
    "M2_7c": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line7[0].f5_45[0]", field_type="text", format="currency"),
    "M2_7d": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line7[0].f5_46[0]", field_type="text", format="currency"),

    # Line 8 -- Balance at end of tax year
    "M2_8a": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line8[0].f5_47[0]", field_type="text", format="currency"),
    "M2_8b": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line8[0].f5_48[0]", field_type="text", format="currency"),
    "M2_8c": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line8[0].f5_49[0]", field_type="text", format="currency"),
    "M2_8d": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line8[0].f5_50[0]", field_type="text", format="currency"),

    # --- M-2 DB key aliases ---
    # The compute engine stores M-2 values as M2_1..M2_8 (AAA column only).
    # Map these DB keys to the column (a) = AAA AcroForm fields.
    "M2_1": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line1[0].f5_19[0]", field_type="text", format="currency"),
    "M2_2": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line2[0].f5_23[0]", field_type="text", format="currency"),
    "M2_3": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line3[0].f5_27[0]", field_type="text", format="currency"),
    "M2_4": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line4[0].f5_31[0]", field_type="text", format="currency"),
    "M2_5": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line5[0].f5_35[0]", field_type="text", format="currency"),
    "M2_6": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line6[0].f5_39[0]", field_type="text", format="currency"),
    "M2_7": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line7[0].f5_43[0]", field_type="text", format="currency"),
    "M2_8": AcroField(acro_name="topmostSubform[0].Page5[0].Table_SchM-2[0].Line8[0].f5_47[0]", field_type="text", format="currency"),

}
