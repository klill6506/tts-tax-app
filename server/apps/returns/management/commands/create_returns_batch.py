"""
Batch-create tax returns for entities that have prior year data.

Creates a TaxYear + TaxReturn + pre-populated FormFieldValues for each
entity that has a PriorYearReturn but no return for the target year.

Includes all auto-population from prior year:
- Standard deductions (Lacerte-style, ~40 categories)
- Schedule B defaults (all "No")
- Balance Sheet BOY from PY EOY
- M-2 beginning balance from PY ending balance
- Shareholders from PY K-1 data
- Officers from PY 1125-E data
- Return header fields (S election date, shareholder count, etc.)

Usage:
    poetry run python manage.py create_returns_batch --year 2025
    poetry run python manage.py create_returns_batch --year 2025 --dry-run
    poetry run python manage.py create_returns_batch --year 2025 --recreate
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
from apps.returns.views import (
    _populate_boy_from_prior_year,
    _populate_m2_boy_from_prior_year,
    _populate_schedule_b_defaults,
    _populate_shareholders_from_prior_year,
    _populate_officers_from_prior_year,
    _prepopulate_standard_deductions,
)

ENTITY_FORM_MAP = {
    "scorp": "1120-S",
    "partnership": "1065",
    "ccorp": "1120",
    "individual": "1040",
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
            "--recreate",
            action="store_true",
            help="Delete existing returns and recreate them.",
        )
        parser.add_argument(
            "--user",
            default="Ken2",
            help="Username for created_by (default: Ken2).",
        )

    def handle(self, **options):
        year = options.get("year", 2025)
        dry_run = options["dry_run"]
        recreate = options["recreate"]
        username = options["user"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found.")

        # Cache form definitions
        form_defs = {}
        for code in ENTITY_FORM_MAP.values():
            fd = FormDefinition.objects.filter(
                code=code, tax_year_applicable=year,
            ).first() or FormDefinition.objects.filter(code=code).first()
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
        if recreate:
            self.stdout.write(self.style.WARNING("RECREATE — existing returns will be deleted"))
        self.stdout.write("")

        stats = {
            "created": 0, "deleted": 0, "skipped_exists": 0,
            "skipped_no_form": 0, "shareholders": 0, "officers": 0,
        }

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
            existing = TaxReturn.objects.filter(tax_year=tax_year)
            if existing.exists():
                if recreate and not dry_run:
                    existing.delete()
                    stats["deleted"] += 1
                elif not recreate:
                    stats["skipped_exists"] += 1
                    continue

            if dry_run:
                action = "Recreate" if recreate else "Create"
                self.stdout.write(
                    self.style.SUCCESS(f"  Would {action}: {entity.name} - {form_code}")
                )
                stats["created"] += 1
                continue

            form_def = form_defs[form_code]

            # Auto-populate return-level fields from PY
            extra_fields = {}
            if entity.naics_code:
                extra_fields["business_activity_code"] = entity.naics_code
            if entity.business_activity:
                extra_fields["product_or_service"] = entity.business_activity
            if pyr.line_values:
                raw_date = pyr.line_values.get("_s_election_date", "")
                if raw_date:
                    # Convert MM/DD/YYYY → YYYY-MM-DD for Django DateField
                    try:
                        dt = datetime.datetime.strptime(raw_date, "%m/%d/%Y")
                        extra_fields["s_election_date"] = dt.strftime("%Y-%m-%d")
                    except ValueError:
                        extra_fields["s_election_date"] = raw_date
                if pyr.line_values.get("_number_of_shareholders"):
                    extra_fields["number_of_shareholders"] = pyr.line_values["_number_of_shareholders"]

            tax_return = TaxReturn.objects.create(
                tax_year=tax_year,
                form_definition=form_def,
                created_by=user,
                tax_year_start=datetime.date(year, 1, 1),
                tax_year_end=datetime.date(year, 12, 31),
                **extra_fields,
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

            # ── All auto-population steps ──
            _prepopulate_standard_deductions(tax_return)
            _populate_schedule_b_defaults(tax_return)
            _populate_boy_from_prior_year(tax_return)
            _populate_m2_boy_from_prior_year(tax_return)
            sh_count = _populate_shareholders_from_prior_year(tax_return)
            off_count = _populate_officers_from_prior_year(tax_return)

            stats["created"] += 1
            stats["shareholders"] += sh_count
            stats["officers"] += off_count

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Created: {entity.name} - {form_code} "
                    f"({len(lines)} fields, {sh_count} SH, {off_count} OFF)"
                )
            )

        self.stdout.write("")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Created:          {stats['created']}")
        if recreate:
            self.stdout.write(f"Deleted first:    {stats['deleted']}")
        self.stdout.write(f"Already existed:  {stats['skipped_exists']}")
        self.stdout.write(f"No form mapping:  {stats['skipped_no_form']}")
        self.stdout.write(f"Shareholders:     {stats['shareholders']}")
        self.stdout.write(f"Officers:         {stats['officers']}")
