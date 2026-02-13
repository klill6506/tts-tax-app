"""Show all TB rows for inspection."""

from django.core.management.base import BaseCommand

from apps.imports.models import TrialBalanceRow


class Command(BaseCommand):
    help = "Display all trial balance rows."

    def handle(self, *args, **options):
        rows = TrialBalanceRow.objects.all().order_by("row_number")
        for r in rows:
            self.stdout.write(
                f"{r.row_number:3d} | {r.account_number:10s} | "
                f"{r.account_name:40s} | Dr {r.debit:>12} | Cr {r.credit:>12}"
            )
