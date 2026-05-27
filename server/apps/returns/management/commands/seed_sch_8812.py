"""
Seed Schedule 8812 (Form 1040) definition.

Run: poetry run python manage.py seed_sch_8812 [--year 2025]

Source: SCH_8812_TY2025 Rule Studio spec (Session 14, 2026-05-26).
All 32 lines from the spec's line_map are materialized as FormLine rows.
Input lines are `is_computed=False` (preparer enters); everything else
(calculated, subtotal, total) is `is_computed=True` and written by
`apps.returns.compute_8812`.
"""

from django.core.management.base import BaseCommand

from apps.returns.models import (
    FieldType,
    FormDefinition,
    FormLine,
    FormSection,
    NormalBalance,
)

C = FieldType.CURRENCY
I = FieldType.INTEGER

DR = NormalBalance.DEBIT
CR = NormalBalance.CREDIT

# Format: (line_number, label, field_type, is_computed, sort, normal_balance)
#
# Section breakdown matches the IRS Schedule 8812 form layout:
#   Part I (Lines 1-14)  — Combined CTC + ODC nonrefundable computation
#   Part II-A (Lines 16a-20) — ACTC standard 15%-method path
#   Part II-B (Lines 21-27)  — ACTC alternate "3+ QC" payroll-tax path
SECTIONS = [
    (
        "part_i_credit",
        "Part I — Combined Credit Computation",
        10,
        [
            ("L_1", "Form 1040 Line 11 AGI", C, False, 10, CR),
            ("L_2a", "Puerto Rico excluded income", C, False, 20, CR),
            ("L_2b", "Form 2555 lines 45 + 50 (combined)", C, False, 30, CR),
            ("L_2c", "Form 4563 line 15 — American Samoa", C, False, 40, CR),
            ("L_2d", "Sum of 2a + 2b + 2c", C, True, 50, CR),
            ("L_3", "MAGI = Line 1 + Line 2d", C, True, 60, CR),
            ("L_4", "Number of qualifying children under 17 with valid SSN", I, True, 70, CR),
            ("L_5", "Line 4 × $2,200", C, True, 80, CR),
            ("L_6", "Number of other dependents", I, True, 90, CR),
            ("L_7", "Line 6 × $500", C, True, 100, CR),
            ("L_8", "Combined pre-phaseout credit (Line 5 + Line 7)", C, True, 110, CR),
            ("L_9", "Phaseout threshold ($400K MFJ / $200K other)", C, True, 120, DR),
            ("L_10", "Excess of MAGI over threshold (rounded UP to $1,000)", C, True, 130, DR),
            ("L_11", "Phaseout reduction = Line 10 × 5%", C, True, 140, DR),
            ("L_12", "Net credit post-phaseout (Line 8 − Line 11)", C, True, 150, CR),
            ("L_13", "Tax liability cap (Credit Limit Worksheet A)", C, True, 160, DR),
            ("L_14", "CTC + ODC nonrefundable (min of Line 12, Line 13) → 1040 L_19", C, True, 170, CR),
            ("L_15", "Reserved for future use", C, True, 180, CR),
        ],
    ),
    (
        "part_ii_a_actc",
        "Part II-A — Additional Child Tax Credit (15% method)",
        20,
        [
            ("L_16a", "ACTC overflow (Line 12 − Line 14)", C, True, 10, CR),
            ("L_16b", "ACTC per-child cap (count of QC × $1,700)", C, True, 20, CR),
            ("L_17", "Smaller of Line 16a or Line 16b", C, True, 30, CR),
            ("L_18a", "Earned income (per Earned Income Worksheet)", C, False, 40, CR),
            ("L_18b", "Nontaxable combat pay election", C, False, 50, CR),
            ("L_19", "Earned income excess (Line 18a − $2,500, floored at 0)", C, True, 60, CR),
            ("L_20", "15% earned-income method (Line 19 × 0.15)", C, True, 70, CR),
        ],
    ),
    (
        "part_ii_b_alt",
        "Part II-B — Alternate Path (3+ qualifying children)",
        30,
        [
            ("L_21", "SS + Medicare + Add'l Medicare taxes (W-2 box 4+6, both spouses MFJ)", C, False, 10, CR),
            ("L_22", "Sch 1 line 15 + Sch 2 lines 5, 6, 13", C, True, 20, CR),
            ("L_23", "Line 21 + Line 22", C, True, 30, CR),
            ("L_24", "Form 1040 Line 27a (EITC) + Sch 3 Line 11 (excess SS/RRTA)", C, True, 40, DR),
            ("L_25", "Line 23 − Line 24, floored at 0", C, True, 50, CR),
            ("L_26", "Larger of Line 20 or Line 25", C, True, 60, CR),
            ("L_27", "Additional Child Tax Credit (final) → 1040 L_28", C, True, 70, CR),
        ],
    ),
]

DEFAULT_YEAR = 2025


class Command(BaseCommand):
    help = "Seed Schedule 8812 form definition for a given tax year."

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
            code="SCH_8812",
            tax_year_applicable=year,
            defaults={
                "name": "Schedule 8812 — Credits for Qualifying Children and Other Dependents",
                "description": (
                    "Schedule 8812 (Form 1040) for TY 2025. Implements "
                    "OBBBA §70104: $2,200 per QC with valid SSN, $500 ODC, "
                    "§24(h) phaseout thresholds, ACTC via 15% method + 3+ QC "
                    "alternate path."
                ),
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
                is_computed,
                sort_order,
                normal_balance,
            ) in lines:
                FormLine.objects.update_or_create(
                    section=section,
                    line_number=line_number,
                    defaults={
                        "label": label,
                        "field_type": field_type,
                        "mapping_key": "",
                        "is_computed": is_computed,
                        "sort_order": sort_order,
                        "normal_balance": normal_balance,
                    },
                )
                line_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded Schedule 8812 ({year}): {line_count} lines "
                f"across {len(SECTIONS)} sections."
            )
        )
