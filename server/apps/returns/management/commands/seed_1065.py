"""
Seed the Form 1065 definition with all sections and lines.

Run: poetry run python manage.py seed_1065
"""

from django.core.management.base import BaseCommand

from apps.returns.models import (
    FieldType,
    FormDefinition,
    FormFieldValue,
    FormLine,
    FormSection,
    NormalBalance,
)

# ---------------------------------------------------------------------------
# 1065 Line Definitions
# Each section is (code, title, sort_order, lines)
# Each line is (line_number, label, field_type, mapping_key, is_computed, sort, normal_balance)
# normal_balance: DR = debit-normal (expenses, assets)
#                 CR = credit-normal (revenue, liabilities, equity, accum depr)
# ---------------------------------------------------------------------------

C = FieldType.CURRENCY
I = FieldType.INTEGER
T = FieldType.TEXT
B = FieldType.BOOLEAN

DR = NormalBalance.DEBIT
CR = NormalBalance.CREDIT

SECTIONS = [
    # ------ ADMIN: INVOICE + LETTER ------
    (
        "admin",
        "Admin — Invoice & Letter",
        5,
        [
            # Invoice fields
            ("INV_PREP_FEE", "Preparation fee", C, "", False, 10, DR),
            ("INV_FEE_2_DESC", "Additional fee 2 description", T, "", False, 20, DR),
            ("INV_FEE_2", "Additional fee 2", C, "", False, 21, DR),
            ("INV_FEE_3_DESC", "Additional fee 3 description", T, "", False, 30, DR),
            ("INV_FEE_3", "Additional fee 3", C, "", False, 31, DR),
            ("INV_MEMO", "Invoice memo", T, "", False, 40, DR),
            ("INV_TOTAL", "Invoice total", C, "", True, 50, DR),
            # Letter fields
            ("LTR_FILING_METHOD", "Filing method", T, "", False, 100, DR),
            ("LTR_8879_NEEDED", "Form 8879 needed", B, "", False, 110, DR),
            ("LTR_ST_FILING", "State filing method", T, "", False, 120, DR),
            ("LTR_FED_BALANCE", "Federal balance due", C, "", False, 130, DR),
            ("LTR_FED_DUE_DATE", "Federal due date", T, "", False, 131, DR),
            ("LTR_GA_BALANCE", "Georgia balance due", C, "", False, 140, DR),
            ("LTR_GA_DUE_DATE", "Georgia due date", T, "", False, 141, DR),
            ("LTR_EST_TAX_1", "Estimated tax payment 1", C, "", False, 200, DR),
            ("LTR_EST_DATE_1", "Estimated tax date 1", T, "", False, 201, DR),
            ("LTR_EST_TAX_2", "Estimated tax payment 2", C, "", False, 210, DR),
            ("LTR_EST_DATE_2", "Estimated tax date 2", T, "", False, 211, DR),
            ("LTR_EST_TAX_3", "Estimated tax payment 3", C, "", False, 220, DR),
            ("LTR_EST_DATE_3", "Estimated tax date 3", T, "", False, 221, DR),
            ("LTR_EST_TAX_4", "Estimated tax payment 4", C, "", False, 230, DR),
            ("LTR_EST_DATE_4", "Estimated tax date 4", T, "", False, 231, DR),
            ("LTR_CUSTOM_NOTE", "Custom letter note", T, "", False, 300, DR),
        ],
    ),
    # ------ PAGE 1: INCOME ------
    (
        "page1_income",
        "Page 1 — Income",
        10,
        [
            ("1a", "Gross receipts or sales", C, "1065_L1a", False, 10, CR),
            ("1b", "Returns and allowances", C, "1065_L1b", False, 20, DR),
            ("1c", "Balance (subtract 1b from 1a)", C, "", True, 30, DR),
            ("2", "Cost of goods sold (attach Form 1125-A)", C, "", True, 40, DR),
            ("3", "Gross profit (subtract line 2 from line 1c)", C, "", True, 50, DR),
            ("4", "Ordinary income (loss) from other partnerships, estates, and trusts", C, "1065_L4", False, 60, CR),
            ("5", "Net farm profit (loss) (attach Schedule F)", C, "1065_L5", False, 70, CR),
            ("6", "Net gain (loss) from Form 4797, Part II, line 17", C, "1065_L6", False, 80, DR),
            ("7", "Other income (loss)", C, "1065_L7", False, 90, CR),
            ("8", "Total income (loss) (combine lines 3 through 7)", C, "", True, 100, DR),
        ],
    ),
    # ------ SCHEDULE A: COST OF GOODS SOLD (Form 1125-A) ------
    (
        "sched_a",
        "Schedule A — Cost of Goods Sold (Form 1125-A)",
        15,
        [
            ("A1", "Inventory at beginning of year", C, "1065_A1", False, 10, DR),
            ("A2", "Purchases", C, "1065_A2", False, 20, DR),
            ("A3", "Cost of labor", C, "1065_A3", False, 30, DR),
            ("A4", "Additional section 263A costs", C, "1065_A4", False, 40, DR),
            ("A5", "Other costs", C, "1065_A5", False, 50, DR),
            ("A6", "Total (add lines 1 through 5)", C, "", True, 60, DR),
            ("A7", "Inventory at end of year", C, "1065_A7", False, 70, DR),
            ("A8", "Cost of goods sold (line 6 minus line 7)", C, "", True, 80, DR),
            ("A9a", "Method used for valuing closing inventory", T, "", False, 90, DR),
            ("A9f", "Was there any change in determining quantities, cost, or valuations?", B, "", False, 91, DR),
        ],
    ),
    # ------ PAGE 1: DEDUCTIONS ------
    (
        "page1_deductions",
        "Page 1 — Deductions",
        20,
        [
            ("9", "Salaries and wages (other than to partners)", C, "1065_L9", False, 10, DR),
            ("10", "Guaranteed payments to partners", C, "", True, 20, DR),
            ("11", "Repairs and maintenance", C, "1065_L11", False, 30, DR),
            ("12", "Bad debts", C, "1065_L12", False, 40, DR),
            ("13", "Rent", C, "1065_L13", False, 50, DR),
            ("14", "Taxes and licenses", C, "1065_L14", False, 60, DR),
            ("15", "Interest (see instructions)", C, "1065_L15", False, 70, DR),
            ("16", "Depreciation", C, "1065_L16", False, 80, DR),
            ("17", "Depletion", C, "1065_L17", False, 90, DR),
            ("18", "Retirement plans, etc.", C, "1065_L18", False, 100, DR),
            ("19", "Employee benefit programs", C, "1065_L19", False, 110, DR),
            # Named deductions (roll up to Line 20 "Other deductions" statement)
            ("D_ACCT", "Accounting", C, "", False, 200, DR),
            ("D_ANSW", "Answering Service", C, "", False, 210, DR),
            ("D_AUTO", "Auto and Truck Expense", C, "", False, 220, DR),
            ("D_BANK", "Bank Charges", C, "", False, 230, DR),
            ("D_COMM", "Commissions", C, "", False, 240, DR),
            ("D_DELI", "Delivery and Freight", C, "", False, 250, DR),
            ("D_DUES", "Dues and Subscriptions", C, "", False, 260, DR),
            ("D_GIFT", "Gifts", C, "", False, 270, DR),
            ("D_INSU", "Insurance", C, "", False, 280, DR),
            ("D_JANI", "Janitorial", C, "", False, 290, DR),
            ("D_LAUN", "Laundry and Cleaning", C, "", False, 300, DR),
            ("D_LICE", "Licenses and Permits", C, "", False, 305, DR),
            ("D_LEGA", "Legal and Professional", C, "", False, 310, DR),
            ("D_MEALS_50", "Meals (50% deductible)", C, "", False, 316, DR),
            ("D_MEALS_DOT", "DOT Meals (80% deductible)", C, "", False, 317, DR),
            ("D_ENTERTAINMENT", "Entertainment (nondeductible)", C, "", False, 318, DR),
            ("D_MEALS_DED", "Deductible meals", C, "", True, 319, DR),
            ("D_MEALS_NONDED", "Nondeductible meals & entertainment", C, "", True, 320, DR),
            ("D_MISC", "Miscellaneous", C, "", False, 330, DR),
            ("D_OFFI", "Office Expense", C, "", False, 340, DR),
            ("D_ORGN", "Organizational Expenditures", C, "", False, 350, DR),
            ("D_OUTS", "Outside Services", C, "", False, 360, DR),
            ("D_PARK", "Parking and Tolls", C, "", False, 370, DR),
            ("D_POST", "Postage", C, "", False, 380, DR),
            ("D_PRNT", "Printing", C, "", False, 390, DR),
            ("D_SECU", "Security", C, "", False, 400, DR),
            ("D_SUPP", "Supplies", C, "", False, 410, DR),
            ("D_TELE", "Telephone", C, "", False, 420, DR),
            ("D_TOOL", "Tools", C, "", False, 430, DR),
            ("D_TRAV", "Travel", C, "", False, 440, DR),
            ("D_UNIF", "Uniforms", C, "", False, 450, DR),
            ("D_UTIL", "Utilities", C, "", False, 460, DR),
            ("D_WAST", "Waste Removal", C, "", False, 470, DR),
            # Free-form deduction rows
            ("D_FREE1_DESC", "", T, "", False, 500, DR),
            ("D_FREE1", "", C, "", False, 501, DR),
            ("D_FREE2_DESC", "", T, "", False, 510, DR),
            ("D_FREE2", "", C, "", False, 511, DR),
            ("D_FREE3_DESC", "", T, "", False, 520, DR),
            ("D_FREE3", "", C, "", False, 521, DR),
            ("D_FREE4_DESC", "", T, "", False, 530, DR),
            ("D_FREE4", "", C, "", False, 531, DR),
            ("D_FREE5_DESC", "", T, "", False, 540, DR),
            ("D_FREE5", "", C, "", False, 541, DR),
            ("D_FREE6_DESC", "", T, "", False, 550, DR),
            ("D_FREE6", "", C, "", False, 551, DR),
            # Summary lines
            ("20", "Other deductions (attach statement)", C, "", True, 600, DR),
            ("21", "Total deductions (add lines 9 through 20)", C, "", True, 610, DR),
            ("22", "Ordinary business income (loss) (subtract line 21 from line 8)", C, "", True, 620, DR),
        ],
    ),
    # ------ SCHEDULE B: OTHER INFORMATION ------
    (
        "sched_b",
        "Schedule B — Other Information",
        25,
        [
            ("B1", "What type of entity is filing this return?", T, "", False, 10, DR),
            ("B2", "At any time during the tax year, was any partner in the partnership a disregarded entity, a trust, an estate, or a nominee or similar person?", B, "", False, 20, DR),
            ("B3", "At the end of the tax year, did the partnership own, directly or indirectly, 50% or more of the profit, loss, or capital in any other partnership?", B, "", False, 30, DR),
            ("B4", "At the end of the tax year, did any foreign or domestic corporation, partnership, trust, or tax-exempt organization, or any foreign government own, directly or indirectly, an interest of 50% or more in the profit, loss, or capital of the partnership?", B, "", False, 40, DR),
            ("B5", "Did the partnership file Form 8893, Election of Partnership Level Tax Treatment, or an election under section 6231(a)(1)(B)(ii) for partnership-level tax treatment, that is in effect for this tax year?", B, "", False, 50, DR),
            ("B6", "Does the partnership satisfy all four of the following conditions? (a) The partnership's total receipts were less than $250,000. (b) The partnership's total assets at end of year were less than $1 million. (c) Schedules K-1 are filed with the return. (d) The partnership is not filing or required to file Schedule M-3.", B, "", False, 60, DR),
            ("B7", "Is this partnership a publicly traded partnership as defined in section 469(k)(2)?", B, "", False, 70, DR),
            ("B8", "During the tax year, did the partnership have any debt that was canceled, was forgiven, or had the terms modified so as to reduce the principal amount of the debt?", B, "", False, 80, DR),
            ("B9", "Has this partnership filed, or is it required to file, Form 8918, Material Advisor Disclosure Statement, to provide information on any reportable transaction?", B, "", False, 90, DR),
            ("B10a", "At any time during calendar year 2025, did the partnership have an interest in or a signature or other authority over a financial account in a foreign country?", B, "", False, 100, DR),
            ("B10b", "If 'Yes,' enter the name of the foreign country", T, "", False, 105, DR),
            ("B11", "At any time during the tax year, did the partnership receive a distribution from, or was it the grantor of, or transferor to, a foreign trust?", B, "", False, 110, DR),
            ("B12a", "Is the partnership making, or had it previously made (and not revoked), a section 754 election?", B, "", False, 120, DR),
            ("B12b", "Did the partnership make for this tax year an optional basis adjustment under section 743(b) or 734(b)?", B, "", False, 125, DR),
            ("B13", "Is the partnership required to adjust the basis of partnership assets under section 743(b) or 734(b) because of a substantial built-in loss or substantial basis reduction?", B, "", False, 130, DR),
            ("B14", "Check this box if, during the current or prior tax year, the partnership distributed any property received in a like-kind exchange or contributed such property to another entity.", B, "", False, 140, DR),
            ("B15a", "Did the partnership have an election under section 163(j) for any real property trade or business or any farming business in effect during the tax year?", B, "", False, 150, DR),
            ("B16", "Does the partnership satisfy one or more of the following? (a) Owns a pass-through entity with current, or prior year carryover, excess business interest expense. (b) Had aggregate average annual gross receipts for the 3 preceding tax years more than $31 million and has business interest expense. (c) Is a tax shelter with business interest expense.", B, "", False, 160, DR),
            ("B17a", "During the tax year, did the partnership make any payments that would require it to file Form(s) 1099?", B, "", False, 170, DR),
            ("B17b", "If 'Yes,' did the partnership file or will it file required Form(s) 1099?", B, "", False, 175, DR),
            ("B18", "At any time during the tax year, did the partnership (a) receive (as a reward, award, or payment for property or services); or (b) sell, exchange, or otherwise dispose of a digital asset?", B, "", False, 180, DR),
            # Partnership representative (BBA regime)
            ("B_REP_NAME", "Partnership representative name", T, "", False, 200, DR),
            ("B_REP_PHONE", "Partnership representative phone", T, "", False, 210, DR),
            ("B_REP_ADDRESS", "Partnership representative address", T, "", False, 220, DR),
            ("B_REP_SSN_EIN", "Partnership representative SSN or EIN", T, "", False, 230, DR),
        ],
    ),
    # ------ SCHEDULE F: PROFIT OR LOSS FROM FARMING ------
    (
        "sched_f",
        "Schedule F — Profit or Loss From Farming",
        27,
        [
            # Header fields
            ("FH_CROP", "Principal crop or activity", T, "", False, 1, DR),
            ("FH_CODE", "Agricultural activity code", T, "", False, 2, DR),
            ("FH_METHOD", "Accounting method", T, "", False, 3, DR),
            ("FH_EIN", "Employer ID number (EIN)", T, "", False, 4, DR),
            ("FH_PARTICIPATION", "Did you materially participate in the operation of this business during the tax year?", B, "", False, 5, DR),
            ("FH_1099_RECEIVED", "Did you receive an applicable subsidy in the tax year?", B, "", False, 6, DR),
            ("FH_1099_FILED", "If 'Yes,' did you file required Form(s) 1099?", B, "", False, 7, DR),
            # Part I — Farm Income
            ("F1a", "Sales of livestock and other resale items", C, "", False, 10, CR),
            ("F1b", "Cost or other basis of livestock and items sold", C, "", False, 20, DR),
            ("F1c", "Subtract line 1b from line 1a", C, "", True, 30, CR),
            ("F2", "Sales of livestock, produce, grains, and other products raised", C, "", False, 40, CR),
            ("F3", "Cooperative distributions", C, "", False, 50, CR),
            ("F4", "Agricultural program payments", C, "", False, 60, CR),
            ("F5", "Commodity Credit Corporation (CCC) loans", C, "", False, 70, CR),
            ("F6", "Crop insurance proceeds and federal crop disaster payments", C, "", False, 80, CR),
            ("F7", "Custom hire (machine work) income", C, "", False, 90, CR),
            ("F8", "Other farm income", C, "", False, 100, CR),
            ("F9", "Gross farm income (add lines 1c and 2 through 8)", C, "", True, 110, CR),
            # Part II — Farm Expenses
            ("F10", "Car and truck expenses", C, "", False, 200, DR),
            ("F11", "Chemicals", C, "", False, 210, DR),
            ("F12", "Conservation expenses", C, "", False, 220, DR),
            ("F13", "Custom hire (machine work)", C, "", False, 230, DR),
            ("F14", "Depreciation and section 179 expense", C, "", False, 240, DR),
            ("F15", "Employee benefit programs", C, "", False, 250, DR),
            ("F16", "Feed", C, "", False, 260, DR),
            ("F17", "Fertilizers and lime", C, "", False, 270, DR),
            ("F18", "Freight and trucking", C, "", False, 280, DR),
            ("F19", "Gasoline, fuel, and oil", C, "", False, 290, DR),
            ("F20", "Insurance (other than health)", C, "", False, 300, DR),
            ("F21a", "Interest — Mortgage (paid to banks, etc.)", C, "", False, 310, DR),
            ("F21b", "Interest — Other", C, "", False, 320, DR),
            ("F22", "Labor hired", C, "", False, 330, DR),
            ("F23", "Pension and profit-sharing plans", C, "", False, 340, DR),
            ("F24a", "Rent or lease — Vehicles, machinery, equipment", C, "", False, 350, DR),
            ("F24b", "Rent or lease — Other (land, animals, etc.)", C, "", False, 360, DR),
            ("F25", "Repairs and maintenance", C, "", False, 370, DR),
            ("F26", "Seeds and plants", C, "", False, 380, DR),
            ("F27", "Storage and warehousing", C, "", False, 390, DR),
            ("F28", "Supplies", C, "", False, 400, DR),
            ("F29", "Taxes", C, "", False, 410, DR),
            ("F30", "Utilities", C, "", False, 420, DR),
            ("F31", "Veterinary, breeding, and medicine", C, "", False, 430, DR),
            ("F32", "Other farm expenses", C, "", False, 440, DR),
            # Summary
            ("F33", "Total farm expenses (add lines 10 through 32)", C, "", True, 500, DR),
            ("F34", "Net farm profit or loss (line 9 minus line 33)", C, "", True, 510, CR),
        ],
    ),
    # ------ SCHEDULE K ------
    (
        "sched_k",
        "Schedule K — Partners' Distributive Share Items",
        30,
        [
            ("K1", "Ordinary business income (loss)", C, "", True, 10, CR),
            ("K2", "Net rental real estate income (loss)", C, "1065_K2", False, 20, CR),
            ("K3a", "Other gross rental income (loss)", C, "1065_K3a", False, 25, CR),
            ("K3b", "Expenses from other rental activities", C, "1065_K3b", False, 26, DR),
            ("K3c", "Other net rental income (loss)", C, "", True, 30, CR),
            # Guaranteed payments (partnership-specific)
            ("K4a", "Guaranteed payments for services", C, "", True, 35, CR),
            ("K4b", "Guaranteed payments for capital", C, "", True, 36, CR),
            ("K4c", "Total guaranteed payments", C, "", True, 37, CR),
            # Investment income
            ("K5", "Interest income", C, "1065_K5", False, 50, CR),
            ("K6a", "Ordinary dividends", C, "1065_K6a", False, 60, CR),
            ("K6b", "Qualified dividends", C, "1065_K6b", False, 70, CR),
            ("K7", "Royalties", C, "1065_K7", False, 80, CR),
            ("K8", "Net short-term capital gain (loss)", C, "1065_K8", False, 90, CR),
            ("K9a", "Net long-term capital gain (loss)", C, "1065_K9a", False, 100, CR),
            ("K9b", "Collectibles (28%) gain (loss)", C, "1065_K9b", False, 105, CR),
            ("K9c", "Unrecaptured section 1250 gain", C, "1065_K9c", False, 107, CR),
            ("K10", "Net section 1231 gain (loss)", C, "1065_K10", False, 110, CR),
            ("K11", "Other income (loss)", C, "1065_K11", False, 120, CR),
            ("K12", "Section 179 deduction", C, "1065_K12", False, 130, DR),
            ("K13a", "Charitable contributions", C, "1065_K13a", False, 140, DR),
            ("K13d", "Investment interest expense", C, "1065_K13d", False, 150, DR),
            # Self-employment earnings (partnership-specific)
            ("K14a", "Net earnings (loss) from self-employment", C, "", True, 160, DR),
            ("K14b", "Gross farming income (loss)", C, "", True, 162, CR),
            ("K14c", "Gross nonfarm income (loss)", C, "", True, 164, CR),
            # Credits
            ("K15a", "Low-income housing credit (section 42(j)(5))", C, "1065_K15a", False, 170, CR),
            # Foreign taxes
            ("K16a", "Foreign taxes paid or accrued", C, "1065_K16a", False, 180, CR),
            # AMT items
            ("K17a", "Post-1986 depreciation adjustment", C, "1065_K17a", False, 190, DR),
            # Tax-exempt income and nondeductible expenses
            ("K18a", "Tax-exempt interest income", C, "1065_K18a", False, 200, CR),
            ("K18b", "Other tax-exempt income", C, "1065_K18b", False, 205, CR),
            ("K18c", "Nondeductible expenses", C, "", True, 210, DR),
            # Distributions
            ("K19a", "Distributions of cash and marketable securities", C, "", True, 220, DR),
            ("K19b", "Distributions of other property", C, "1065_K19b", False, 225, DR),
            # Other information
            ("K20a", "Investment income", C, "1065_K20a", False, 230, CR),
            ("K20b", "Investment expenses", C, "1065_K20b", False, 235, DR),
        ],
    ),
    # ------ SCHEDULE L: BALANCE SHEET ------
    (
        "sched_l",
        "Schedule L — Balance Sheet per Books",
        40,
        [
            # Assets — Beginning of Year (col a) and End of Year (col d)
            ("L1a", "Cash — beginning of year", C, "1065_L1a_boy", False, 10, DR),
            ("L1d", "Cash — end of year", C, "1065_L1d_eoy", False, 20, DR),
            ("L2a", "Trade notes & accounts receivable — beginning", C, "1065_L2a_boy", False, 30, DR),
            ("L2b", "Less allowance for bad debts — beginning", C, "1065_L2b_boy", False, 32, CR),
            ("L2d", "Trade notes & accounts receivable — end", C, "1065_L2d_eoy", False, 35, DR),
            ("L2e", "Less allowance for bad debts — end", C, "1065_L2e_eoy", False, 37, CR),
            ("L3a", "Inventories — beginning", C, "1065_L3a_boy", False, 42, DR),
            ("L3d", "Inventories — end", C, "1065_L3d_eoy", False, 44, DR),
            ("L4a", "U.S. government obligations — beginning", C, "1065_L4a_boy", False, 46, DR),
            ("L4d", "U.S. government obligations — end", C, "1065_L4d_eoy", False, 47, DR),
            ("L5a", "Tax-exempt securities — beginning", C, "1065_L5a_boy", False, 48, DR),
            ("L5d", "Tax-exempt securities — end", C, "1065_L5d_eoy", False, 49, DR),
            ("L6a", "Other current assets — beginning", C, "1065_L6a_boy", False, 50, DR),
            ("L6d", "Other current assets — end", C, "1065_L6d_eoy", False, 51, DR),
            ("L7a", "Loans to partners — beginning", C, "1065_L7a_boy", False, 55, DR),
            ("L7d", "Loans to partners — end", C, "1065_L7d_eoy", False, 56, DR),
            ("L8a", "Mortgage and real estate loans — beginning", C, "1065_L8a_boy", False, 58, DR),
            ("L8d", "Mortgage and real estate loans — end", C, "1065_L8d_eoy", False, 59, DR),
            ("L9a", "Other investments — beginning", C, "1065_L9a_boy", False, 62, DR),
            ("L9d", "Other investments — end", C, "1065_L9d_eoy", False, 63, DR),
            ("L10a", "Buildings & other depreciable assets — beginning", C, "1065_L10a_boy", False, 70, DR),
            ("L10b", "Less accumulated depreciation — beginning", C, "1065_L10b_boy", False, 72, CR),
            ("L10d", "Buildings & other depreciable assets — end", C, "1065_L10d_eoy", False, 74, DR),
            ("L10e", "Less accumulated depreciation — end", C, "1065_L10e_eoy", False, 76, CR),
            ("L11a", "Depletable assets — beginning", C, "1065_L11a_boy", False, 78, DR),
            ("L11b", "Less accumulated depletion — beginning", C, "1065_L11b_boy", False, 79, CR),
            ("L11d", "Depletable assets — end", C, "1065_L11d_eoy", False, 80, DR),
            ("L11e", "Less accumulated depletion — end", C, "1065_L11e_eoy", False, 81, CR),
            ("L12a", "Land (net of any amortization) — beginning", C, "1065_L12a_boy", False, 82, DR),
            ("L12d", "Land (net of any amortization) — end", C, "1065_L12d_eoy", False, 83, DR),
            ("L13a", "Intangible assets — beginning", C, "1065_L13a_boy", False, 84, DR),
            ("L13b", "Less accumulated amortization — beginning", C, "1065_L13b_boy", False, 85, CR),
            ("L13d", "Intangible assets — end", C, "1065_L13d_eoy", False, 86, DR),
            ("L13e", "Less accumulated amortization — end", C, "1065_L13e_eoy", False, 87, CR),
            ("L14a", "Other assets — beginning", C, "1065_L14a_boy", False, 88, DR),
            ("L14d", "Other assets — end", C, "1065_L14d_eoy", False, 89, DR),
            ("L15a", "Total assets — beginning", C, "", True, 130, DR),
            ("L15d", "Total assets — end", C, "", True, 140, DR),
            # Liabilities (credit-normal)
            ("L16a", "Accounts payable — beginning", C, "1065_L16a_boy", False, 150, CR),
            ("L16d", "Accounts payable — end", C, "1065_L16d_eoy", False, 160, CR),
            ("L17a", "Mortgages, notes, bonds payable < 1 year — beginning", C, "1065_L17a_boy", False, 165, CR),
            ("L17d", "Mortgages, notes, bonds payable < 1 year — end", C, "1065_L17d_eoy", False, 166, CR),
            ("L18a", "Other current liabilities — beginning", C, "1065_L18a_boy", False, 170, CR),
            ("L18d", "Other current liabilities — end", C, "1065_L18d_eoy", False, 180, CR),
            ("L19a", "All nonrecourse loans — beginning", C, "1065_L19a_boy", False, 185, CR),
            ("L19d", "All nonrecourse loans — end", C, "1065_L19d_eoy", False, 186, CR),
            ("L20a", "Loans from partners — beginning", C, "1065_L20a_boy", False, 190, CR),
            ("L20d", "Loans from partners — end", C, "1065_L20d_eoy", False, 200, CR),
            ("L21a", "Mortgages, notes, bonds payable >= 1 year — beginning", C, "1065_L21a_boy", False, 205, CR),
            ("L21d", "Mortgages, notes, bonds payable >= 1 year — end", C, "1065_L21d_eoy", False, 206, CR),
            ("L22a", "Other liabilities — beginning", C, "1065_L22a_boy", False, 210, CR),
            ("L22d", "Other liabilities — end", C, "1065_L22d_eoy", False, 220, CR),
            # Capital (credit-normal)
            ("L23a", "Partners' capital accounts — beginning", C, "1065_L23a_boy", False, 230, CR),
            ("L23d", "Partners' capital accounts — end", C, "1065_L23d_eoy", False, 240, CR),
            ("L24a", "Total liabilities and capital — beginning", C, "", True, 250, CR),
            ("L24d", "Total liabilities and capital — end", C, "", True, 260, CR),
        ],
    ),
    # ------ SCHEDULE M-1 ------
    (
        "sched_m1",
        "Schedule M-1 — Reconciliation of Income (Loss) per Books with Income (Loss) per Return",
        50,
        [
            ("M1_1", "Net income (loss) per books", C, "1065_M1_1", False, 10, DR),
            ("M1_2", "Income included on Schedule K not recorded on books", C, "1065_M1_2", False, 20, DR),
            ("M1_3", "Guaranteed payments (other than health insurance)", C, "", True, 30, DR),
            ("M1_4a", "Expenses recorded on books not included on Schedule K (depreciation)", C, "1065_M1_4a", False, 35, DR),
            ("M1_4b", "Expenses recorded on books not included on Schedule K (travel, entertainment)", C, "", True, 37, DR),
            ("M1_4c", "Other expenses on books not on Schedule K", C, "1065_M1_4c", False, 38, DR),
            ("M1_5", "Add lines 1 through 4c", C, "", True, 50, DR),
            ("M1_6", "Income recorded on books not included on Schedule K (tax-exempt interest)", C, "1065_M1_6", False, 55, DR),
            ("M1_7a", "Deductions included on Schedule K not charged against books (depreciation)", C, "1065_M1_7a", False, 62, DR),
            ("M1_7b", "Other deductions on Schedule K not charged against books", C, "1065_M1_7b", False, 65, DR),
            ("M1_8", "Add lines 6 through 7b", C, "", True, 80, DR),
            ("M1_9", "Income (loss) (line 5 minus line 8)", C, "", True, 90, DR),
        ],
    ),
    # ------ SCHEDULE M-2 ------
    (
        "sched_m2",
        "Schedule M-2 — Analysis of Partners' Capital Accounts",
        60,
        [
            ("M2_1", "Balance at beginning of tax year", C, "1065_M2_1", False, 10, CR),
            ("M2_2a", "Capital contributed during year (cash)", C, "1065_M2_2a", False, 20, CR),
            ("M2_2b", "Capital contributed during year (property)", C, "1065_M2_2b", False, 30, CR),
            ("M2_3", "Net income (loss) per books", C, "1065_M2_3", False, 40, CR),
            ("M2_4", "Other increases", C, "1065_M2_4", False, 50, CR),
            ("M2_5", "Add lines 1 through 4", C, "", True, 60, DR),
            ("M2_6a", "Distributions (cash)", C, "1065_M2_6a", False, 70, DR),
            ("M2_6b", "Distributions (property)", C, "1065_M2_6b", False, 80, DR),
            ("M2_7", "Other decreases", C, "1065_M2_7", False, 90, DR),
            ("M2_8", "Add lines 6a through 7", C, "", True, 100, DR),
            ("M2_9", "Balance at end of tax year (line 5 minus line 8)", C, "", True, 110, CR),
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed the Form 1065 definition with sections and lines."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year", type=int, default=2025,
            help="Tax year to seed (default: 2025)",
        )

    def handle(self, *args, **options):
        year = options.get("year", 2025)
        form, created = FormDefinition.objects.update_or_create(
            code="1065",
            tax_year_applicable=year,
            defaults={
                "name": "U.S. Return of Partnership Income",
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} FormDefinition: {form}")

        line_count = 0
        for sec_code, sec_title, sec_order, lines in SECTIONS:
            section, _ = FormSection.objects.update_or_create(
                form=form,
                code=sec_code,
                defaults={"title": sec_title, "sort_order": sec_order},
            )

            new_line_numbers = {ln for ln, *_ in lines}
            for line_num, label, ftype, mkey, computed, sort, nbal in lines:
                FormLine.objects.update_or_create(
                    section=section,
                    line_number=line_num,
                    defaults={
                        "label": label,
                        "field_type": ftype,
                        "mapping_key": mkey,
                        "is_computed": computed,
                        "sort_order": sort,
                        "normal_balance": nbal,
                    },
                )
                line_count += 1

            # Remove stale lines
            stale = FormLine.objects.filter(section=section).exclude(
                line_number__in=new_line_numbers
            )
            stale_count = stale.count()
            if stale_count:
                fv_deleted, _ = FormFieldValue.objects.filter(
                    form_line__in=stale
                ).delete()
                stale.delete()
                self.stdout.write(
                    self.style.WARNING(
                        f"  Removed {stale_count} stale line(s) from {sec_code}"
                        f" ({fv_deleted} field values cleaned up)"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(SECTIONS)} sections, {line_count} lines for {form.code}."
            )
        )
