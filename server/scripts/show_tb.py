"""Show all TB rows for inspection."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.imports.models import TrialBalanceRow

rows = TrialBalanceRow.objects.all().order_by("row_number")
for r in rows:
    print(
        f"{r.row_number:3d} | {r.account_number:10s} | {r.account_name:40s} | "
        f"Dr {r.debit:>12} | Cr {r.credit:>12}"
    )
