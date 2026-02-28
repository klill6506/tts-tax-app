"""
Batch-create tax returns for entities that have prior year data.

Creates a TaxYear + TaxReturn + pre-populated FormFieldValues for each
entity that has a PriorYearReturn but no return for the target year.

Usage:
    poetry run python manage.py create_returns_batch --year 2025
    poetry run python manage.py create_returns_batch --year 2025 --dry-run
"""

import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from apps.clients.models import TaxYear
from apps.returns.models import (
    FormDefinition,
    FormFieldValue,
    FormLine,
    PriorYearReturn,
    TaxReturn,
)

ENTITY_FORM_MAP = {
    "scorp": "1120-S",
    "partnership": "1065",
    "ccorp": "1120",
}


class Command(BaseCommand):
    help = "Batch-create tax returns for entities with prior year data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            required=True,
            help="Tax year to create returns for (e.g., 2025).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created without saving.",
        )
        parser.add_argument(
            "--user",
            default="Ken2",
            help="Username for created_by (default: Ken2).",
        )

    def handle(self, **options):
        year = options["year"]
        dry_run = options["dry_run"]
        username = options["user"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found.")

        # Cache form definitions
        form_defs = {}
        for code in ENTITY_FORM_MAP.values():
            fd = FormDefinition.objects.filter(code=code).first()
            if fd:
                form_defs[code] = fd

        if not form_defs:
            raise CommandError("No form definitions found. Run seed commands first.")

        # Find entities with prior year data for (year - 1)
        prior_year = year - 1
        prior_returns = (
            PriorYearReturn.objects.filter(year=prior_year)
            .select_related("entity")
        )

        self.stdout.write(
            f"Found {prior_returns.count()} prior year returns for {prior_year}"
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no data will be saved"))
        self.stdout.write("")

        stats = {"created": 0, "skipped_exists": 0, "skipped_no_form": 0}

        for pyr in prior_returns:
            entity = pyr.entity
            form_code = ENTITY_FORM_MAP.get(entity.entity_type)

            if not form_code or form_code not in form_defs:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Skip: {entity.name} — no form for type '{entity.entity_type}'"
                    )
                )
                stats["skipped_no_form"] += 1
                continue

            # Get or create TaxYear
            tax_year, _ = TaxYear.objects.get_or_create(
                entity=entity, year=year,
            )

            # Check if return already exists
            if TaxReturn.objects.filter(tax_year=tax_year).exists():
                self.stdout.write(f"  Exists: {entity.name} ({year})")
                stats["skipped_exists"] += 1
                continue

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f"  Would create: {entity.name} - {form_code}")
                )
                stats["created"] += 1
                continue

            form_def = form_defs[form_code]

            tax_return = TaxReturn.objects.create(
                tax_year=tax_year,
                form_definition=form_def,
                created_by=user,
                tax_year_start=datetime.date(year, 1, 1),
                tax_year_end=datetime.date(year, 12, 31),
            )

            # Pre-populate all form lines with empty values
            lines = FormLine.objects.filter(
                section__form=form_def
            ).select_related("section")
            FormFieldValue.objects.bulk_create([
                FormFieldValue(
                    tax_return=tax_return,
                    form_line=line,
                    value="",
                )
                for line in lines
            ])

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Created: {entity.name} - {form_code} ({len(lines)} fields)"
                )
            )
            stats["created"] += 1

        self.stdout.write("")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Created:          {stats['created']}")
        self.stdout.write(f"Already existed:  {stats['skipped_exists']}")
        self.stdout.write(f"No form mapping:  {stats['skipped_no_form']}")
