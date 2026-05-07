"""
Bulk import employers from a TaxWise CSV export.

Spec
----
Source CSV layout (one header row + N data rows):
    EIN, NAME, ADDRESS, CITY            (4 columns)

Quirks the parser must handle:
  * UTF-8 BOM on the first byte of the file.
  * Headers may have leading/trailing whitespace and inconsistent capitalization;
    they are normalized via str.strip().lower() before lookup.
  * The "CITY" column is actually city + state + zip mashed together in any of:
        ADDISON TX 75001-
        "ADDISON, TX 75001-"
        "AKRON, OH 44316"
        ALBANY GA 31702-1867
    Parsing handled by apps.employers.parsers.parse_city_state_zip.
  * The "ADDRESS" column sometimes contains a line-2 fragment ("SUITE 800",
    apartment numbers, etc.) instead of a real street address. ~5-10% of rows.
    Detection heuristic:
       - street starts with one of: SUITE, STE, UNIT, APT, FLOOR, FL, ROOM, RM, #
       - OR street begins with a number < 100 (likely apartment/unit number)
  * No state-withholding-ID column at all. EmployerStateAccount rows are NOT
    created by this command — they accumulate via the W-2 entry learning loop.
  * Some rows have an empty ADDRESS (and a few have other field gaps); flagged
    via parse_warning, never crash the whole import.

Behavior
--------
  * Default = DRY-RUN (transaction.atomic() with set_rollback(True)). Pass
    --commit to actually persist. Mirrors apps.imports.import_lacerte_clients
    and apps.returns.management.commands.import_partnerships.
  * Upsert by EIN:
      - if no existing row, create with source=<--source>, verified=False
      - if existing row with verified=False, update name/address fields and
        merge parse_warning (preserve any new warnings, don't lose old ones)
      - if existing row with verified=True, SKIP — never overwrite verified data
  * Output is counts-only — never row-level employer names, addresses, or EINs.

Usage
-----
    poetry run python manage.py import_employers \\
        --csv-file "D:/path/to/EIN Database.csv"

    poetry run python manage.py import_employers \\
        --csv-file "..." --commit
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.employers.models import Employer
from apps.employers.parsers import (
    parse_city_state_zip,
    parse_ein,
    validate_zip,
)


# Detect "ADDRESS column contains a line-2 fragment instead of a real street"
_LINE2_KEYWORD_RE = re.compile(
    r"^(SUITE|STE|UNIT|APT|FLOOR|FL|ROOM|RM|#)\b", re.IGNORECASE
)
_LEADING_NUM_RE = re.compile(r"^(\d+)\b")

VALID_SOURCES = {"taxwise_import", "user_entered"}


def detect_address_line2(street: str) -> bool:
    """True if `street` looks like an apartment/suite line, not a real street."""
    if not street:
        return False
    s = street.strip()
    if _LINE2_KEYWORD_RE.match(s):
        return True
    m = _LEADING_NUM_RE.match(s)
    if m and int(m.group(1)) < 100:
        return True
    return False


class Command(BaseCommand):
    help = (
        "Bulk import employers from a TaxWise CSV export. "
        "Dry-run by default — pass --commit to actually write."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            required=True,
            help="Absolute path to the TaxWise employer CSV (UTF-8, may have BOM).",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Actually write to the DB. Without this, runs in dry-run.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Process only the first N data rows (0 = all).",
        )
        parser.add_argument(
            "--source",
            type=str,
            default="taxwise_import",
            choices=sorted(VALID_SOURCES),
            help="Employer.source value to set on newly-created rows.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"])
        commit = options["commit"]
        limit = options["limit"]
        source = options["source"]

        if not csv_path.is_file():
            raise CommandError(f"CSV not found: {csv_path}")

        mode = "COMMIT" if commit else "DRY-RUN (no writes)"
        self.stdout.write(f"CSV:    {csv_path}")
        self.stdout.write(f"Source: {source}")
        self.stdout.write(f"Mode:   {mode}")
        if limit:
            self.stdout.write(f"Limit:  first {limit} rows")
        self.stdout.write("")

        stats = {
            "total": 0,
            "created": 0,
            "updated": 0,
            "skipped_verified": 0,
            "errors": 0,
            "with_warning": 0,
        }
        warning_categories: Counter[str] = Counter()
        error_categories: Counter[str] = Counter()

        with transaction.atomic():
            with open(csv_path, encoding="utf-8-sig", newline="") as fh:
                reader = csv.reader(fh)
                try:
                    raw_headers = next(reader)
                except StopIteration:
                    raise CommandError("CSV is empty.")

                headers = [h.strip().lower() for h in raw_headers]
                required = {"ein", "name", "address", "city"}
                missing = required - set(headers)
                if missing:
                    raise CommandError(
                        f"CSV missing required header columns: {sorted(missing)}. "
                        f"Got: {headers}"
                    )
                idx = {h: headers.index(h) for h in required}

                for row_no, row in enumerate(reader, start=2):  # 2 = first data row
                    if limit and stats["total"] >= limit:
                        break
                    stats["total"] += 1

                    # Defensive: short rows
                    if len(row) < 4:
                        stats["errors"] += 1
                        error_categories["short row"] += 1
                        continue

                    raw_ein = row[idx["ein"]]
                    raw_name = row[idx["name"]]
                    raw_address = row[idx["address"]]
                    raw_csz = row[idx["city"]]

                    canonical_ein = parse_ein(raw_ein)
                    if canonical_ein is None:
                        stats["errors"] += 1
                        error_categories["malformed EIN"] += 1
                        continue

                    name = (raw_name or "").strip()
                    if not name:
                        stats["errors"] += 1
                        error_categories["empty name"] += 1
                        continue

                    street = (raw_address or "").strip()
                    city, state, zip_raw, csz_warnings = parse_city_state_zip(raw_csz)
                    zip_norm, zip_warnings = (
                        validate_zip(zip_raw) if zip_raw else ("", [])
                    )

                    row_warnings: list[str] = []
                    for w in csz_warnings:
                        if w == "empty":
                            row_warnings.append("empty city column")
                            warning_categories["empty city/state/zip column"] += 1
                        elif w == "missing zip":
                            row_warnings.append(w)
                            warning_categories["missing zip"] += 1
                        elif w.startswith("unparseable"):
                            row_warnings.append("unparseable city/state/zip")
                            warning_categories["unparseable city/state/zip"] += 1
                        else:
                            row_warnings.append(w)
                            warning_categories[w] += 1

                    if zip_warnings:
                        row_warnings.append("invalid zip format")
                        warning_categories["invalid zip format"] += 1

                    if not street:
                        row_warnings.append("empty street")
                        warning_categories["empty street"] += 1
                    elif detect_address_line2(street):
                        row_warnings.append("address line 2 detected")
                        warning_categories["address line 2 detected"] += 1

                    if row_warnings:
                        stats["with_warning"] += 1

                    parse_warning_text = "; ".join(row_warnings)

                    # Upsert by EIN
                    existing = Employer.objects.filter(ein=canonical_ein).first()
                    if existing is not None and existing.verified:
                        stats["skipped_verified"] += 1
                        continue

                    if existing is None:
                        Employer.objects.create(
                            ein=canonical_ein,
                            name=name,
                            street=street,
                            city=city,
                            state=state,
                            zip=zip_norm,
                            source=source,
                            verified=False,
                            parse_warning=parse_warning_text,
                        )
                        stats["created"] += 1
                    else:
                        existing.name = name
                        existing.street = street
                        existing.city = city
                        existing.state = state
                        existing.zip = zip_norm
                        # Merge: preserve old warnings, append new ones (deduped)
                        merged = set(filter(None, (existing.parse_warning or "").split("; ")))
                        merged.update(filter(None, parse_warning_text.split("; ")))
                        existing.parse_warning = "; ".join(sorted(merged))
                        existing.save()
                        stats["updated"] += 1

            if not commit:
                transaction.set_rollback(True)

        # ---- summary -------------------------------------------------------
        verb_create = "Created" if commit else "Would create"
        verb_update = "Updated" if commit else "Would update"

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. total={stats['total']}, "
            f"{verb_create.lower()}={stats['created']}, "
            f"{verb_update.lower()}={stats['updated']}, "
            f"skipped_verified={stats['skipped_verified']}, "
            f"errors={stats['errors']}, "
            f"with_warning={stats['with_warning']}"
        ))
        if not commit:
            self.stdout.write(self.style.WARNING(
                "DRY-RUN — no changes written. Re-run with --commit to apply."
            ))

        if error_categories:
            self.stdout.write("")
            self.stdout.write("Error categories:")
            for cat, n in error_categories.most_common():
                self.stdout.write(f"  [{n:5d}] {cat}")

        if warning_categories:
            self.stdout.write("")
            self.stdout.write("Warning categories:")
            for cat, n in warning_categories.most_common():
                self.stdout.write(f"  [{n:5d}] {cat}")
