"""
Seed the Form 1120-S definition with all sections and lines.

Run: poetry run python manage.py seed_1120s
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
        ],
    ),
    # ------ PAGE 1: DEDUCTIONS ------
    (
        "page1_deductions",
        "Page 1 — Deductions",
        20,
        [
            ("7", "Compensation of officers", C, "1120S_L7", False, 10, DR),
            ("8", "Salaries and wages", C, "1120S_L8", False, 20, DR),
            ("9", "Repairs and maintenance", C, "1120S_L9", False, 30, DR),
            ("10", "Bad debts", C, "1120S_L10", False, 40, DR),
            ("11", "Rents", C, "1120S_L11", False, 50, DR),
            ("12", "Taxes and licenses", C, "1120S_L12", False, 60, DR),
            ("13", "Interest", C, "1120S_L13", False, 70, DR),
            ("14", "Depreciation not on Form 4562", C, "1120S_L14", False, 80, DR),
            ("15", "Depletion", C, "1120S_L15", False, 90, DR),
            ("16", "Advertising", C, "1120S_L16", False, 100, DR),
            ("17", "Pension, profit-sharing, etc.", C, "1120S_L17", False, 110, DR),
            ("18", "Employee benefit programs", C, "1120S_L18", False, 120, DR),
            ("19", "Other deductions", C, "1120S_L19", False, 130, DR),
            ("20", "Total deductions (7 through 19)", C, "", True, 140, DR),
            ("21", "Ordinary business income (loss) (6 minus 20)", C, "", True, 150, DR),
        ],
    ),
    # ------ SCHEDULE B: OTHER INFORMATION ------
    (
        "sched_b",
        "Schedule B — Other Information",
        25,
        [
            ("B1", "Check accounting method used", T, "", False, 10, DR),
            ("B2", "Are the corporation's total receipts for the tax year less than $250,000?", B, "", False, 20, DR),
            ("B3", "Is this corporation a member of a controlled group?", B, "", False, 30, DR),
            ("B3_name", "Name of controlling entity", T, "", False, 35, DR),
            ("B3_ein", "EIN of controlling entity", T, "", False, 36, DR),
            ("B4", "At any time during the tax year, did any foreign or domestic corporation, partnership, trust, or tax-exempt organization own directly 20% or more of the stock?", B, "", False, 40, DR),
            ("B5", "At the end of the tax year, did any individual, partnership, corporation, estate, or trust own directly 20% or more of the stock?", B, "", False, 50, DR),
            ("B6", "Does the corporation have an election under section 444 in effect?", B, "", False, 60, DR),
            ("B7a", "Does the corporation have qualified subchapter S subsidiaries?", B, "", False, 70, DR),
            ("B7a_count", "Number of qualified subchapter S subsidiaries", I, "", False, 75, DR),
            ("B8", "Did the corporation have any debt that was canceled, forgiven, or had the terms modified?", B, "", False, 80, DR),
            ("B9", "Did the corporation make the section 163(j)(7)(B) election?", B, "", False, 90, DR),
            ("B10", "Has the corporation filed, or is it required to file, Form 8990?", B, "", False, 100, DR),
            ("B11", "Does the corporation have oil and gas activities?", B, "", False, 110, DR),
            ("B12", "Is the corporation required to file Form 8918, Material Advisor Disclosure Statement?", B, "", False, 120, DR),
            ("B13a", "Was there a transfer of property to the S corporation?", B, "", False, 130, DR),
            ("B13b", "Did the corporation have an excess business loss as defined in section 461(l)?", B, "", False, 140, DR),
            ("B14", "At end of tax year, did the corporation have an interest in or signature authority over a foreign bank account?", B, "", False, 150, DR),
            ("B15", "During the tax year, did the corporation receive, sell, exchange, or dispose of any digital assets?", B, "", False, 160, DR),
            ("B16", "During the tax year, did the corporation make any payments that would require it to file Form(s) 1099?", B, "", False, 170, DR),
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
            ("K1", "Ordinary business income (loss)", C, "1120S_K1", False, 10, CR),
            ("K2", "Net rental real estate income (loss)", C, "1120S_K2", False, 20, CR),
            ("K3", "Other net rental income (loss)", C, "1120S_K3", False, 30, CR),
            ("K4", "Interest income", C, "1120S_K4", False, 40, CR),
            ("K5a", "Ordinary dividends", C, "1120S_K5a", False, 50, CR),
            ("K5b", "Qualified dividends", C, "1120S_K5b", False, 60, CR),
            ("K6", "Royalties", C, "1120S_K6", False, 70, CR),
            ("K7", "Net short-term capital gain (loss)", C, "1120S_K7", False, 80, CR),
            ("K8a", "Net long-term capital gain (loss)", C, "1120S_K8a", False, 90, CR),
            ("K9", "Net section 1231 gain (loss)", C, "1120S_K9", False, 100, CR),
            ("K10", "Other income (loss)", C, "1120S_K10", False, 110, CR),
            ("K11", "Section 179 deduction", C, "1120S_K11", False, 120, DR),
            ("K12a", "Charitable contributions", C, "1120S_K12a", False, 130, DR),
            ("K13a", "Low-income housing credit (section 42(j)(5))", C, "1120S_K13a", False, 140, DR),
            ("K14a", "Name of country or U.S. possession", T, "1120S_K14a", False, 150, DR),
            ("K15a", "Post-1986 depreciation adjustment", C, "1120S_K15a", False, 160, DR),
            ("K16a", "Tax-exempt interest income", C, "1120S_K16a", False, 170, CR),
            ("K16b", "Other tax-exempt income", C, "1120S_K16b", False, 180, CR),
            ("K16c", "Nondeductible expenses", C, "1120S_K16c", False, 190, DR),
            ("K16d", "Distributions", C, "1120S_K16d", False, 200, DR),
            ("K17a", "Investment income", C, "1120S_K17a", False, 210, CR),
            ("K17b", "Investment expenses", C, "1120S_K17b", False, 220, DR),
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
            ("L2d", "Trade notes & A/R — end", C, "1120S_L2d_eoy", False, 40, DR),
            ("L5a", "Loans to shareholders — beginning", C, "1120S_L5a_boy", False, 50, DR),
            ("L5d", "Loans to shareholders — end", C, "1120S_L5d_eoy", False, 60, DR),
            ("L7a", "Other current assets — beginning", C, "1120S_L7a_boy", False, 70, DR),
            ("L7d", "Other current assets — end", C, "1120S_L7d_eoy", False, 80, DR),
            ("L9a", "Buildings & other depreciable assets — beginning", C, "1120S_L9a_boy", False, 90, DR),
            ("L9b", "Less accumulated depreciation — beginning", C, "1120S_L9b_boy", False, 100, CR),
            ("L9d", "Buildings & other depreciable assets — end", C, "1120S_L9d_eoy", False, 110, DR),
            ("L9e", "Less accumulated depreciation — end", C, "1120S_L9e_eoy", False, 120, CR),
            ("L14a", "Total assets — beginning", C, "", True, 130, DR),
            ("L14d", "Total assets — end", C, "", True, 140, DR),
            # Liabilities (credit-normal)
            ("L15a", "Accounts payable — beginning", C, "1120S_L15a_boy", False, 150, CR),
            ("L15d", "Accounts payable — end", C, "1120S_L15d_eoy", False, 160, CR),
            ("L17a", "Other current liabilities — beginning", C, "1120S_L17a_boy", False, 170, CR),
            ("L17d", "Other current liabilities — end", C, "1120S_L17d_eoy", False, 180, CR),
            ("L18a", "Loans from shareholders — beginning", C, "1120S_L18a_boy", False, 190, CR),
            ("L18d", "Loans from shareholders — end", C, "1120S_L18d_eoy", False, 200, CR),
            ("L20a", "Other liabilities — beginning", C, "1120S_L20a_boy", False, 210, CR),
            ("L20d", "Other liabilities — end", C, "1120S_L20d_eoy", False, 220, CR),
            # Equity (credit-normal)
            ("L21a", "Capital stock — beginning", C, "1120S_L21a_boy", False, 230, CR),
            ("L21d", "Capital stock — end", C, "1120S_L21d_eoy", False, 240, CR),
            ("L23a", "Retained earnings — beginning", C, "1120S_L23a_boy", False, 250, CR),
            ("L23d", "Retained earnings — end", C, "1120S_L23d_eoy", False, 260, CR),
            ("L24a", "AAA — beginning", C, "1120S_L24a_boy", False, 270, CR),
            ("L24d", "AAA — end", C, "1120S_L24d_eoy", False, 280, CR),
            ("L25a", "Shareholders' undistributed taxable income — beginning", C, "1120S_L25a_boy", False, 290, CR),
            ("L25d", "Shareholders' undistributed taxable income — end", C, "1120S_L25d_eoy", False, 300, CR),
            ("L27a", "Total liabilities and equity — beginning", C, "", True, 310, CR),
            ("L27d", "Total liabilities and equity — end", C, "", True, 320, CR),
        ],
    ),
    # ------ SCHEDULE M-1 ------
    (
        "sched_m1",
        "Schedule M-1 — Reconciliation of Income (Loss)",
        60,
        [
            ("M1_1", "Net income (loss) per books", C, "1120S_M1_1", False, 10, DR),
            ("M1_2", "Income on Schedule K not on books", C, "1120S_M1_2", False, 20, DR),
            ("M1_3a", "Guaranteed payments", C, "1120S_M1_3a", False, 30, DR),
            ("M1_3b", "Expenses on books not on Schedule K (travel & entertainment)", C, "1120S_M1_3b", False, 40, DR),
            ("M1_4", "Add lines 1 through 3b", C, "", True, 50, DR),
            ("M1_5", "Income on books not on Schedule K", C, "1120S_M1_5", False, 60, DR),
            ("M1_6", "Deductions on Schedule K not charged against books", C, "1120S_M1_6", False, 70, DR),
            ("M1_7", "Add lines 5 and 6", C, "", True, 80, DR),
            ("M1_8", "Income (loss) (Schedule K, line 18) (line 4 minus line 7)", C, "", True, 90, DR),
        ],
    ),
    # ------ SCHEDULE M-2 ------
    (
        "sched_m2",
        "Schedule M-2 — Analysis of AAA, OAA, and STPI",
        70,
        [
            ("M2_1", "Balance at beginning of tax year", C, "1120S_M2_1", False, 10, CR),
            ("M2_2", "Ordinary income from page 1, line 21", C, "", True, 20, DR),
            ("M2_3", "Other additions", C, "1120S_M2_3", False, 30, CR),
            ("M2_4", "Loss from page 1, line 21", C, "", True, 40, DR),
            ("M2_5", "Other reductions", C, "1120S_M2_5", False, 50, DR),
            ("M2_6", "Combine lines 1 through 5", C, "", True, 60, DR),
            ("M2_7", "Distributions other than dividend distributions", C, "1120S_M2_7", False, 70, DR),
            ("M2_8", "Balance at end of tax year (line 6 minus line 7)", C, "", True, 80, DR),
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed the Form 1120-S definition with sections and lines."

    def handle(self, *args, **options):
        form, created = FormDefinition.objects.update_or_create(
            code="1120-S",
            defaults={
                "name": "U.S. Income Tax Return for an S Corporation",
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
