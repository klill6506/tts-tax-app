"""One-off script to import Ken's real TB file."""

import os
import sys
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.clients.models import TaxYear
from apps.imports.models import TrialBalanceRow, TrialBalanceUpload, UploadStatus
from apps.imports.parsers import parse_csv

# Get the TaxYear
ty = TaxYear.objects.select_related("entity__client").first()
print(f"TaxYear: {ty.entity.client.name} > {ty.entity.name} | {ty.year}")

# Read the file
csv_path = Path(r"D:\Archive\Microsoft 2025 Trial Balance.csv")
content = csv_path.read_bytes()
uploaded_file = SimpleUploadedFile(
    "Microsoft 2025 Trial Balance.csv", content, content_type="text/csv"
)

# Parse it
rows = parse_csv(uploaded_file)
print(f"Parsed {len(rows)} rows:")
for r in rows[:5]:
    print(f"  {r['account_name']:40s}  DR={r['debit']:>12}  CR={r['credit']:>12}")
print(f"  ... ({len(rows)} total)")

# Create the upload record
upload = TrialBalanceUpload.objects.create(
    tax_year=ty,
    original_filename="Microsoft 2025 Trial Balance.csv",
    file=SimpleUploadedFile(
        "Microsoft 2025 Trial Balance.csv", content, content_type="text/csv"
    ),
    status=UploadStatus.PARSED,
    row_count=len(rows),
)

# Bulk-create the rows
row_objects = [
    TrialBalanceRow(
        upload=upload,
        row_number=idx + 1,
        account_number=row["account_number"],
        account_name=row["account_name"],
        debit=row["debit"],
        credit=row["credit"],
        raw_data=row["raw_data"],
    )
    for idx, row in enumerate(rows)
]
TrialBalanceRow.objects.bulk_create(row_objects)

print(f"\nUpload ID: {upload.id}")
print(f"Status:    {upload.status}")
print(f"Rows:      {upload.row_count}")

# Quick balance check
total_dr = sum(r["debit"] for r in rows)
total_cr = sum(r["credit"] for r in rows)
print(f"\nTotal Debits:  {total_dr:>14}")
print(f"Total Credits: {total_cr:>14}")
diff = total_dr - total_cr
if diff == 0:
    print("TB is BALANCED!")
else:
    print(f"OUT OF BALANCE by {diff}")
