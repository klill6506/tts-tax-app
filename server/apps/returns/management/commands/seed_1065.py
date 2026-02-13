"""
Seed the Form 1065 definition with all sections and lines.

Run: poetry run python manage.py seed_1065
"""

from django.core.management.base import BaseCommand

from apps.returns.models import FieldType, FormDefinition, FormLine, FormSection

# ---------------------------------------------------------------------------
# 1065 Line Definitions
# Each section is (code, title, sort_order, lines)
# Each line is (line_number, label, field_type, mapping_key, is_computed, sort)
# ---------------------------------------------------------------------------

C = FieldType.CURRENCY
I = FieldType.INTEGER
T = FieldType.TEXT
B = FieldType.BOOLEAN

SECTIONS = [
    # ------ PAGE 1: INCOME ------
    (
        "page1_income",
        "Page 1 — Income",
        10,
        [
            ("1a", "Gross receipts or sales", C, "1065_L1a", False, 10),
            ("1b", "Returns and allowances", C, "1065_L1b", False, 20),
            ("1c", "Balance (subtract 1b from 1a)", C, "", True, 30),
            ("2", "Cost of goods sold (attach Form 1125-A)", C, "1065_L2", False, 40),
            ("3", "Gross profit (subtract line 2 from line 1c)", C, "", True, 50),
            ("4", "Ordinary income (loss) from other partnerships, estates, and trusts", C, "1065_L4", False, 60),
            ("5", "Net farm profit (loss)", C, "1065_L5", False, 70),
            ("6", "Net gain (loss) from Form 4797, Part II, line 17", C, "1065_L6", False, 80),
            ("7", "Other income (loss)", C, "1065_L7", False, 90),
            ("8", "Total income (loss) (combine lines 3 through 7)", C, "", True, 100),
        ],
    ),
    # ------ PAGE 1: DEDUCTIONS ------
    (
        "page1_deductions",
        "Page 1 — Deductions",
        20,
        [
            ("9", "Salaries and wages (other than to partners)", C, "1065_L9", False, 10),
            ("10", "Guaranteed payments to partners", C, "1065_L10", False, 20),
            ("11", "Repairs and maintenance", C, "1065_L11", False, 30),
            ("12", "Bad debts", C, "1065_L12", False, 40),
            ("13", "Rent", C, "1065_L13", False, 50),
            ("14", "Taxes and licenses", C, "1065_L14", False, 60),
            ("15", "Interest (see instructions)", C, "1065_L15", False, 70),
            ("16", "Depreciation", C, "1065_L16", False, 80),
            ("17", "Depletion", C, "1065_L17", False, 90),
            ("18", "Retirement plans, etc.", C, "1065_L18", False, 100),
            ("19", "Employee benefit programs", C, "1065_L19", False, 110),
            ("20", "Other deductions (attach statement)", C, "1065_L20", False, 120),
            ("21", "Total deductions (add lines 9 through 20)", C, "", True, 130),
            ("22", "Ordinary business income (loss) (subtract line 21 from line 8)", C, "", True, 140),
        ],
    ),
    # ------ SCHEDULE K ------
    (
        "sched_k",
        "Schedule K — Partners' Distributive Share Items",
        30,
        [
            ("K1", "Ordinary business income (loss)", C, "1065_K1", False, 10),
            ("K2", "Net rental real estate income (loss)", C, "1065_K2", False, 20),
            ("K3", "Other net rental income (loss)", C, "1065_K3", False, 30),
            ("K4", "Guaranteed payments", C, "1065_K4", False, 40),
            ("K5", "Interest income", C, "1065_K5", False, 50),
            ("K6a", "Ordinary dividends", C, "1065_K6a", False, 60),
            ("K6b", "Qualified dividends", C, "1065_K6b", False, 70),
            ("K7", "Royalties", C, "1065_K7", False, 80),
            ("K8", "Net short-term capital gain (loss)", C, "1065_K8", False, 90),
            ("K9a", "Net long-term capital gain (loss)", C, "1065_K9a", False, 100),
            ("K10", "Net section 1231 gain (loss)", C, "1065_K10", False, 110),
            ("K11", "Other income (loss)", C, "1065_K11", False, 120),
            ("K12", "Section 179 deduction", C, "1065_K12", False, 130),
            ("K13a", "Charitable contributions", C, "1065_K13a", False, 140),
            ("K13d", "Investment interest expense", C, "1065_K13d", False, 150),
            ("K14a", "Net earnings (loss) from self-employment", C, "1065_K14a", False, 160),
            ("K16a", "Foreign taxes paid or accrued", C, "1065_K16a", False, 170),
            ("K18a", "Tax-exempt interest income", C, "1065_K18a", False, 180),
            ("K19a", "Distributions", C, "1065_K19a", False, 190),
        ],
    ),
    # ------ SCHEDULE L: BALANCE SHEET ------
    (
        "sched_l",
        "Schedule L — Balance Sheet per Books",
        40,
        [
            # Assets — Beginning of Year (col a) and End of Year (col d)
            ("L1a", "Cash — beginning of year", C, "1065_L1a_boy", False, 10),
            ("L1d", "Cash — end of year", C, "1065_L1d_eoy", False, 20),
            ("L2a", "Trade notes & accounts receivable — beginning", C, "1065_L2a_boy", False, 30),
            ("L2d", "Trade notes & accounts receivable — end", C, "1065_L2d_eoy", False, 40),
            ("L3a", "Inventories — beginning", C, "1065_L3a_boy", False, 50),
            ("L3d", "Inventories — end", C, "1065_L3d_eoy", False, 60),
            ("L6a", "Other current assets — beginning", C, "1065_L6a_boy", False, 70),
            ("L6d", "Other current assets — end", C, "1065_L6d_eoy", False, 80),
            ("L7a", "Loans to partners — beginning", C, "1065_L7a_boy", False, 90),
            ("L7d", "Loans to partners — end", C, "1065_L7d_eoy", False, 100),
            ("L9a", "Buildings & other depreciable assets — beginning", C, "1065_L9a_boy", False, 110),
            ("L9b", "Less accumulated depreciation — beginning", C, "1065_L9b_boy", False, 120),
            ("L9d", "Buildings & other depreciable assets — end", C, "1065_L9d_eoy", False, 130),
            ("L9e", "Less accumulated depreciation — end", C, "1065_L9e_eoy", False, 140),
            ("L11a", "Land — beginning", C, "1065_L11a_boy", False, 150),
            ("L11d", "Land — end", C, "1065_L11d_eoy", False, 160),
            ("L13a", "Other assets — beginning", C, "1065_L13a_boy", False, 170),
            ("L13d", "Other assets — end", C, "1065_L13d_eoy", False, 180),
            ("L14a", "Total assets — beginning", C, "", True, 190),
            ("L14d", "Total assets — end", C, "", True, 200),
            # Liabilities
            ("L15a", "Accounts payable — beginning", C, "1065_L15a_boy", False, 210),
            ("L15d", "Accounts payable — end", C, "1065_L15d_eoy", False, 220),
            ("L16a", "Mortgages, notes, bonds payable (less than 1 year) — beginning", C, "1065_L16a_boy", False, 230),
            ("L16d", "Mortgages, notes, bonds payable (less than 1 year) — end", C, "1065_L16d_eoy", False, 240),
            ("L17a", "Other current liabilities — beginning", C, "1065_L17a_boy", False, 250),
            ("L17d", "Other current liabilities — end", C, "1065_L17d_eoy", False, 260),
            ("L19a", "Loans from partners — beginning", C, "1065_L19a_boy", False, 270),
            ("L19d", "Loans from partners — end", C, "1065_L19d_eoy", False, 280),
            ("L21a", "Other liabilities — beginning", C, "1065_L21a_boy", False, 290),
            ("L21d", "Other liabilities — end", C, "1065_L21d_eoy", False, 300),
            # Capital
            ("L22a", "Partners' capital accounts — beginning", C, "1065_L22a_boy", False, 310),
            ("L22d", "Partners' capital accounts — end", C, "1065_L22d_eoy", False, 320),
            ("L23a", "Total liabilities and capital — beginning", C, "", True, 330),
            ("L23d", "Total liabilities and capital — end", C, "", True, 340),
        ],
    ),
    # ------ SCHEDULE M-1 ------
    (
        "sched_m1",
        "Schedule M-1 — Reconciliation of Income (Loss) per Books with Income (Loss) per Return",
        50,
        [
            ("M1_1", "Net income (loss) per books", C, "1065_M1_1", False, 10),
            ("M1_2", "Income included on Schedule K not recorded on books", C, "1065_M1_2", False, 20),
            ("M1_3", "Guaranteed payments", C, "1065_M1_3", False, 30),
            ("M1_4", "Expenses recorded on books not included on Schedule K", C, "1065_M1_4", False, 40),
            ("M1_5", "Add lines 1 through 4", C, "", True, 50),
            ("M1_6", "Income recorded on books not included on Schedule K", C, "1065_M1_6", False, 60),
            ("M1_7", "Deductions included on Schedule K not charged against books", C, "1065_M1_7", False, 70),
            ("M1_8", "Add lines 6 and 7", C, "", True, 80),
            ("M1_9", "Income (loss) (line 5 minus line 8)", C, "", True, 90),
        ],
    ),
    # ------ SCHEDULE M-2 ------
    (
        "sched_m2",
        "Schedule M-2 — Analysis of Partners' Capital Accounts",
        60,
        [
            ("M2_1", "Balance at beginning of tax year", C, "1065_M2_1", False, 10),
            ("M2_2a", "Capital contributed during year (cash)", C, "1065_M2_2a", False, 20),
            ("M2_2b", "Capital contributed during year (property)", C, "1065_M2_2b", False, 30),
            ("M2_3", "Net income (loss) per books", C, "1065_M2_3", False, 40),
            ("M2_4", "Other increases", C, "1065_M2_4", False, 50),
            ("M2_5", "Add lines 1 through 4", C, "", True, 60),
            ("M2_6a", "Distributions (cash)", C, "1065_M2_6a", False, 70),
            ("M2_6b", "Distributions (property)", C, "1065_M2_6b", False, 80),
            ("M2_7", "Other decreases", C, "1065_M2_7", False, 90),
            ("M2_8", "Add lines 6a through 7", C, "", True, 100),
            ("M2_9", "Balance at end of tax year (line 5 minus line 8)", C, "", True, 110),
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed the Form 1065 definition with sections and lines."

    def handle(self, *args, **options):
        form, created = FormDefinition.objects.update_or_create(
            code="1065",
            defaults={
                "name": "U.S. Return of Partnership Income",
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

            for line_num, label, ftype, mkey, computed, sort in lines:
                FormLine.objects.update_or_create(
                    section=section,
                    line_number=line_num,
                    defaults={
                        "label": label,
                        "field_type": ftype,
                        "mapping_key": mkey,
                        "is_computed": computed,
                        "sort_order": sort,
                    },
                )
                line_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(SECTIONS)} sections, {line_count} lines for {form.code}."
            )
        )
