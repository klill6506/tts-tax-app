"""
Seed the Form 1120 definition with all sections and lines.

Run: poetry run python manage.py seed_1120
"""

from django.core.management.base import BaseCommand

from apps.returns.models import (
    FieldType,
    FormDefinition,
    FormLine,
    FormSection,
    NormalBalance,
)

# ---------------------------------------------------------------------------
# 1120 Line Definitions
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
    # ------ PAGE 1: INCOME ------
    (
        "page1_income",
        "Page 1 — Income",
        10,
        [
            ("1a", "Gross receipts or sales", C, "1120_L1a", False, 10, CR),
            ("1b", "Returns and allowances", C, "1120_L1b", False, 20, DR),
            ("1c", "Balance (1a minus 1b)", C, "", True, 30, DR),
            ("2", "Cost of goods sold (attach Form 1125-A)", C, "1120_L2", False, 40, DR),
            ("3", "Gross profit (1c minus 2)", C, "", True, 50, DR),
            ("4", "Dividends and inclusions (Schedule C, line 19)", C, "1120_L4", False, 60, CR),
            ("5", "Interest", C, "1120_L5", False, 70, CR),
            ("6", "Gross rents", C, "1120_L6", False, 80, CR),
            ("7", "Gross royalties", C, "1120_L7", False, 90, CR),
            ("8", "Capital gain net income (attach Schedule D)", C, "1120_L8", False, 100, CR),
            ("9", "Net gain or (loss) from Form 4797", C, "1120_L9", False, 110, CR),
            ("10", "Other income", C, "1120_L10", False, 120, CR),
            ("11", "Total income (add lines 3 through 10)", C, "", True, 130, DR),
        ],
    ),
    # ------ PAGE 1: DEDUCTIONS ------
    (
        "page1_deductions",
        "Page 1 — Deductions",
        20,
        [
            ("12", "Compensation of officers (attach Form 1125-E)", C, "1120_L12", False, 10, DR),
            ("13", "Salaries and wages", C, "1120_L13", False, 20, DR),
            ("14", "Repairs and maintenance", C, "1120_L14", False, 30, DR),
            ("15", "Bad debts", C, "1120_L15", False, 40, DR),
            ("16", "Rents", C, "1120_L16", False, 50, DR),
            ("17", "Taxes and licenses", C, "1120_L17", False, 60, DR),
            ("18", "Interest", C, "1120_L18", False, 70, DR),
            ("19", "Charitable contributions", C, "1120_L19", False, 80, DR),
            ("20", "Depreciation from Form 4562", C, "1120_L20", False, 90, DR),
            ("21", "Depletion", C, "1120_L21", False, 100, DR),
            ("22", "Advertising", C, "1120_L22", False, 110, DR),
            ("23", "Pension, profit-sharing, etc., plans", C, "1120_L23", False, 120, DR),
            ("24", "Employee benefit programs", C, "1120_L24", False, 130, DR),
            ("25", "Domestic production activities deduction", C, "1120_L25", False, 140, DR),
            ("26", "Other deductions (attach statement)", C, "1120_L26", False, 150, DR),
            ("27", "Total deductions (add lines 12 through 26)", C, "", True, 160, DR),
            ("28", "Taxable income before NOL deduction and special deductions (11 minus 27)", C, "", True, 170, DR),
            ("29a", "NOL deduction", C, "1120_L29a", False, 180, DR),
            ("29b", "Special deductions (Schedule C, line 24)", C, "1120_L29b", False, 190, DR),
            ("29c", "Add lines 29a and 29b", C, "", True, 200, DR),
            ("30", "Taxable income (line 28 minus line 29c)", C, "", True, 210, DR),
        ],
    ),
    # ------ PAGE 1: TAX, CREDITS, PAYMENTS ------
    (
        "page1_tax",
        "Page 1 — Tax, Credits, Payments",
        30,
        [
            ("31", "Total tax (Schedule J, line 10)", C, "", True, 10, DR),
            ("32", "Total payments and credits", C, "1120_L32", False, 20, DR),
            ("33", "Estimated tax penalty", C, "1120_L33", False, 30, DR),
            ("34", "Amount owed", C, "", True, 40, DR),
            ("35", "Overpayment", C, "", True, 50, CR),
            ("36", "Credited to estimated tax", C, "1120_L36", False, 60, DR),
        ],
    ),
    # ------ SCHEDULE C: DIVIDENDS, INCLUSIONS, AND SPECIAL DEDUCTIONS ------
    (
        "sched_c",
        "Schedule C — Dividends, Inclusions, and Special Deductions",
        40,
        [
            ("C1", "Dividends from less-than-20%-owned domestic corporations", C, "1120_C1", False, 10, CR),
            ("C2", "Dividends from 20%-or-more-owned domestic corporations", C, "1120_C2", False, 20, CR),
            ("C3", "Dividends on certain debt-financed stock", C, "1120_C3", False, 30, CR),
            ("C4", "Dividends on certain preferred stock of public utilities (<20%)", C, "1120_C4", False, 40, CR),
            ("C5", "Dividends on certain preferred stock of public utilities (20%+)", C, "1120_C5", False, 50, CR),
            ("C6", "Dividends from less-than-20%-owned foreign corporations", C, "1120_C6", False, 60, CR),
            ("C7", "Dividends from 20%-or-more-owned foreign corporations", C, "1120_C7", False, 70, CR),
            ("C8", "Wholly owned foreign subsidiary dividends", C, "1120_C8", False, 80, CR),
            ("C9", "Subtotal (add lines 1 through 8)", C, "", True, 90, CR),
            ("C10", "Dividends from domestic corps received by SBICs", C, "1120_C10", False, 100, CR),
            ("C11", "Dividends from affiliated group members", C, "1120_C11", False, 110, CR),
            ("C12", "Dividends from certain FSCs", C, "1120_C12", False, 120, CR),
            ("C13", "Foreign-source portion of dividends from 10%+ owned foreign corp", C, "1120_C13", False, 130, CR),
            ("C14", "Dividends from foreign corps not included on other lines", C, "1120_C14", False, 140, CR),
            ("C15", "Subpart F income from controlled foreign corporations", C, "1120_C15", False, 150, CR),
            ("C16", "Foreign dividend gross-up (section 78)", C, "1120_C16", False, 160, CR),
            ("C17", "IC-DISC and former DISC dividends", C, "1120_C17", False, 170, CR),
            ("C18", "Other dividends", C, "1120_C18", False, 180, CR),
            ("C19", "Deduction for dividends paid on certain preferred stock", C, "1120_C19", False, 190, CR),
            ("C20", "Total dividends and inclusions (add lines 9 through 18)", C, "", True, 200, CR),
            ("C21", "Total special deductions", C, "", True, 210, DR),
        ],
    ),
    # ------ SCHEDULE J: TAX COMPUTATION ------
    (
        "sched_j",
        "Schedule J — Tax Computation",
        50,
        [
            ("J1", "Taxable income (line 30, page 1)", C, "", True, 10, DR),
            ("J2", "Tax (21% flat rate)", C, "", True, 20, DR),
            ("J3", "Alternative minimum tax", C, "1120_J3", False, 30, DR),
            ("J4", "Add lines 2 and 3", C, "", True, 40, DR),
            ("J5a", "Foreign tax credit (Form 1118)", C, "1120_J5a", False, 50, DR),
            ("J5b", "General business credit (Form 3800)", C, "1120_J5b", False, 60, DR),
            ("J5c", "Credit for prior year minimum tax (Form 8827)", C, "1120_J5c", False, 70, DR),
            ("J5d", "Other credits", C, "1120_J5d", False, 80, DR),
            ("J5e", "Total credits (add lines 5a through 5d)", C, "", True, 90, DR),
            ("J6", "Subtract line 5e from line 4", C, "", True, 100, DR),
            ("J7", "Personal holding company tax (Schedule PH)", C, "1120_J7", False, 110, DR),
            ("J8", "Other taxes", C, "1120_J8", False, 120, DR),
            ("J9", "Total tax (add lines 6, 7, and 8)", C, "", True, 130, DR),
            ("J10", "Estimated tax payments", C, "1120_J10", False, 140, DR),
        ],
    ),
    # ------ SCHEDULE K: OTHER INFORMATION ------
    (
        "sched_k",
        "Schedule K — Other Information",
        60,
        [
            ("K1", "Accounting method", T, "1120_K1", False, 10, DR),
            ("K2", "Business activity code", T, "1120_K2", False, 20, DR),
            ("K3", "Business activity", T, "1120_K3", False, 30, DR),
            ("K4", "Product or service", T, "1120_K4", False, 40, DR),
            ("K5", "Is the corporation a member of a controlled group?", B, "1120_K5", False, 50, DR),
            ("K6", "Did the corp own 20%+ of voting stock of foreign or domestic corp?", B, "1120_K6", False, 60, DR),
        ],
    ),
    # ------ SCHEDULE L: BALANCE SHEET PER BOOKS ------
    (
        "sched_l",
        "Schedule L — Balance Sheet per Books",
        70,
        [
            # Assets — Beginning of Year (BOY) and End of Year (EOY)
            ("L1a", "Cash — beginning of year", C, "1120_L1a_boy", False, 10, DR),
            ("L1d", "Cash — end of year", C, "1120_L1d_eoy", False, 20, DR),
            ("L2a", "Trade notes & accounts receivable — beginning", C, "1120_L2a_boy", False, 30, DR),
            ("L2b", "Less allowance for bad debts — beginning", C, "1120_L2b_boy", False, 40, CR),
            ("L2d", "Trade notes & accounts receivable — end", C, "1120_L2d_eoy", False, 50, DR),
            ("L2e", "Less allowance for bad debts — end", C, "1120_L2e_eoy", False, 60, CR),
            ("L3a", "Inventories — beginning", C, "1120_L3a_boy", False, 70, DR),
            ("L3d", "Inventories — end", C, "1120_L3d_eoy", False, 80, DR),
            ("L4a", "U.S. government obligations — beginning", C, "1120_L4a_boy", False, 90, DR),
            ("L4d", "U.S. government obligations — end", C, "1120_L4d_eoy", False, 100, DR),
            ("L5a", "Tax-exempt securities — beginning", C, "1120_L5a_boy", False, 110, DR),
            ("L5d", "Tax-exempt securities — end", C, "1120_L5d_eoy", False, 120, DR),
            ("L6a", "Other current assets — beginning", C, "1120_L6a_boy", False, 130, DR),
            ("L6d", "Other current assets — end", C, "1120_L6d_eoy", False, 140, DR),
            ("L7a", "Loans to stockholders — beginning", C, "1120_L7a_boy", False, 150, DR),
            ("L7d", "Loans to stockholders — end", C, "1120_L7d_eoy", False, 160, DR),
            ("L8a", "Mortgage and real estate loans — beginning", C, "1120_L8a_boy", False, 170, DR),
            ("L8d", "Mortgage and real estate loans — end", C, "1120_L8d_eoy", False, 180, DR),
            ("L9a", "Other investments — beginning", C, "1120_L9a_boy", False, 190, DR),
            ("L9d", "Other investments — end", C, "1120_L9d_eoy", False, 200, DR),
            ("L10a", "Buildings & other depreciable assets — beginning", C, "1120_L10a_boy", False, 210, DR),
            ("L10b", "Less accumulated depreciation — beginning", C, "1120_L10b_boy", False, 220, CR),
            ("L10d", "Buildings & other depreciable assets — end", C, "1120_L10d_eoy", False, 230, DR),
            ("L10e", "Less accumulated depreciation — end", C, "1120_L10e_eoy", False, 240, CR),
            ("L11a", "Depletable assets — beginning", C, "1120_L11a_boy", False, 250, DR),
            ("L11b", "Less accumulated depletion — beginning", C, "1120_L11b_boy", False, 260, CR),
            ("L11d", "Depletable assets — end", C, "1120_L11d_eoy", False, 270, DR),
            ("L11e", "Less accumulated depletion — end", C, "1120_L11e_eoy", False, 280, CR),
            ("L12a", "Land (net of any amortization) — beginning", C, "1120_L12a_boy", False, 290, DR),
            ("L12d", "Land (net of any amortization) — end", C, "1120_L12d_eoy", False, 300, DR),
            ("L13a", "Intangible assets (amortizable only) — beginning", C, "1120_L13a_boy", False, 310, DR),
            ("L13b", "Less accumulated amortization — beginning", C, "1120_L13b_boy", False, 320, CR),
            ("L13d", "Intangible assets (amortizable only) — end", C, "1120_L13d_eoy", False, 330, DR),
            ("L13e", "Less accumulated amortization — end", C, "1120_L13e_eoy", False, 340, CR),
            ("L14a", "Other assets — beginning", C, "1120_L14a_boy", False, 350, DR),
            ("L14d", "Other assets — end", C, "1120_L14d_eoy", False, 360, DR),
            ("L15a", "Total assets — beginning", C, "", True, 370, DR),
            ("L15d", "Total assets — end", C, "", True, 380, DR),
            # Liabilities
            ("L16a", "Accounts payable — beginning", C, "1120_L16a_boy", False, 390, CR),
            ("L16d", "Accounts payable — end", C, "1120_L16d_eoy", False, 400, CR),
            ("L17a", "Mortgages, notes, bonds payable (<1 year) — beginning", C, "1120_L17a_boy", False, 410, CR),
            ("L17d", "Mortgages, notes, bonds payable (<1 year) — end", C, "1120_L17d_eoy", False, 420, CR),
            ("L18a", "Other current liabilities — beginning", C, "1120_L18a_boy", False, 430, CR),
            ("L18d", "Other current liabilities — end", C, "1120_L18d_eoy", False, 440, CR),
            ("L19a", "Loans from stockholders — beginning", C, "1120_L19a_boy", False, 450, CR),
            ("L19d", "Loans from stockholders — end", C, "1120_L19d_eoy", False, 460, CR),
            ("L20a", "Mortgages, notes, bonds payable (1 year or more) — beginning", C, "1120_L20a_boy", False, 470, CR),
            ("L20d", "Mortgages, notes, bonds payable (1 year or more) — end", C, "1120_L20d_eoy", False, 480, CR),
            ("L21a", "Other liabilities — beginning", C, "1120_L21a_boy", False, 490, CR),
            ("L21d", "Other liabilities — end", C, "1120_L21d_eoy", False, 500, CR),
            # Shareholders' Equity
            ("L22a_pref", "Capital stock: preferred — beginning", C, "1120_L22a_pref_boy", False, 510, CR),
            ("L22d_pref", "Capital stock: preferred — end", C, "1120_L22d_pref_eoy", False, 520, CR),
            ("L22a_com", "Capital stock: common — beginning", C, "1120_L22a_com_boy", False, 530, CR),
            ("L22d_com", "Capital stock: common — end", C, "1120_L22d_com_eoy", False, 540, CR),
            ("L23a", "Additional paid-in capital — beginning", C, "1120_L23a_boy", False, 550, CR),
            ("L23d", "Additional paid-in capital — end", C, "1120_L23d_eoy", False, 560, CR),
            ("L24a", "Retained earnings — appropriated — beginning", C, "1120_L24a_boy", False, 570, CR),
            ("L24d", "Retained earnings — appropriated — end", C, "1120_L24d_eoy", False, 580, CR),
            ("L25a", "Retained earnings — unappropriated — beginning", C, "1120_L25a_boy", False, 590, CR),
            ("L25d", "Retained earnings — unappropriated — end", C, "1120_L25d_eoy", False, 600, CR),
            ("L26a", "Adjustments to shareholders' equity — beginning", C, "1120_L26a_boy", False, 610, CR),
            ("L26d", "Adjustments to shareholders' equity — end", C, "1120_L26d_eoy", False, 620, CR),
            ("L27a", "Less cost of treasury stock — beginning", C, "1120_L27a_boy", False, 630, DR),
            ("L27d", "Less cost of treasury stock — end", C, "1120_L27d_eoy", False, 640, DR),
            ("L28a", "Total liabilities and shareholders' equity — beginning", C, "", True, 650, CR),
            ("L28d", "Total liabilities and shareholders' equity — end", C, "", True, 660, CR),
        ],
    ),
    # ------ SCHEDULE M-1: RECONCILIATION ------
    (
        "sched_m1",
        "Schedule M-1 — Reconciliation of Income (Loss) per Books With Income per Return",
        80,
        [
            ("M1_1", "Net income (loss) per books", C, "1120_M1_1", False, 10, DR),
            ("M1_2", "Federal income tax per books", C, "1120_M1_2", False, 20, DR),
            ("M1_3", "Excess of capital losses over capital gains", C, "1120_M1_3", False, 30, DR),
            ("M1_4", "Income subject to tax not recorded on books this year", C, "1120_M1_4", False, 40, DR),
            ("M1_5a", "Expenses on books not deducted on return — depreciation", C, "1120_M1_5a", False, 50, DR),
            ("M1_5b", "Expenses on books not deducted on return — charitable contributions", C, "1120_M1_5b", False, 60, DR),
            ("M1_5c", "Expenses on books not deducted on return — travel and entertainment", C, "1120_M1_5c", False, 70, DR),
            ("M1_5d", "Expenses on books not deducted on return — other", C, "1120_M1_5d", False, 80, DR),
            ("M1_6", "Add lines 1 through 5", C, "", True, 90, DR),
            ("M1_7a", "Income on books not included on return — tax-exempt interest", C, "1120_M1_7a", False, 100, DR),
            ("M1_7b", "Income on books not included on return — other", C, "1120_M1_7b", False, 110, DR),
            ("M1_8a", "Deductions on return not charged against book income — depreciation", C, "1120_M1_8a", False, 120, DR),
            ("M1_8b", "Deductions on return not charged against book income — other", C, "1120_M1_8b", False, 130, DR),
            ("M1_9", "Add lines 7 and 8", C, "", True, 140, DR),
            ("M1_10", "Taxable income (line 28, page 1) — line 6 less line 9", C, "", True, 150, DR),
        ],
    ),
    # ------ SCHEDULE M-2: UNAPPROPRIATED RETAINED EARNINGS ------
    (
        "sched_m2",
        "Schedule M-2 — Analysis of Unappropriated Retained Earnings per Books",
        90,
        [
            ("M2_1", "Balance at beginning of year", C, "1120_M2_1", False, 10, CR),
            ("M2_2", "Net income (loss) per books", C, "1120_M2_2", False, 20, CR),
            ("M2_3", "Other increases (itemize)", C, "1120_M2_3", False, 30, CR),
            ("M2_4", "Add lines 1, 2, and 3", C, "", True, 40, DR),
            ("M2_5a", "Distributions — cash", C, "1120_M2_5a", False, 50, DR),
            ("M2_5b", "Distributions — stock", C, "1120_M2_5b", False, 60, DR),
            ("M2_5c", "Distributions — property", C, "1120_M2_5c", False, 70, DR),
            ("M2_6", "Other decreases (itemize)", C, "1120_M2_6", False, 80, DR),
            ("M2_7", "Add lines 5 and 6", C, "", True, 90, DR),
            ("M2_8", "Balance at end of year (line 4 less line 7)", C, "", True, 100, CR),
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed the Form 1120 definition with sections and lines."

    def handle(self, *args, **options):
        form, created = FormDefinition.objects.update_or_create(
            code="1120",
            defaults={
                "name": "U.S. Corporation Income Tax Return",
                "tax_year_applicable": 2025,
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(SECTIONS)} sections, {line_count} lines for {form.code}."
            )
        )
