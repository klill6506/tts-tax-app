"""
Import prior year return data from Lacerte-printed PDF returns.

Reads a folder of Lacerte PDF files, parses each one to extract form line
values, balance sheet, and other deduction detail, then stores the data
in PriorYearReturn records matched to existing entities by EIN.

Usage:
    poetry run python manage.py import_prior_year \
        --folder "D:\\dev\\tts-tax-app\\Lacerte Export"

    poetry run python manage.py import_prior_year \
        --folder "D:\\dev\\tts-tax-app\\Lacerte Export" --dry-run
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.clients.models import Entity
from apps.imports.lacerte_parser import parse_lacerte_1120s
from apps.returns.models import PriorYearReturn


class Command(BaseCommand):
    help = "Import prior year return data from Lacerte PDF files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--folder",
            required=True,
            help="Path to folder containing Lacerte PDF files.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and report without saving to database.",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=0,
            help="Override tax year (default: auto-detect from PDF).",
        )

    def handle(self, **options):
        folder = Path(options["folder"])
        dry_run = options["dry_run"]
        year_override = options["year"]

        if not folder.is_dir():
            raise CommandError(f"Folder not found: {folder}")

        pdf_files = sorted(folder.glob("*.pdf"))
        if not pdf_files:
            raise CommandError(f"No PDF files found in {folder}")

        self.stdout.write(f"Found {len(pdf_files)} PDF file(s) in {folder}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no data will be saved"))
        self.stdout.write("")

        # Build EIN → Entity and name → Entity lookups
        entities_by_ein = {}
        entities_by_name = {}
        for entity in Entity.objects.all():
            if entity.ein:
                clean_ein = entity.ein.replace("-", "")
                entities_by_ein[clean_ein] = entity
            # Name lookup (case-insensitive, stripped)
            name_key = entity.name.strip().upper()
            entities_by_name[name_key] = entity

        stats = {
            "parsed": 0,
            "matched": 0,
            "matched_by_ein": 0,
            "matched_by_name": 0,
            "eins_backfilled": 0,
            "created": 0,
            "updated": 0,
            "skipped_no_ein": 0,
            "skipped_no_match": 0,
            "errors": 0,
        }
        unmatched = []

        for pdf_file in pdf_files:
            self.stdout.write(f"  Parsing: {pdf_file.name}")

            try:
                result = parse_lacerte_1120s(pdf_file)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"    ERROR: {e}")
                )
                stats["errors"] += 1
                continue

            stats["parsed"] += 1

            if result.warnings:
                for w in result.warnings:
                    self.stdout.write(self.style.WARNING(f"    Warning: {w}"))

            if not result.ein:
                self.stdout.write(self.style.WARNING("    Skipped: no EIN found"))
                stats["skipped_no_ein"] += 1
                continue

            # Match to entity: try EIN first, then name
            clean_ein = result.ein.replace("-", "")
            entity = entities_by_ein.get(clean_ein)
            match_method = "ein"

            if not entity and result.entity_name:
                name_key = result.entity_name.strip().upper()
                entity = entities_by_name.get(name_key)
                if entity:
                    match_method = "name"

            if not entity:
                self.stdout.write(
                    self.style.WARNING(
                        f"    No match: EIN {result.ein} ({result.entity_name})"
                    )
                )
                stats["skipped_no_match"] += 1
                unmatched.append((result.ein, result.entity_name, pdf_file.name))
                continue

            stats["matched"] += 1
            if match_method == "ein":
                stats["matched_by_ein"] += 1
            else:
                stats["matched_by_name"] += 1

            tax_year = year_override or result.tax_year
            form_code = result.form_code or "1120-S"

            line_count = len(result.line_values)
            bs_count = len(result.balance_sheet)
            od_count = len(result.other_deductions)

            match_label = f"by {match_method}" if match_method == "name" else ""
            self.stdout.write(
                self.style.SUCCESS(
                    f"    Matched {match_label}: {entity.name} (EIN {result.ein}) — "
                    f"{line_count} lines, {bs_count} BS items, {od_count} deductions"
                )
            )

            # Backfill EIN on entity if missing
            if not entity.ein and result.ein and not dry_run:
                entity.ein = result.ein
                entity.save(update_fields=["ein"])
                stats["eins_backfilled"] += 1

            if dry_run:
                continue

            # Create or update PriorYearReturn
            pyr, created = PriorYearReturn.objects.update_or_create(
                entity=entity,
                year=tax_year,
                form_code=form_code,
                defaults={
                    "line_values": result.line_values,
                    "other_deductions": result.other_deductions,
                    "balance_sheet": result.balance_sheet,
                    "source_software": "lacerte",
                    "source_file": pdf_file.name,
                },
            )

            if created:
                stats["created"] += 1
            else:
                stats["updated"] += 1

        # Summary
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Parsed:          {stats['parsed']}")
        self.stdout.write(f"Matched:         {stats['matched']}")
        self.stdout.write(f"  by EIN:        {stats['matched_by_ein']}")
        self.stdout.write(f"  by name:       {stats['matched_by_name']}")
        if not dry_run:
            self.stdout.write(f"Created:         {stats['created']}")
            self.stdout.write(f"Updated:         {stats['updated']}")
            self.stdout.write(f"EINs backfilled: {stats['eins_backfilled']}")
        self.stdout.write(f"No EIN in PDF:   {stats['skipped_no_ein']}")
        self.stdout.write(f"No match:        {stats['skipped_no_match']}")
        self.stdout.write(f"Errors:          {stats['errors']}")

        if unmatched:
            self.stdout.write("")
            self.stdout.write("Unmatched EINs:")
            for ein, name, filename in unmatched:
                self.stdout.write(f"  {ein}  {name}  ({filename})")
