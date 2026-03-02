"""Backfill filing_states for existing tax years from entity.state.

Tax years created before the filing_states field have an empty list.
This command sets filing_states = [entity.state] for any tax year
where entity.state is set but filing_states is empty.

Usage:
    poetry run python manage.py backfill_filing_states
    poetry run python manage.py backfill_filing_states --dry-run
"""

from django.core.management.base import BaseCommand

from apps.clients.models import TaxYear


class Command(BaseCommand):
    help = "Backfill filing_states from entity.state for existing tax years"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        tax_years = TaxYear.objects.select_related("entity").filter(
            filing_states=[],
            entity__state__isnull=False,
        ).exclude(entity__state="")

        count = 0
        for ty in tax_years:
            state = ty.entity.state.upper()
            if dry_run:
                self.stdout.write(
                    f"  Would set {ty.entity.name} ({ty.year}) -> [{state}]"
                )
            else:
                ty.filing_states = [state]
                ty.save(update_fields=["filing_states"])
            count += 1

        prefix = "Would update" if dry_run else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{prefix} {count} tax year(s)."))
