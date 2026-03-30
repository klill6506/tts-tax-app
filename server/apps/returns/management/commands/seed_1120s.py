"""
Seed the Form 1120-S definition with all sections and lines.

Run: poetry run python manage.py seed_1120s
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
# 1120-S Line Definitions
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
            ("1a", "Gross receipts or sales", C, "1120S_L1a", False, 10, CR),
            ("1b", "Returns and allowances", C, "1120S_L1b", False, 20, DR),
            ("1c", "Balance (1a minus 1b)", C, "", True, 30, DR),
            ("2", "Cost of goods sold (Schedule A, line 8)", C, "", True, 40, DR),
            ("3", "Gross profit (1c minus 2)", C, "", True, 50, DR),
            ("4", "Net gain (loss) from Form 4797", C, "1120S_L4", False, 60, DR),
            ("5", "Other income (loss)", C, "1120S_L5", False, 70, CR),
            ("6", "Total income (loss) (3 + 4 + 5)", C, "", True, 80, DR),
        ],
    ),
    # ------ SCHEDULE A: COST OF GOODS SOLD ------
    (
        "sched_a",
        "Schedule A — Cost of Goods Sold",
        15,
        [
            ("A1", "Inventory at beginning of year", C, "1120S_A1", False, 10, DR),
            ("A2", "Purchases", C, "1120S_A2", False, 20, DR),
            ("A3", "Cost of labor", C, "1120S_A3", False, 30, DR),
            ("A4", "Additional section 263A costs", C, "1120S_A4", False, 40, DR),
            ("A5", "Other costs", C, "1120S_A5", False, 50, DR),
            ("A6", "Total (add lines 1 through 5)", C, "", True, 60, DR),
            ("A7", "Inventory at end of year", C, "1120S_A7", False, 70, DR),
            ("A8", "Cost of goods sold (line 6 minus line 7)", C, "", True, 80, DR),
            # Inventory method indicators (Form 1125-A, line 9)
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
            # IRS form lines 7–18 (map to specific 1120-S page 1 lines)
            ("7", "Compensation of officers", C, "1120S_L7", False, 10, DR),
            ("8", "Salaries and wages", C, "1120S_L8", False, 20, DR),
            ("9", "Repairs and maintenance", C, "1120S_L9", False, 30, DR),
            ("10", "Bad debts", C, "1120S_L10", False, 40, DR),
            ("11", "Rents", C, "1120S_L11", False, 50, DR),
            ("12", "Taxes and licenses", C, "1120S_L12", False, 60, DR),
            ("13", "Interest", C, "1120S_L13", False, 70, DR),
            ("14", "Depreciation (not 4562)", C, "1120S_L14", False, 80, DR),
            ("15", "Depletion", C, "1120S_L15", False, 90, DR),
            ("16", "Advertising", C, "1120S_L16", False, 100, DR),
            ("17", "Pension/Profit-Sharing", C, "1120S_L17", False, 110, DR),
            ("18", "Employee benefit programs", C, "1120S_L18", False, 120, DR),
            # Named deductions (roll up to Line 19 "Other deductions" statement)
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
            # Free-form deduction rows (user enters description + amount)
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
            ("19", "Other deductions", C, "1120S_L19", True, 600, DR),
            ("20", "Total deductions", C, "", True, 610, DR),
            ("21", "Ordinary business income (loss)", C, "", True, 620, DR),
        ],
    ),
    # ------ SCHEDULE B: OTHER INFORMATION ------
    # Questions 1 & 2 (accounting method, business activity) are on the
    # TaxReturn model / Info tab — not stored as FormLines.
    (
        "sched_b",
        "Schedule B — Other Information",
        25,
        [
            ("B3", "At any time during the tax year, was any shareholder of the corporation a disregarded entity, a trust, an estate, or a nominee or similar person?", B, "", False, 30, DR),
            ("B4a", "At the end of the tax year, did the corporation own, directly or indirectly, 50% or more of the total stock issued and outstanding of any foreign or domestic corporation?", B, "", False, 40, DR),
            ("B4b", "Did the corporation own directly an interest of 20% or more, or own, directly or indirectly, an interest of 50% or more, in the profit, loss, or capital in any foreign or domestic partnership?", B, "", False, 45, DR),
            ("B5a", "At the end of the tax year, did the corporation have any outstanding shares of restricted stock?", B, "", False, 50, DR),
            ("B5b", "At the end of the tax year, did the corporation have any outstanding stock options, warrants, or similar instruments?", B, "", False, 55, DR),
            ("B6", "Has this corporation filed, or is it required to file, Form 8918, Material Advisor Disclosure Statement?", B, "", False, 60, DR),
            ("B7", "Check this box if the corporation issued publicly offered debt instruments with original issue discount.", B, "", False, 70, DR),
            ("B8", "If the corporation was a C corporation before it elected to be an S corporation or acquired an asset with a basis determined by reference to a C corporation's basis, and has net unrealized built-in gain in excess of the net recognized built-in gain from prior years, enter the net unrealized built-in gain reduced by net recognized built-in gain from prior years.", C, "", False, 80, DR),
            ("B9", "Did the corporation have an election under section 163(j) for any real property trade or business or any farming business in effect during the tax year?", B, "", False, 90, DR),
            ("B10", "Does the corporation satisfy one or more of the following? (a) Owns a pass-through entity with current, or prior year carryover, excess business interest expense. (b) Aggregate average annual gross receipts for the 3 preceding tax years are more than $31 million. (c) Is a tax shelter with business interest expense.", B, "", False, 100, DR),
            ("B11", "Does the corporation satisfy both of the following conditions? (a) Total receipts for the tax year were less than $250,000. (b) Total assets at the end of the tax year were less than $250,000.", B, "", False, 110, DR),
            ("B12", "During the tax year, did the corporation have any non-shareholder debt that was canceled, was forgiven, or had the terms modified so as to reduce the principal amount of the debt?", B, "", False, 120, DR),
            ("B13", "During the tax year, was a qualified subchapter S subsidiary election terminated or revoked?", B, "", False, 130, DR),
            ("B14a", "During the tax year, did the corporation make any payments that would require it to file Form(s) 1099?", B, "", False, 140, DR),
            ("B14b", "If 'Yes,' did the corporation file or will it file required Form(s) 1099?", B, "", False, 145, DR),
            ("B15", "Does the corporation intend to self-certify as a Qualified Opportunity Fund?", B, "", False, 150, DR),
            ("B16", "At any time during the tax year, did the corporation (a) receive (as a reward, award, or payment for property or services); or (b) sell, exchange, or otherwise dispose of a digital asset?", B, "", False, 160, DR),
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
    # ------ PAGE 1: TAX AND PAYMENTS ------
    (
        "page1_tax",
        "Page 1 — Tax and Payments",
        30,
        [
            ("22a", "Excess net passive income or LIFO tax", C, "1120S_L22a", False, 10, DR),
            ("22b", "Tax from Schedule D", C, "1120S_L22b", False, 20, DR),
            ("22c", "Add 22a and 22b", C, "", True, 30, DR),
            ("23a", "Estimated tax payments", C, "1120S_L23a", False, 40, DR),
            ("23b", "Tax deposited with Form 7004", C, "1120S_L23b", False, 50, DR),
            ("23c", "Credit for federal tax paid on fuels", C, "1120S_L23c", False, 60, DR),
            ("23d", "Total (23a + 23b + 23c)", C, "", True, 70, DR),
            ("24", "Estimated tax penalty", C, "1120S_L24", False, 80, DR),
            ("25", "Amount owed", C, "", True, 90, DR),
            ("26", "Overpayment", C, "", True, 100, DR),
            ("27", "Credited to estimated tax", C, "1120S_L27", False, 110, DR),
        ],
    ),
    # ------ SCHEDULE K ------
    (
        "sched_k",
        "Schedule K — Shareholders' Pro Rata Share Items",
        40,
        [
            ("K1", "Ordinary business income (loss)", C, "1120S_K1", True, 10, CR),
            ("K2", "Net rental real estate income (loss)", C, "1120S_K2", False, 20, CR),
            ("K3", "Other net rental income (loss)", C, "1120S_K3", False, 30, CR),
            ("K4", "Interest income", C, "1120S_K4", False, 40, CR),
            ("K5a", "Ordinary dividends", C, "1120S_K5a", False, 50, CR),
            ("K5b", "Qualified dividends", C, "1120S_K5b", False, 60, CR),
            ("K6", "Royalties", C, "1120S_K6", False, 70, CR),
            ("K7", "Net short-term capital gain (loss)", C, "1120S_K7", False, 80, CR),
            ("K8a", "Net long-term capital gain (loss)", C, "1120S_K8a", False, 90, CR),
            ("K8b", "Collectibles (28%) gain (loss)", C, "1120S_K8b", False, 92, CR),
            ("K8c", "Unrecaptured section 1250 gain", C, "1120S_K8c", True, 94, CR),
            ("K9", "Net section 1231 gain (loss)", C, "1120S_K9", False, 100, CR),
            ("K10", "Other income (loss)", C, "1120S_K10", False, 110, CR),
            ("K11", "Section 179 deduction", C, "1120S_K11", False, 120, DR),
            ("K12a", "Charitable contributions", C, "1120S_K12a", False, 130, DR),
            ("K12b", "Investment interest expense", C, "1120S_K12b", False, 132, DR),
            ("K12c", "Section 59(e)(2) expenditures", C, "1120S_K12c", False, 134, DR),
            ("K12d", "Other deductions", C, "1120S_K12d", False, 136, DR),
            ("K13a", "Low-income housing credit (section 42(j)(5))", C, "1120S_K13a", False, 140, DR),
            ("K13b", "Low-income housing credit (other)", C, "1120S_K13b", False, 141, DR),
            ("K13c", "Qualified rehabilitation expenditures", C, "1120S_K13c", False, 142, DR),
            ("K13d", "Other rental real estate credits", C, "1120S_K13d", False, 143, DR),
            ("K13e", "Other rental credits", C, "1120S_K13e", False, 144, DR),
            ("K13f", "Biofuel producer credit", C, "1120S_K13f", False, 145, DR),
            ("K13g", "Other credits", C, "1120S_K13g", False, 146, DR),
            ("K14a", "Name of country or U.S. possession", T, "1120S_K14a", False, 150, DR),
            ("K15a", "Post-1986 depreciation adjustment", C, "1120S_K15a", True, 160, DR),
            ("K15b", "Adjusted gain or loss", C, "1120S_K15b", False, 162, DR),
            ("K15c", "Depletion (other than oil & gas)", C, "1120S_K15c", False, 164, DR),
            ("K15d", "Oil, gas & geothermal — gross income", C, "1120S_K15d", False, 165, CR),
            ("K15e", "Oil, gas & geothermal — deductions", C, "1120S_K15e", False, 166, DR),
            ("K15f", "Other AMT items", C, "1120S_K15f", False, 168, DR),
            ("K16a", "Tax-exempt interest income", C, "1120S_K16a", False, 170, CR),
            ("K16b", "Other tax-exempt income", C, "1120S_K16b", False, 180, CR),
            ("K16c", "Nondeductible expenses", C, "1120S_K16c", True, 190, DR),
            ("K16d", "Distributions", C, "1120S_K16d", False, 200, DR),
            ("K17a", "Investment income", C, "1120S_K17a", False, 210, CR),
            ("K17b", "Investment expenses", C, "1120S_K17b", False, 220, DR),
            ("K17c", "Dividend equivalents", C, "1120S_K17c", False, 222, DR),
            # QBI (Section 199A) — flows to K-1 Box 17, Code V
            ("QBI_W2_WAGES", "Section 199A — W-2 wages paid", C, "1120S_QBI_W2", False, 225, DR),
            ("QBI_UBIA", "Section 199A — UBIA of qualified property", C, "1120S_QBI_UBIA", False, 226, DR),
            ("QBI_IS_SSTB", "Section 199A — SSTB indicator", B, "1120S_QBI_SSTB", False, 227, DR),
            ("K18", "Income (loss) reconciliation — total", C, "", True, 230, CR),
        ],
    ),
    # ------ SCHEDULE L: BALANCE SHEET ------
    (
        "sched_l",
        "Schedule L — Balance Sheet per Books",
        50,
        [
            # Assets — Beginning of Year (col a) and End of Year (col d)
            ("L1a", "Cash — beginning of year", C, "1120S_L1a_boy", False, 10, DR),
            ("L1d", "Cash — end of year", C, "1120S_L1d_eoy", False, 20, DR),
            ("L2a", "Trade notes & A/R — beginning", C, "1120S_L2a_boy", False, 30, DR),
            ("L2b", "Less allowance for bad debts — beginning", C, "1120S_L2b_boy", False, 32, CR),
            ("L2d", "Trade notes & A/R — end", C, "1120S_L2d_eoy", False, 35, DR),
            ("L2e", "Less allowance for bad debts — end", C, "1120S_L2e_eoy", False, 37, CR),
            ("L3a", "Inventories — beginning", C, "1120S_L3a_boy", False, 42, DR),
            ("L3d", "Inventories — end", C, "1120S_L3d_eoy", True, 44, DR),
            ("L4a", "U.S. government obligations — beginning", C, "1120S_L4a_boy", False, 46, DR),
            ("L4d", "U.S. government obligations — end", C, "1120S_L4d_eoy", False, 47, DR),
            ("L5a", "Tax-exempt securities — beginning", C, "1120S_L5a_boy", False, 48, DR),
            ("L5d", "Tax-exempt securities — end", C, "1120S_L5d_eoy", False, 49, DR),
            ("L6a", "Other current assets — beginning", C, "1120S_L6a_boy", False, 50, DR),
            ("L6d", "Other current assets — end", C, "1120S_L6d_eoy", False, 51, DR),
            ("L7a", "Loans to shareholders — beginning", C, "1120S_L7a_boy", False, 55, DR),
            ("L7d", "Loans to shareholders — end", C, "1120S_L7d_eoy", False, 56, DR),
            ("L8a", "Mortgage and real estate loans — beginning", C, "1120S_L8a_boy", False, 58, DR),
            ("L8d", "Mortgage and real estate loans — end", C, "1120S_L8d_eoy", False, 59, DR),
            ("L9a", "Other investments — beginning", C, "1120S_L9a_boy", False, 62, DR),
            ("L9d", "Other investments — end", C, "1120S_L9d_eoy", False, 63, DR),
            ("L10a", "Buildings & other depreciable assets — beginning", C, "1120S_L10a_boy", False, 70, DR),
            ("L10b", "Less accumulated depreciation — beginning", C, "1120S_L10b_boy", False, 72, CR),
            ("L10d", "Buildings & other depreciable assets — end", C, "1120S_L10d_eoy", True, 74, DR),
            ("L10e", "Less accumulated depreciation — end", C, "1120S_L10e_eoy", True, 76, CR),
            ("L11a", "Depletable assets — beginning", C, "1120S_L11a_boy", False, 78, DR),
            ("L11b", "Less accumulated depletion — beginning", C, "1120S_L11b_boy", False, 79, CR),
            ("L11d", "Depletable assets — end", C, "1120S_L11d_eoy", False, 80, DR),
            ("L11e", "Less accumulated depletion — end", C, "1120S_L11e_eoy", False, 81, CR),
            ("L12a", "Land (net of any amortization) — beginning", C, "1120S_L12a_boy", False, 82, DR),
            ("L12d", "Land (net of any amortization) — end", C, "1120S_L12d_eoy", False, 83, DR),
            ("L13a", "Intangible assets — beginning", C, "1120S_L13a_boy", False, 84, DR),
            ("L13b", "Less accumulated amortization — beginning", C, "1120S_L13b_boy", False, 85, CR),
            ("L13d", "Intangible assets — end", C, "1120S_L13d_eoy", True, 86, DR),
            ("L13e", "Less accumulated amortization — end", C, "1120S_L13e_eoy", True, 87, CR),
            ("L14a", "Other assets — beginning", C, "1120S_L14a_boy", False, 88, DR),
            ("L14d", "Other assets — end", C, "1120S_L14d_eoy", False, 89, DR),
            ("L15a", "Total assets — beginning", C, "", True, 130, DR),
            ("L15d", "Total assets — end", C, "", True, 140, DR),
            # Liabilities (credit-normal)
            ("L16a", "Accounts payable — beginning", C, "1120S_L16a_boy", False, 150, CR),
            ("L16d", "Accounts payable — end", C, "1120S_L16d_eoy", False, 160, CR),
            ("L17a", "Mortgages, notes, bonds payable < 1 year — beginning", C, "1120S_L17a_boy", False, 165, CR),
            ("L17d", "Mortgages, notes, bonds payable < 1 year — end", C, "1120S_L17d_eoy", False, 166, CR),
            ("L18a", "Other current liabilities — beginning", C, "1120S_L18a_boy", False, 170, CR),
            ("L18d", "Other current liabilities — end", C, "1120S_L18d_eoy", False, 180, CR),
            ("L19a", "Loans from shareholders — beginning", C, "1120S_L19a_boy", False, 190, CR),
            ("L19d", "Loans from shareholders — end", C, "1120S_L19d_eoy", False, 200, CR),
            ("L20a", "Mortgages, notes, bonds payable >= 1 year — beginning", C, "1120S_L20a_boy", False, 205, CR),
            ("L20d", "Mortgages, notes, bonds payable >= 1 year — end", C, "1120S_L20d_eoy", False, 206, CR),
            ("L21a", "Other liabilities — beginning", C, "1120S_L21a_boy", False, 210, CR),
            ("L21d", "Other liabilities — end", C, "1120S_L21d_eoy", False, 220, CR),
            # Equity (credit-normal)
            ("L22a", "Capital stock — beginning", C, "1120S_L22a_boy", False, 230, CR),
            ("L22d", "Capital stock — end", C, "1120S_L22d_eoy", False, 240, CR),
            ("L23a", "Additional paid-in capital — beginning", C, "1120S_L23a_boy", False, 245, CR),
            ("L23d", "Additional paid-in capital — end", C, "1120S_L23d_eoy", False, 246, CR),
            ("L24a", "Retained earnings — beginning", C, "1120S_L24a_boy", False, 250, CR),
            ("L24d", "Retained earnings — end", C, "", True, 260, CR),
            ("L25a", "Adjustments to shareholders' equity — beginning", C, "1120S_L25a_boy", False, 265, CR),
            ("L25d", "Adjustments to shareholders' equity — end", C, "1120S_L25d_eoy", False, 266, CR),
            ("L26a", "Less cost of treasury stock — beginning", C, "1120S_L26a_boy", False, 270, DR),
            ("L26d", "Less cost of treasury stock — end", C, "1120S_L26d_eoy", False, 271, DR),
            ("L27a", "Total liabilities and shareholders' equity — beginning", C, "", True, 280, CR),
            ("L27d", "Total liabilities and shareholders' equity — end", C, "", True, 285, CR),
        ],
    ),
    # ------ SCHEDULE M-1 ------
    (
        "sched_m1",
        "Schedule M-1 — Reconciliation of Income (Loss)",
        60,
        [
            ("M1_1", "Net income (loss) per books", C, "", True, 10, DR),
            ("M1_2", "Income on Schedule K not on books", C, "1120S_M1_2", False, 20, DR),
            ("M1_3a", "Depreciation", C, "1120S_M1_3a", False, 30, DR),
            ("M1_3b", "Meals and entertainment", C, "", True, 35, DR),
            ("M1_3c", "Other expenses on books not on Sched K", C, "1120S_M1_3c", False, 38, DR),
            ("M1_4", "Add lines 1 through 3c", C, "", True, 50, DR),
            ("M1_5a", "Tax-exempt interest", C, "1120S_M1_5a", False, 55, DR),
            ("M1_5b", "Other income on books not on Sched K", C, "1120S_M1_5b", False, 58, DR),
            ("M1_6a", "Depreciation", C, "1120S_M1_6a", False, 62, DR),
            ("M1_6b", "Other deductions on Sched K not charged against books", C, "1120S_M1_6b", False, 65, DR),
            ("M1_7", "Add lines 5a through 6b", C, "", True, 80, DR),
            ("M1_8", "Income (loss) (Schedule K, line 18) (line 4 minus line 7)", C, "", True, 90, DR),
        ],
    ),
    # ------ SCHEDULE M-2 ------
    # 4 columns: (a) AAA, (b) OAA, (c) STPI, (d) Accumulated E&P
    (
        "sched_m2",
        "Schedule M-2 — Analysis of AAA, OAA, and STPI",
        70,
        [
            # Row 1 — Balance at beginning of tax year
            ("M2_1a", "Balance at BOY (AAA)", C, "1120S_M2_1a", False, 10, CR),
            ("M2_1b", "Balance at BOY (OAA)", C, "1120S_M2_1b", False, 11, CR),
            ("M2_1c", "Balance at BOY (STPI)", C, "1120S_M2_1c", False, 12, CR),
            ("M2_1d", "Balance at BOY (Accu E&P)", C, "1120S_M2_1d", False, 13, CR),
            # Row 2 — Ordinary income from page 1, line 21
            ("M2_2a", "Ordinary income (AAA)", C, "", True, 20, DR),
            ("M2_2b", "Ordinary income (OAA)", C, "1120S_M2_2b", False, 21, DR),
            ("M2_2c", "Ordinary income (STPI)", C, "1120S_M2_2c", False, 22, DR),
            ("M2_2d", "Ordinary income (Accu E&P)", C, "1120S_M2_2d", False, 23, DR),
            # Row 3 — Other additions
            ("M2_3a", "Other additions (AAA)", C, "1120S_M2_3a", True, 30, CR),
            ("M2_3b", "Other additions (OAA)", C, "1120S_M2_3b", False, 31, CR),
            ("M2_3c", "Other additions (STPI)", C, "1120S_M2_3c", False, 32, CR),
            ("M2_3d", "Other additions (Accu E&P)", C, "1120S_M2_3d", False, 33, CR),
            # Row 4 — Loss from page 1, line 21
            ("M2_4a", "Loss (AAA)", C, "", True, 40, DR),
            ("M2_4b", "Loss (OAA)", C, "1120S_M2_4b", False, 41, DR),
            ("M2_4c", "Loss (STPI)", C, "1120S_M2_4c", False, 42, DR),
            ("M2_4d", "Loss (Accu E&P)", C, "1120S_M2_4d", False, 43, DR),
            # Row 5 — Other reductions
            ("M2_5a", "Other reductions (AAA)", C, "", True, 50, DR),
            ("M2_5b", "Other reductions (OAA)", C, "1120S_M2_5b", False, 51, DR),
            ("M2_5c", "Other reductions (STPI)", C, "1120S_M2_5c", False, 52, DR),
            ("M2_5d", "Other reductions (Accu E&P)", C, "1120S_M2_5d", False, 53, DR),
            # Row 6 — Combine lines 1 through 5
            ("M2_6a", "Subtotal (AAA)", C, "", True, 60, DR),
            ("M2_6b", "Subtotal (OAA)", C, "", True, 61, DR),
            ("M2_6c", "Subtotal (STPI)", C, "", True, 62, DR),
            ("M2_6d", "Subtotal (Accu E&P)", C, "", True, 63, DR),
            # Row 7 — Distributions
            ("M2_7a", "Distributions (AAA)", C, "1120S_M2_7a", False, 70, DR),
            ("M2_7b", "Distributions (OAA)", C, "1120S_M2_7b", False, 71, DR),
            ("M2_7c", "Distributions (STPI)", C, "1120S_M2_7c", False, 72, DR),
            ("M2_7d", "Distributions (Accu E&P)", C, "1120S_M2_7d", False, 73, DR),
            # Row 8 — Balance at end of tax year (line 6 minus line 7)
            ("M2_8a", "Balance at EOY (AAA)", C, "", True, 80, DR),
            ("M2_8b", "Balance at EOY (OAA)", C, "", True, 81, DR),
            ("M2_8c", "Balance at EOY (STPI)", C, "", True, 82, DR),
            ("M2_8d", "Balance at EOY (Accu E&P)", C, "", True, 83, DR),
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed the Form 1120-S definition with sections and lines."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year", type=int, default=2025,
            help="Tax year to seed (default: 2025)",
        )

    def handle(self, *args, **options):
        year = options.get("year", 2025)
        form, created = FormDefinition.objects.update_or_create(
            code="1120-S",
            tax_year_applicable=year,
            defaults={
                "name": "U.S. Income Tax Return for an S Corporation",
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
                line, _ = FormLine.objects.update_or_create(
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
                # If this line is now computed, clear any manual overrides
                # on existing FormFieldValues so the formula takes effect.
                if computed:
                    FormFieldValue.objects.filter(
                        form_line=line,
                        is_overridden=True,
                    ).update(is_overridden=False)
                line_count += 1

            # Remove stale lines (e.g., old Schedule B entries)
            stale = FormLine.objects.filter(section=section).exclude(
                line_number__in=new_line_numbers
            )
            stale_count = stale.count()
            if stale_count:
                # Must delete protected FormFieldValues first
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
