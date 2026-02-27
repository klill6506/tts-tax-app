"""
Import S-Corp entities and shareholder links from Lacerte CSV exports.

Phase 1: Creates Client + Entity(scorp) records from the S-Corp client list.
Phase 2: Links shareholders to their S-Corp entities via ClientEntityLink.
         Attempts to match shareholders to existing individual clients
         imported by import_clients.  Creates new individual Client + Entity
         records for shareholders not yet in the system.

Usage:
    poetry run python manage.py import_scorps \
        --corps scorps.csv --shareholders shareholders.csv
    poetry run python manage.py import_scorps \
        --corps scorps.csv --shareholders shareholders.csv --dry-run
"""

import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.clients.models import (
    Client,
    ClientEntityLink,
    ClientStatus,
    Entity,
    EntityType,
    LinkRole,
)
from apps.firms.models import Firm

DEFAULT_FIRM_ID = "dfe4540f-5ead-4030-9a3f-e5994837ae67"

NAME_SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_city_state_zip(raw):
    """Parse 'CANTON, GA 30114' into (city, state, zip)."""
    if not raw or not raw.strip():
        return "", "", ""
    raw = raw.strip().strip('"')
    match = re.match(
        r"^(.+?),\s*([A-Z]{2})\s+(\d{5}(?:-\d{0,4})?)$", raw, re.IGNORECASE
    )
    if match:
        return (
            match.group(1).strip(),
            match.group(2).upper(),
            match.group(3).rstrip("-"),
        )
    # State + no zip
    match = re.match(r"^(.+?),\s*([A-Z]{2})\s*$", raw, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).upper(), ""
    return raw, "", ""


def extract_embedded_address(address):
    """
    Handle addresses where city/state/zip is embedded in the address field.
    E.g. '1592 MARS HILL RD STE A WATKINSVILLE, GA 30677'
    Returns (street, city, state, zip).
    """
    # Find ", ST ZIP" at end of address
    match = re.search(
        r",\s*([A-Z]{2})\s+(\d{5}(?:-?\d{0,4})?)$",
        address,
        re.IGNORECASE,
    )
    if match:
        before_comma = address[: match.start()].strip()
        state = match.group(1).upper()
        zip_code = match.group(2).rstrip("-")
        # Last word before the comma is the city name
        parts = before_comma.rsplit(None, 1)
        if len(parts) >= 2:
            street = parts[0]
            city = parts[1]
        else:
            city = before_comma
            street = ""
        return street, city, state, zip_code
    return address, "", "", ""


def to_last_first(name):
    """Convert 'TROY SLATE' to 'SLATE, TROY'."""
    if not name or not name.strip():
        return name or ""
    name = name.strip()
    # Already in "LAST, FIRST" format
    if "," in name:
        return name.upper()
    parts = name.split()
    if len(parts) < 2:
        return name.upper()
    # Detect suffix at end (JR, III, etc.)
    suffix = ""
    if len(parts) > 2 and parts[-1].upper().rstrip(".") in NAME_SUFFIXES:
        suffix = " " + parts.pop().upper().rstrip(".")
    last = parts[-1].upper()
    first = " ".join(parts[:-1]).upper()
    return f"{last}{suffix}, {first}"


def normalize_for_match(name):
    """
    Normalize a name for fuzzy matching.
    Returns (last_name, first_names) tuple, uppercase, suffixes stripped.
    """
    name = name.upper().strip()
    # Strip suffixes
    for sfx in sorted(NAME_SUFFIXES, key=len, reverse=True):
        name = re.sub(r"\b" + sfx + r"\.?\s*", "", name).strip()
    name = re.sub(r"\s+", " ", name).strip()

    if "," in name:
        parts = name.split(",", 1)
        last = parts[0].strip()
        first = parts[1].strip()
    else:
        parts = name.split()
        if len(parts) < 2:
            return (name, "")
        last = parts[-1]
        first = " ".join(parts[:-1])
    return (last, first)


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Import S-Corp entities and shareholder links from Lacerte CSVs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--corps", required=True, help="Path to S-Corp client list CSV"
        )
        parser.add_argument(
            "--shareholders", required=True, help="Path to shareholders CSV"
        )
        parser.add_argument(
            "--firm",
            default=DEFAULT_FIRM_ID,
            help=f"Firm UUID (default: {DEFAULT_FIRM_ID})",
        )
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--include-zz",
            action="store_true",
            help="Include zz-prefixed (inactive) entries",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        include_zz = options["include_zz"]

        try:
            firm = Firm.objects.get(pk=options["firm"])
        except Firm.DoesNotExist:
            raise CommandError(f"Firm {options['firm']} not found.")

        corps_path = Path(options["corps"])
        shareholders_path = Path(options["shareholders"])

        if not corps_path.exists():
            raise CommandError(f"File not found: {corps_path}")
        if not shareholders_path.exists():
            raise CommandError(f"File not found: {shareholders_path}")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "--- DRY RUN (no changes will be made) ---\n"
            ))

        # Phase 1: Import S-Corp entities
        scorp_lookup = self._import_corps(corps_path, firm, dry_run, include_zz)

        # Phase 2: Link shareholders
        self._link_shareholders(shareholders_path, firm, scorp_lookup, dry_run)

    # ------------------------------------------------------------------
    # Phase 1: S-Corp entities
    # ------------------------------------------------------------------

    def _import_corps(self, path, firm, dry_run, include_zz):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "Phase 1: Importing S-Corp entities"
        ))

        scorp_lookup = {}  # client_no -> Entity (or corp_name in dry run)
        created = 0
        skipped_zz = 0
        skipped_dup = 0

        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                corp_name = row["corp_name"].strip()
                client_no = row["client_no"].strip()

                if not corp_name:
                    continue

                if not include_zz and corp_name.lower().startswith("zz"):
                    skipped_zz += 1
                    continue

                # Parse address
                address = row.get("corp_address", "").strip()
                city, state, zip_code = parse_city_state_zip(
                    row.get("corp_city_state_zip", "")
                )

                # If city/state is empty, try extracting from address field
                if not city and not state and address:
                    address, city, state, zip_code = extract_embedded_address(
                        address
                    )

                if dry_run:
                    scorp_lookup[client_no] = corp_name
                    created += 1
                    continue

                # Create Client
                client, cl_created = Client.objects.get_or_create(
                    firm=firm,
                    name=corp_name,
                    defaults={"status": ClientStatus.ACTIVE},
                )

                # Create Entity
                entity, _ = Entity.objects.get_or_create(
                    client=client,
                    name=corp_name,
                    entity_type=EntityType.SCORP,
                    defaults={
                        "legal_name": corp_name,
                        "address_line1": address,
                        "city": city,
                        "state": state,
                        "zip_code": zip_code,
                    },
                )

                scorp_lookup[client_no] = entity
                if cl_created:
                    created += 1
                else:
                    skipped_dup += 1

        action = "Would create" if dry_run else "Created"
        self.stdout.write(self.style.SUCCESS(
            f"  {action}: {created} S-Corp clients + entities"
        ))
        if skipped_zz:
            self.stdout.write(self.style.WARNING(
                f"  Skipped (zz-prefix): {skipped_zz}"
            ))
        if skipped_dup:
            self.stdout.write(self.style.WARNING(
                f"  Skipped (already exist): {skipped_dup}"
            ))
        return scorp_lookup

    # ------------------------------------------------------------------
    # Phase 2: Shareholder links
    # ------------------------------------------------------------------

    def _link_shareholders(self, path, firm, scorp_lookup, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\nPhase 2: Linking shareholders"
        ))

        # Build lookup of existing clients for name matching
        exact_lookup = {}  # name.upper() -> Client
        fuzzy_lookup = {}  # (last, first) tuple -> Client

        for c in Client.objects.filter(firm=firm):
            exact_lookup[c.name.upper()] = c
            key = normalize_for_match(c.name)
            # Only store first match per key to avoid accidental overwrites
            if key not in fuzzy_lookup:
                fuzzy_lookup[key] = c

        links_created = 0
        links_skipped_dup = 0
        links_skipped_no_corp = 0
        individuals_created = 0
        matched_existing = 0
        first_shareholder = set()  # Track first shareholder per S-Corp

        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                client_no = row["client_no"].strip()
                shareholder_name = row["shareholder_name"].strip()

                if not shareholder_name:
                    continue

                # Skip shareholders for S-Corps we didn't import
                if client_no not in scorp_lookup:
                    links_skipped_no_corp += 1
                    continue

                scorp_ref = scorp_lookup[client_no]
                formatted_name = to_last_first(shareholder_name)
                match_key = normalize_for_match(shareholder_name)

                is_primary = client_no not in first_shareholder
                first_shareholder.add(client_no)

                # Parse shareholder address
                sh_address = row.get("shareholder_address", "").strip()
                sh_city, sh_state, sh_zip = parse_city_state_zip(
                    row.get("shareholder_city_state_zip", "")
                )
                if not sh_city and not sh_state and sh_address:
                    sh_address, sh_city, sh_state, sh_zip = (
                        extract_embedded_address(sh_address)
                    )
                sh_phone = row.get("phone", "").strip()
                sh_email = row.get("email", "").strip()

                # --- DRY RUN ---
                if dry_run:
                    existing = (
                        exact_lookup.get(formatted_name.upper())
                        or fuzzy_lookup.get(match_key)
                    )
                    corp_name = scorp_ref  # string in dry run mode
                    if existing:
                        ex_name = (
                            existing.name
                            if hasattr(existing, "name")
                            else existing
                        )
                        self.stdout.write(
                            f"  MATCH: {shareholder_name} "
                            f"-> existing '{ex_name}' "
                            f"-> {corp_name}"
                        )
                        matched_existing += 1
                    else:
                        self.stdout.write(
                            f"  NEW:   {shareholder_name} "
                            f"-> '{formatted_name}' "
                            f"-> {corp_name}"
                        )
                        individuals_created += 1
                        # Add to lookups so subsequent rows can match
                        exact_lookup[formatted_name.upper()] = formatted_name
                        fuzzy_lookup[match_key] = formatted_name
                    links_created += 1
                    continue

                # --- REAL RUN ---

                # Find existing client (exact first, then fuzzy)
                individual_client = exact_lookup.get(formatted_name.upper())
                if not individual_client or not isinstance(
                    individual_client, Client
                ):
                    individual_client = fuzzy_lookup.get(match_key)

                if individual_client and isinstance(individual_client, Client):
                    matched_existing += 1
                else:
                    # Create new individual Client + Entity
                    individual_client = Client.objects.create(
                        firm=firm, name=formatted_name
                    )
                    ind_entity = Entity.objects.create(
                        client=individual_client,
                        name=formatted_name,
                        entity_type=EntityType.INDIVIDUAL,
                        legal_name=formatted_name,
                        address_line1=sh_address,
                        city=sh_city,
                        state=sh_state,
                        zip_code=sh_zip,
                        phone=sh_phone,
                        email=sh_email,
                    )
                    # Auto-create taxpayer self-link
                    ClientEntityLink.objects.create(
                        client=individual_client,
                        entity=ind_entity,
                        role=LinkRole.TAXPAYER,
                        is_primary=True,
                    )
                    individuals_created += 1
                    # Add to lookups for subsequent matching
                    exact_lookup[formatted_name.upper()] = individual_client
                    fuzzy_lookup[match_key] = individual_client

                # Create shareholder link
                link, created = ClientEntityLink.objects.get_or_create(
                    client=individual_client,
                    entity=scorp_ref,
                    role=LinkRole.SHAREHOLDER,
                    defaults={"is_primary": is_primary},
                )
                if created:
                    links_created += 1
                else:
                    links_skipped_dup += 1

        action = "Would create" if dry_run else "Created"
        self.stdout.write(self.style.SUCCESS(
            f"\n  {action}: {links_created} shareholder links"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  Matched to existing individuals: {matched_existing}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  New individuals created: {individuals_created}"
        ))
        if links_skipped_dup:
            self.stdout.write(self.style.WARNING(
                f"  Skipped (duplicate links): {links_skipped_dup}"
            ))
        if links_skipped_no_corp:
            self.stdout.write(self.style.WARNING(
                f"  Skipped (S-Corp not imported): {links_skipped_no_corp}"
            ))
