"""
Seed the Form 1040 definition with all sections and lines.

Run: poetry run python manage.py seed_1040
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
# 1040 Line Definitions
# Each section is (code, title, sort_order, lines)
# Each line is (line_number, label, field_type, mapping_key, is_computed, sort, normal_balance)
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
            ("1a", "Wages, salaries, tips (W-2, box 1)", C, "1040_L1a", True, 10, CR),
            ("1z", "Add lines 1a through 1h", C, "", True, 20, CR),
            ("2a", "Tax-exempt interest", C, "1040_L2a", True, 30, CR),
            ("2b", "Taxable interest", C, "1040_L2b", True, 40, CR),
            ("8", "Other income from Schedule 1, line 10", C, "1040_L8", False, 50, CR),
            ("9", "Total income", C, "", True, 60, CR),
        ],
    ),
    # ------ PAGE 1: ADJUSTMENTS & DEDUCTIONS ------
    (
        "page1_deductions",
        "Page 1 — Adjustments & Deductions",
        20,
        [
            ("10", "Adjustments to income from Schedule 1, line 26", C, "1040_L10", False, 10, DR),
            ("11", "Adjusted gross income", C, "", True, 20, DR),
            ("12", "Standard deduction or itemized deductions", C, "", True, 30, DR),
            ("13", "Qualified business income deduction", C, "1040_L13", False, 40, DR),
            ("14", "Total deductions (line 12 + line 13)", C, "", True, 50, DR),
            ("15", "Taxable income", C, "", True, 60, DR),
        ],
    ),
    # ------ PAGE 2: TAX AND CREDITS ------
    (
        "page2_tax",
        "Page 2 — Tax and Credits",
        30,
        [
            ("16", "Tax (from Tax Table or Tax Computation Worksheet)", C, "", True, 10, DR),
            ("24", "Total tax", C, "", True, 20, DR),
        ],
    ),
    # ------ PAGE 2: PAYMENTS ------
    (
        "page2_payments",
        "Page 2 — Payments",
        40,
        [
            ("25a", "Federal income tax withheld from W-2s", C, "1040_L25a", True, 10, CR),
            ("25d", "Total federal tax withheld", C, "", True, 20, CR),
            ("33", "Total payments", C, "", True, 30, CR),
        ],
    ),
    # ------ PAGE 2: REFUND / AMOUNT OWED ------
    (
        "page2_refund",
        "Page 2 — Refund or Amount Owed",
        50,
        [
            ("34", "Overpaid (if line 33 > line 24)", C, "", True, 10, CR),
            ("37", "Amount you owe (if line 24 > line 33)", C, "", True, 20, DR),
        ],
    ),
]

DEFAULT_YEAR = 2025


class Command(BaseCommand):
    help = "Seed Form 1040 definition for a given tax year."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=DEFAULT_YEAR,
            help=f"Tax year to seed (default {DEFAULT_YEAR})",
        )

    def handle(self, *args, **options):
        year = options.get("year", DEFAULT_YEAR)
        form_def, _ = FormDefinition.objects.update_or_create(
            code="1040",
            tax_year_applicable=year,
            defaults={
                "name": "U.S. Individual Income Tax Return",
                "description": "Form 1040 — Individual Income Tax Return",
            },
        )

        line_count = 0
        for section_code, section_title, section_order, lines in SECTIONS:
            section, _ = FormSection.objects.update_or_create(
                form=form_def,
                code=section_code,
                defaults={
                    "title": section_title,
                    "sort_order": section_order,
                },
            )

            for (
                line_number,
                label,
                field_type,
                mapping_key,
                is_computed,
                sort_order,
                normal_balance,
            ) in lines:
                fl, _ = FormLine.objects.update_or_create(
                    section=section,
                    line_number=line_number,
                    defaults={
                        "label": label,
                        "field_type": field_type,
                        "mapping_key": mapping_key,
                        "is_computed": is_computed,
                        "sort_order": sort_order,
                        "normal_balance": normal_balance,
                    },
                )
                line_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded Form 1040 ({year}): {line_count} lines across {len(SECTIONS)} sections."
            )
        )
