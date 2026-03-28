"""
Seed the Georgia Form 600S definition with all sections and lines.

Run: poetry run python manage.py seed_ga600s
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
# GA 600S Line Definitions
# Each section is (code, title, sort_order, lines)
# Each line is (line_number, label, field_type, mapping_key, is_computed, sort, normal_balance)
# ---------------------------------------------------------------------------

C = FieldType.CURRENCY
I = FieldType.INTEGER
T = FieldType.TEXT
B = FieldType.BOOLEAN
P = FieldType.PERCENTAGE

DR = NormalBalance.DEBIT
CR = NormalBalance.CREDIT

SECTIONS = [
    # ------ SCHEDULE 1: GA TAXABLE INCOME & TAX (Page 1) ------
    (
        "sched_1",
        "Schedule 1 — Computation of GA Taxable Income and Tax",
        10,
        [
            ("GA_PTET", "PTET Election (Pass-Through Entity Tax)", B, "", False, 5, DR),
            ("S1_1", "Georgia Net Income (from Schedule 5, Line 7)", C, "GA600S_S1_1", True, 10, CR),
            ("S1_2", "Additional Georgia Taxable Income", C, "GA600S_S1_2", False, 20, CR),
            ("S1_3", "Total Income (Add Lines 1 and 2)", C, "", True, 30, CR),
            ("S1_4", "Georgia Net Operating Loss Deduction (from Schedule 10)", C, "GA600S_S1_4", False, 40, DR),
            ("S1_5", "Passive Loss/Capital Loss Deduction", C, "GA600S_S1_5", False, 50, DR),
            ("S1_6", "Total Georgia Taxable Income (Line 3 less Lines 4 and 5)", C, "", True, 60, CR),
            ("S1_7", "Income Tax (5.39% x Line 6)", C, "", True, 70, DR),
        ],
    ),
    # ------ SCHEDULE 2: GA TAXABLE NET INCOME (PTET ONLY) ------
    (
        "sched_2",
        "Schedule 2 — Computation of Georgia Taxable Net Income (PTET)",
        20,
        [
            ("S2_1", "Georgia Net Income (from Schedule 5, Line 7)", C, "", True, 10, CR),
            ("S2_2", "Georgia Net Operating Loss Deduction", C, "GA600S_S2_2", False, 20, DR),
            ("S2_3", "Georgia Taxable Net Income (Line 1 less Line 2)", C, "", True, 30, CR),
            ("S2_4", "Tax at entity level (5.39% x Line 3)", C, "", True, 40, DR),
        ],
    ),
    # ------ SCHEDULE 3: NET WORTH TAX (Page 2) ------
    (
        "sched_3",
        "Schedule 3 — Computation of Net Worth Tax",
        30,
        [
            ("S3_1", "Total Capital stock issued", C, "GA600S_S3_1", False, 10, CR),
            ("S3_2", "Paid in or Capital surplus", C, "GA600S_S3_2", False, 20, CR),
            ("S3_3", "Total Retained earnings", C, "GA600S_S3_3", False, 30, CR),
            ("S3_4", "Net Worth (Total of Lines 1, 2, and 3)", C, "", True, 40, CR),
            ("S3_5", "Ratio (GA and Dom. 100%; Foreign from Sch 2)", P, "GA600S_S3_5", False, 50, DR),
            ("S3_6", "Net Worth Taxable by Georgia (Line 4 x Line 5)", C, "", True, 60, CR),
            ("S3_7", "Net Worth Tax (from table in instructions)", C, "", True, 70, DR),
        ],
    ),
    # ------ SCHEDULE 4: TAX DUE OR OVERPAYMENT (Page 2) ------
    # Three columns: A=Income Tax, B=Net Worth Tax, C=Total
    (
        "sched_4",
        "Schedule 4 — Computation of Tax Due or Overpayment",
        40,
        [
            ("S4_1a", "Total Tax — Income Tax", C, "", True, 10, DR),
            ("S4_1b", "Total Tax — Net Worth Tax", C, "", True, 11, DR),
            ("S4_1c", "Total Tax — Total", C, "", True, 12, DR),
            ("S4_2a", "Estimated tax payments — Income Tax", C, "GA600S_S4_2a", False, 20, CR),
            ("S4_2b", "Estimated tax payments — Net Worth Tax", C, "GA600S_S4_2b", False, 21, CR),
            ("S4_2c", "Estimated tax payments — Total", C, "", True, 22, CR),
            ("S4_3a", "Credits from Schedule 11 — Income Tax", C, "GA600S_S4_3a", False, 30, CR),
            ("S4_3b", "Credits from Schedule 11 — Net Worth Tax", C, "GA600S_S4_3b", False, 31, CR),
            ("S4_3c", "Credits from Schedule 11 — Total", C, "", True, 32, CR),
            ("S4_4a", "Withholding Credits — Income Tax", C, "GA600S_S4_4a", False, 40, CR),
            ("S4_4b", "Withholding Credits — Net Worth Tax", C, "GA600S_S4_4b", False, 41, CR),
            ("S4_4c", "Withholding Credits — Total", C, "", True, 42, CR),
            ("S4_5c", "Balance of tax due", C, "", True, 52, DR),
            ("S4_6c", "Amount of overpayment", C, "", True, 62, CR),
            ("S4_7a", "Interest due — Income Tax", C, "GA600S_S4_7a", False, 70, DR),
            ("S4_7b", "Interest due — Net Worth Tax", C, "GA600S_S4_7b", False, 71, DR),
            ("S4_7c", "Interest due — Total", C, "", True, 72, DR),
            ("S4_8a", "Form 600 UET penalty — Income Tax", C, "GA600S_S4_8a", False, 80, DR),
            ("S4_8b", "Form 600 UET penalty — Net Worth Tax", C, "GA600S_S4_8b", False, 81, DR),
            ("S4_8c", "Form 600 UET penalty — Total", C, "", True, 82, DR),
            ("S4_9a", "Other penalty due — Income Tax", C, "GA600S_S4_9a", False, 90, DR),
            ("S4_9b", "Other penalty due — Net Worth Tax", C, "GA600S_S4_9b", False, 91, DR),
            ("S4_9c", "Other penalty due — Total", C, "", True, 92, DR),
            ("S4_10c", "Amount Due", C, "", True, 102, DR),
            ("S4_11c", "Credit to next year estimated tax", C, "", True, 112, CR),
        ],
    ),
    # ------ SCHEDULE 5: GA NET INCOME (Page 2) ------
    (
        "sched_5",
        "Schedule 5 — Computation of Georgia Net Income",
        50,
        [
            ("S5_1", "Total Income for Georgia purposes (Schedule 6, Line 11)", C, "", True, 10, CR),
            ("S5_2", "Income allocated everywhere (Attach Schedule)", C, "GA600S_S5_2", False, 20, DR),
            ("S5_3", "Business Income subject to apportionment (Line 1 less Line 2)", C, "", True, 30, CR),
            ("S5_4", "Georgia Ratio (Schedule 9, default 1.000000)", P, "GA600S_S5_4", False, 40, DR),
            ("S5_5", "Net business income apportioned to Georgia (Line 3 x Line 4)", C, "", True, 50, CR),
            ("S5_6", "Net income allocated to Georgia (Attach Schedule)", C, "GA600S_S5_6", False, 60, CR),
            ("S5_7", "Georgia Net Income (Add Line 5 and Line 6)", C, "", True, 70, CR),
        ],
    ),
    # ------ SCHEDULE 6: TOTAL INCOME FOR GA PURPOSES (Page 2) ------
    (
        "sched_6",
        "Schedule 6 — Computation of Total Income for GA Purposes",
        60,
        [
            ("S6_1", "Ordinary income (loss) per Federal return", C, "GA600S_S6_1", False, 10, CR),
            ("S6_2", "Net income (loss) from rental real estate activities", C, "GA600S_S6_2", False, 20, CR),
            ("S6_3a", "Gross income from other rental activities", C, "GA600S_S6_3a", False, 30, CR),
            ("S6_3b", "Less: expenses from other rental activities", C, "GA600S_S6_3b", False, 31, DR),
            ("S6_3c", "Net business income from other rental activities", C, "", True, 32, CR),
            ("S6_4a", "Portfolio income: Interest Income", C, "GA600S_S6_4a", False, 40, CR),
            ("S6_4b", "Portfolio income: Dividend Income", C, "GA600S_S6_4b", False, 41, CR),
            ("S6_4c", "Portfolio income: Royalty Income", C, "GA600S_S6_4c", False, 42, CR),
            ("S6_4d", "Portfolio income: Net short-term capital gain (loss)", C, "GA600S_S6_4d", False, 43, CR),
            ("S6_4e", "Portfolio income: Net long-term capital gain (loss)", C, "GA600S_S6_4e", False, 44, CR),
            ("S6_4f", "Portfolio income: Other portfolio income (loss)", C, "GA600S_S6_4f", False, 45, CR),
            ("S6_5", "Net gain (loss) under section 1231", C, "GA600S_S6_5", False, 50, CR),
            ("S6_6", "Other Income (loss)", C, "GA600S_S6_6", False, 60, CR),
            ("S6_7", "Total Federal Income (Add Lines 1 through 6)", C, "", True, 70, CR),
            ("S6_8", "Additions to Federal Income (Schedule 7)", C, "", True, 80, DR),
            ("S6_9", "Total (Add Line 7 and Line 8)", C, "", True, 90, CR),
            ("S6_10", "Subtractions from Federal Income (Schedule 8)", C, "", True, 100, DR),
            ("S6_11", "Total Income for Georgia purposes (Line 9 less Line 10)", C, "", True, 110, CR),
        ],
    ),
    # ------ SCHEDULE 7: ADDITIONS TO FEDERAL TAXABLE INCOME (Page 3) ------
    (
        "sched_7",
        "Schedule 7 — Additions to Federal Taxable Income",
        70,
        [
            ("S7_1", "State and municipal bond interest (other than Georgia)", C, "GA600S_S7_1", False, 10, DR),
            ("S7_2", "Net income or net profits taxes imposed by other jurisdictions", C, "GA600S_S7_2", False, 20, DR),
            ("S7_3", "Expense attributable to tax exempt income", C, "GA600S_S7_3", False, 30, DR),
            ("S7_4", "Reserved", C, "", False, 40, DR),
            ("S7_5", "Intangible expenses and related interest costs", C, "GA600S_S7_5", False, 50, DR),
            ("S7_6", "Captive REIT expenses and costs", C, "GA600S_S7_6", False, 60, DR),
            ("S7_7", "Other Additions (Attach Schedule)", C, "GA600S_S7_7", False, 70, DR),
            ("S7_8", "TOTAL (Enter on Schedule 6, Line 8)", C, "", True, 80, DR),
        ],
    ),
    # ------ SCHEDULE 8: SUBTRACTIONS FROM FEDERAL TAXABLE INCOME (Page 3) ------
    (
        "sched_8",
        "Schedule 8 — Subtractions from Federal Taxable Income",
        80,
        [
            ("S8_1", "Interest on obligations of United States", C, "GA600S_S8_1", False, 10, CR),
            ("S8_2", "Exception to intangible expenses (Attach IT-Addback)", C, "GA600S_S8_2", False, 20, CR),
            ("S8_3", "Exception to captive REIT expenses (Attach IT-REIT)", C, "GA600S_S8_3", False, 30, CR),
            ("S8_4", "Other Subtractions (Attach Schedule)", C, "GA600S_S8_4", False, 40, CR),
            ("S8_5", "TOTAL (Enter on Schedule 6, Line 10)", C, "", True, 50, CR),
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed the Georgia Form 600S definition with sections and lines."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year", type=int, default=2024,
            help="Tax year to seed (default: 2024)",
        )

    def handle(self, *args, **options):
        year = options["year"]
        form, created = FormDefinition.objects.update_or_create(
            code="GA-600S",
            tax_year_applicable=year,
            defaults={
                "name": "Georgia S Corporation Tax Return",
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
            if stale.exists():
                self.stdout.write(
                    f"  Removing {stale.count()} stale lines from {sec_code}"
                )
                stale.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(SECTIONS)} sections, {line_count} lines for GA-600S."
            )
        )
