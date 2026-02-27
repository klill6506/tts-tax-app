"""
Bulk-import individual clients from a CSV or Excel file.

Creates a Client record and an Entity record (entity_type=individual)
for each row.  Skips rows where a client with the same name already
exists in the firm.

Supports two name formats:
  - Single "Name" column (e.g. "Smith, John")
  - Split columns: "TP Last Name" + "TP First Name" (Lacerte-style)

Spouse columns (optional): SP First Name, SP Last Name, SP SSN

Usage:
    poetry run python manage.py import_clients path/to/clients.xlsx
    poetry run python manage.py import_clients clients.csv --dry-run
    poetry run python manage.py import_clients clients.csv --firm <uuid>
"""

import csv
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.clients.models import Client, ClientStatus, Entity, EntityType
from apps.firms.models import Firm

# The Tax Shelter — Ken's firm
DEFAULT_FIRM_ID = "dfe4540f-5ead-4030-9a3f-e5994837ae67"

# ---------------------------------------------------------------------------
# Column detection — matches common header variations
# ---------------------------------------------------------------------------

COLUMN_PATTERNS = {
    # Single combined name
    "name": [
        "name", "client name", "client_name", "full name", "full_name",
        "taxpayer", "taxpayer name", "taxpayer_name",
    ],
    # Split taxpayer name (Lacerte-style)
    "tp_last_name": ["tp last name", "tp last", "last name", "last"],
    "tp_first_name": ["tp first name", "tp first", "first name", "first"],
    # Taxpayer SSN
    "ssn": [
        "ssn", "tp ssn", "social", "social security", "social_security",
        "tin", "tax id", "tax_id", "ein", "id number",
    ],
    # Spouse
    "sp_first_name": ["sp first name", "sp first", "spouse first name"],
    "sp_last_name": ["sp last name", "sp last", "spouse last name"],
    "sp_ssn": ["sp ssn", "spouse ssn", "spouse social"],
    # Address
    "address": [
        "address", "address1", "address_line1", "address line 1",
        "street", "street address",
    ],
    "city": ["city", "town"],
    "state": ["state", "st"],
    "zip": ["zip", "zip code", "zip_code", "zipcode", "postal", "postal code"],
    # Contact
    "phone": ["phone", "phone number", "telephone", "tel"],
    "email": ["email", "e-mail", "email address"],
}


def _normalize(header):
    """Lowercase, strip whitespace and common punctuation."""
    return header.strip().lower().replace("#", "").replace(".", "").strip()


def _detect_columns(headers):
    """
    Map our field names to column indices based on fuzzy header matching.
    Returns dict like {"tp_last_name": 0, "tp_first_name": 1, ...}.
    """
    mapping = {}
    normalized = [_normalize(h) for h in headers]

    for field, patterns in COLUMN_PATTERNS.items():
        for i, col in enumerate(normalized):
            if col in patterns:
                mapping[field] = i
                break

    return mapping


def _build_name(row, col_map):
    """
    Build a 'Last, First' name from the row.
    Handles both single 'name' column and split TP first/last columns.
    Returns the assembled name or empty string.
    """
    def _get(field):
        idx = col_map.get(field)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    # Prefer split first/last (Lacerte-style)
    last = _get("tp_last_name")
    first = _get("tp_first_name")
    if last:
        if first:
            return f"{last}, {first}"
        return last

    # Fall back to single name column
    return _get("name")


# ---------------------------------------------------------------------------
# File parsers
# ---------------------------------------------------------------------------

def _parse_csv(filepath):
    """Parse a CSV file, return (headers, rows)."""
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = None
        for row in reader:
            if not headers:
                headers = row
                continue
            # Skip blank rows
            if not any(cell.strip() for cell in row):
                continue
            rows.append(row)
    if not headers:
        raise CommandError("CSV file appears to be empty.")
    return headers, rows


def _parse_xlsx(filepath):
    """Parse an Excel file, return (headers, rows)."""
    try:
        import openpyxl
    except ImportError:
        raise CommandError("openpyxl is required for .xlsx files: pip install openpyxl")

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active
    all_rows = []
    for row in ws.iter_rows(values_only=True):
        all_rows.append([str(cell) if cell is not None else "" for cell in row])
    wb.close()

    if len(all_rows) < 2:
        raise CommandError("Excel file needs at least a header row and one data row.")

    headers = all_rows[0]
    data_rows = [r for r in all_rows[1:] if any(cell.strip() for cell in r)]
    return headers, data_rows


def _parse_txt(filepath):
    """Parse a tab-delimited text file, return (headers, rows)."""
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter="\t")
        headers = None
        for row in reader:
            if not headers:
                headers = row
                continue
            if not any(cell.strip() for cell in row):
                continue
            rows.append(row)
    if not headers:
        raise CommandError("TXT file appears to be empty.")
    return headers, rows


def parse_file(filepath):
    """Route to the right parser based on file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        return _parse_csv(filepath)
    elif ext in (".xlsx", ".xls"):
        return _parse_xlsx(filepath)
    elif ext == ".txt":
        return _parse_txt(filepath)
    else:
        raise CommandError(f"Unsupported file type: {ext}  (use .csv, .xlsx, or .txt)")


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Import individual clients from a CSV, Excel, or TXT file."

    def add_arguments(self, parser):
        parser.add_argument(
            "filepath",
            type=str,
            help="Path to the CSV, XLSX, or TXT file.",
        )
        parser.add_argument(
            "--firm",
            type=str,
            default=DEFAULT_FIRM_ID,
            help=f"Firm UUID (default: {DEFAULT_FIRM_ID}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and show what would be imported, without writing to DB.",
        )

    def handle(self, *args, **options):
        filepath = options["filepath"]
        firm_id = options["firm"]
        dry_run = options["dry_run"]

        # Validate file exists
        if not os.path.isfile(filepath):
            raise CommandError(f"File not found: {filepath}")

        # Validate firm exists
        try:
            firm = Firm.objects.get(id=firm_id)
        except Firm.DoesNotExist:
            raise CommandError(f"Firm not found: {firm_id}")

        self.stdout.write(f"Importing clients for firm: {firm.name}")
        self.stdout.write(f"File: {filepath}")

        # Parse the file
        headers, rows = parse_file(filepath)
        col_map = _detect_columns(headers)

        # Check we found at least a name column (single or split)
        has_name = "name" in col_map or "tp_last_name" in col_map
        if not has_name:
            self.stdout.write(self.style.WARNING(
                f"\nDetected columns: {headers}"
            ))
            raise CommandError(
                "Could not detect a name column. Expected one of:\n"
                "  - 'Name', 'Client Name', 'Full Name'  (single column)\n"
                "  - 'TP Last Name' + 'TP First Name'    (split columns)\n"
                "  - 'Last Name' + 'First Name'          (split columns)"
            )

        # Detect name mode
        name_mode = "split" if "tp_last_name" in col_map else "single"

        # Show what we detected
        self.stdout.write(f"\nName mode: {name_mode}")
        self.stdout.write(f"Detected columns:")
        for field, idx in sorted(col_map.items(), key=lambda x: x[1]):
            self.stdout.write(f"  {field:>15} -> column {idx} ({headers[idx]})")

        self.stdout.write(f"\nTotal data rows: {len(rows)}")

        # Get existing client names for duplicate detection
        existing_names = set(
            Client.objects.filter(firm=firm)
            .values_list("name", flat=True)
        )

        created = 0
        skipped = 0
        errors = []

        def _get(row, field):
            """Safely get a field value from a row."""
            idx = col_map.get(field)
            if idx is None or idx >= len(row):
                return ""
            return row[idx].strip()

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n--- DRY RUN (no changes will be made) ---\n"
            ))

        # Process rows
        with transaction.atomic():
            for i, row in enumerate(rows, start=1):
                name = _build_name(row, col_map)
                if not name:
                    errors.append(f"Row {i}: empty name, skipped")
                    continue

                if name in existing_names:
                    skipped += 1
                    if dry_run:
                        self.stdout.write(f"  SKIP (exists): {name}")
                    continue

                ssn = _get(row, "ssn")
                address = _get(row, "address")
                city = _get(row, "city")
                state = _get(row, "state")
                zip_code = _get(row, "zip")
                phone = _get(row, "phone")
                email = _get(row, "email")
                sp_first = _get(row, "sp_first_name")
                sp_last = _get(row, "sp_last_name")
                sp_ssn = _get(row, "sp_ssn")

                if dry_run:
                    spouse_str = ""
                    if sp_last or sp_first:
                        spouse_str = f"  Spouse={sp_last}, {sp_first}"
                    self.stdout.write(
                        f"  CREATE: {name}"
                        f"  SSN={ssn or '---'}"
                        f"  {address}, {city}, {state} {zip_code}"
                        f"{spouse_str}"
                    )
                    existing_names.add(name)
                else:
                    client = Client.objects.create(
                        firm=firm,
                        name=name,
                        status=ClientStatus.ACTIVE,
                    )
                    Entity.objects.create(
                        client=client,
                        name=name,
                        entity_type=EntityType.INDIVIDUAL,
                        legal_name=name,
                        ein=ssn,
                        address_line1=address,
                        city=city,
                        state=state,
                        zip_code=zip_code,
                        phone=phone,
                        email=email,
                        spouse_first_name=sp_first,
                        spouse_last_name=sp_last,
                        spouse_ssn=sp_ssn,
                    )
                    existing_names.add(name)

                created += 1

            # If dry run, roll back the transaction
            if dry_run:
                transaction.set_rollback(True)

        # Summary
        self.stdout.write("")
        action = "Would create" if dry_run else "Created"
        self.stdout.write(self.style.SUCCESS(f"  {action}: {created} clients"))
        if skipped:
            self.stdout.write(self.style.WARNING(
                f"  Skipped (already exist): {skipped}"
            ))
        if errors:
            self.stdout.write(self.style.ERROR(f"  Errors: {len(errors)}"))
            for err in errors:
                self.stdout.write(f"    {err}")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\nRun again without --dry-run to actually import."
            ))
