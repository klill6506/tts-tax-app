"""
Import taxpayer demographics from a Lacerte "Client List" custom-report PDF.

Scope: names, SSNs, DOBs, addresses, spouse info. Filing status is inferred
(spouse present -> MFJ, else single). No dependents, no income — those come
from separate importers.

This command writes to a shared production DB; by design:
  * dry-run is the default (use --commit to actually write)
  * sanitization is the default (use --no-sanitize to import real PII)

Creates the full chain per record: Client -> Entity(individual) ->
TaxYear -> TaxReturn(1040) -> Taxpayer (+ ClientEntityLink, role=taxpayer).

Upserts by TP SSN. Fallback lookup by Client.name or Entity.ein
(covers clients imported via the CSV importer, which stuffs SSN into ein).
Existing ClientEntityLinks to S-Corps/partnerships are left untouched.

Usage:
    # Dry run, sanitized (safe default — nothing written)
    poetry run python manage.py import_lacerte_clients \\
        --pdf-file "D:/tax-test-data/lacerte_pdfs/2025 Custom Reports.pdf"

    # Actually write sanitized fake data to the DB
    poetry run python manage.py import_lacerte_clients \\
        --pdf-file "..." --commit

    # Import the real PII (requires both flags; 5-sec warning on stderr)
    poetry run python manage.py import_lacerte_clients \\
        --pdf-file "..." --no-sanitize --commit
"""

from __future__ import annotations

import sys
import time
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.clients.models import (
    Client,
    ClientEntityLink,
    ClientStatus,
    Entity,
    EntityType,
    LinkRole,
    TaxYear,
)
from apps.firms.models import Firm
from apps.imports.lacerte_clientlist_parser import (
    LacerteDemographic,
    parse_lacerte_clientlist,
)
from apps.imports.lacerte_sanitizer import sanitize_all
from apps.returns.models import FormDefinition, Taxpayer, TaxReturn

DEFAULT_FIRM_ID = "dfe4540f-5ead-4030-9a3f-e5994837ae67"  # The Tax Shelter
FORM_1040_CODE = "1040"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redact(ssn: str) -> str:
    if not ssn:
        return "---"
    return f"***-**-{ssn[-4:]}"


def _client_name_from_record(rec: LacerteDemographic) -> str:
    """'LAST, First [M]' — matches the CSV importer's naming style."""
    parts = [rec.tp_first_name]
    if rec.tp_middle_initial:
        parts.append(rec.tp_middle_initial)
    first_block = " ".join(p for p in parts if p)
    if rec.tp_last_name and first_block:
        return f"{rec.tp_last_name}, {first_block}".strip()
    return rec.tp_last_name or first_block or rec.full_name_lnf


def _find_existing(rec: LacerteDemographic, firm: Firm) -> tuple[Client | None, Entity | None, str]:
    """
    Locate an existing Client and (optional) individual Entity for this record.

    Returns (client, individual_entity_or_None, match_method_str).

    Lookup order:
      1. Taxpayer.ssn == TP SSN
      2. Entity.ein == TP SSN (CSV importer stashed SSN in ein)
      3. Client.name exact match on LAST, First[, M]
    """
    if rec.tp_ssn:
        tp = (
            Taxpayer.objects.filter(ssn=rec.tp_ssn)
            .select_related("tax_return__tax_year__entity__client")
            .first()
        )
        if tp is not None:
            ent = tp.tax_return.tax_year.entity
            if ent.client.firm_id == firm.id:
                return (ent.client, ent, "Taxpayer.ssn")

        ent = (
            Entity.objects.filter(
                client__firm=firm,
                entity_type=EntityType.INDIVIDUAL,
                ein=rec.tp_ssn,
            )
            .select_related("client")
            .first()
        )
        if ent is not None:
            return (ent.client, ent, "Entity.ein")

    built_name = _client_name_from_record(rec)
    if built_name:
        client = Client.objects.filter(firm=firm, name=built_name).first()
        if client is not None:
            ent = (
                Entity.objects.filter(
                    client=client, entity_type=EntityType.INDIVIDUAL
                ).first()
            )
            return (client, ent, "Client.name")

    return (None, None, "none")


def _dob_changed(old: date | None, new: date | None) -> bool:
    return (old or None) != (new or None)


def _write_record(
    rec: LacerteDemographic,
    firm: Firm,
    tax_year: int,
    form_1040: FormDefinition,
) -> tuple[str, list[str]]:
    """
    Upsert one record into the DB. Returns (action, changes).

    action is one of: 'created', 'updated', 'nochange'.
    changes is a human-readable list of field deltas for updated rows.
    """
    client_name = _client_name_from_record(rec)
    existing_client, existing_entity, match_method = _find_existing(rec, firm)

    if existing_client is None:
        client = Client.objects.create(
            firm=firm, name=client_name, status=ClientStatus.ACTIVE,
        )
    else:
        client = existing_client

    if existing_entity is None:
        entity = Entity.objects.create(
            client=client,
            name=client_name,
            entity_type=EntityType.INDIVIDUAL,
            legal_name=rec.full_name_lnf,
            ein=rec.tp_ssn,
            address_line1=rec.street,
            city=rec.city,
            state=rec.state,
            zip_code=rec.zip_code,
            email=rec.tp_email,
            spouse_first_name=rec.sp_first_name,
            spouse_last_name=rec.sp_last_name,
            spouse_ssn=rec.sp_ssn,
        )
        entity_created = True
    else:
        entity = existing_entity
        entity_created = False

    # Ensure a taxpayer-role link between client and the individual entity.
    ClientEntityLink.objects.get_or_create(
        client=client,
        entity=entity,
        role=LinkRole.TAXPAYER,
        defaults={"is_primary": True},
    )

    # Ensure TaxYear + TaxReturn for the requested year.
    ty, _ = TaxYear.objects.get_or_create(entity=entity, year=tax_year)
    tax_return = (
        TaxReturn.objects.filter(tax_year=ty, form_definition=form_1040).first()
    )
    if tax_return is None:
        tax_return = TaxReturn.objects.create(
            tax_year=ty,
            form_definition=form_1040,
            tax_year_start=date(tax_year, 1, 1),
            tax_year_end=date(tax_year, 12, 31),
        )

    # Upsert the Taxpayer row.
    taxpayer, tp_created = Taxpayer.objects.get_or_create(tax_return=tax_return)

    changes: list[str] = []
    new_values = {
        "filing_status": rec.filing_status,
        "first_name": rec.tp_first_name,
        "middle_initial": rec.tp_middle_initial,
        "last_name": rec.tp_last_name,
        "ssn": rec.tp_ssn,
        "spouse_first_name": rec.sp_first_name,
        "spouse_middle_initial": rec.sp_middle_initial,
        "spouse_last_name": rec.sp_last_name,
        "spouse_ssn": rec.sp_ssn,
        "address_line1": rec.street,
        "city": rec.city,
        "state": rec.state,
        "zip_code": rec.zip_code,
        "date_of_birth": rec.tp_dob,
        "spouse_date_of_birth": rec.sp_dob,
    }
    for field_name, new_val in new_values.items():
        old_val = getattr(taxpayer, field_name)
        if field_name in ("date_of_birth", "spouse_date_of_birth"):
            if _dob_changed(old_val, new_val):
                changes.append(f"{field_name}: {old_val} -> {new_val}")
                setattr(taxpayer, field_name, new_val)
        else:
            # Model default is "", so treat None/"" as equal
            if (old_val or "") != (new_val or ""):
                # Redact SSN values in the change log
                if field_name.endswith("ssn"):
                    changes.append(
                        f"{field_name}: {_redact(old_val)} -> {_redact(new_val)}"
                    )
                else:
                    changes.append(f"{field_name}: {old_val!r} -> {new_val!r}")
                setattr(taxpayer, field_name, new_val)

    # Also sync name/address changes onto the Entity (entity holds the display
    # copy used by other parts of the app).
    entity_updates = {}
    if entity.legal_name != rec.full_name_lnf:
        entity_updates["legal_name"] = rec.full_name_lnf
    if rec.tp_ssn and entity.ein != rec.tp_ssn:
        entity_updates["ein"] = rec.tp_ssn
    if rec.street and entity.address_line1 != rec.street:
        entity_updates["address_line1"] = rec.street
    if rec.city and entity.city != rec.city:
        entity_updates["city"] = rec.city
    if rec.state and entity.state != rec.state:
        entity_updates["state"] = rec.state
    if rec.zip_code and entity.zip_code != rec.zip_code:
        entity_updates["zip_code"] = rec.zip_code
    if entity_updates:
        for k, v in entity_updates.items():
            setattr(entity, k, v)
        entity.save(update_fields=list(entity_updates.keys()))
        for k, v in entity_updates.items():
            changes.append(f"entity.{k} updated")

    if changes or tp_created:
        taxpayer.save()

    if existing_client is None:
        action = "created"
    elif tp_created or entity_created or changes:
        action = "updated"
    else:
        action = "nochange"

    if match_method != "none" and action != "created":
        changes.insert(0, f"matched via {match_method}")

    return action, changes


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Import taxpayer demographics from a Lacerte Client List PDF. "
        "Dry-run + sanitized by default — see --commit and --no-sanitize."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--pdf-file",
            type=str,
            required=True,
            help="Absolute path to the Lacerte client list PDF.",
        )
        parser.add_argument(
            "--tax-year",
            type=int,
            default=2025,
            help="Tax year for the TaxYear/TaxReturn to create. Default: 2025.",
        )
        parser.add_argument(
            "--firm",
            type=str,
            default=DEFAULT_FIRM_ID,
            help="Firm UUID (default: The Tax Shelter).",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Actually write to the DB. Without this, runs in dry-run.",
        )
        parser.add_argument(
            "--no-sanitize",
            action="store_true",
            help=(
                "Do NOT sanitize PII before writing. Requires deliberate use; "
                "triggers a 5-second stderr warning unless combined with --commit."
            ),
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Process only the first N records (0 = all).",
        )

    def handle(self, *args, **options):
        pdf_file = options["pdf_file"]
        tax_year = options["tax_year"]
        firm_id = options["firm"]
        commit = options["commit"]
        no_sanitize = options["no_sanitize"]
        limit = options["limit"]

        from pathlib import Path
        pdf_path = Path(pdf_file)
        if not pdf_path.is_file():
            raise CommandError(f"PDF not found: {pdf_file}")

        try:
            firm = Firm.objects.get(id=firm_id)
        except Firm.DoesNotExist:
            raise CommandError(f"Firm not found: {firm_id}")

        form_1040 = (
            FormDefinition.objects.filter(code=FORM_1040_CODE)
            .order_by("-tax_year_applicable")
            .first()
        )
        if form_1040 is None:
            raise CommandError(
                f"No FormDefinition found for code={FORM_1040_CODE!r}. "
                "Run `manage.py seed_1040` first."
            )

        if no_sanitize and not commit:
            self.stderr.write(
                "WARNING: --no-sanitize will preview REAL PII in the dry-run "
                "output and, if --commit is added, write raw PII to the shared "
                "prod DB. Ctrl+C to abort."
            )
            time.sleep(5)

        mode_lines = [
            f"PDF: {pdf_path}",
            f"Firm: {firm.name} ({firm.id})",
            f"Tax year: {tax_year}",
            f"Form: {form_1040.code} ({form_1040.tax_year_applicable})",
            f"Sanitize: {'NO (raw PII)' if no_sanitize else 'YES (synthetic)'}",
            f"Mode: {'COMMIT' if commit else 'DRY-RUN (no writes)'}",
        ]
        for line in mode_lines:
            self.stdout.write(line)
        self.stdout.write("")

        self.stdout.write("Parsing PDF...")
        records = parse_lacerte_clientlist(pdf_path)
        self.stdout.write(f"Parsed {len(records)} records.")

        if limit and limit > 0:
            records = records[:limit]
            self.stdout.write(f"Limit: processing first {limit}.")

        if not no_sanitize:
            records = sanitize_all(records)

        stats = {"created": 0, "updated": 0, "nochange": 0, "errors": 0}

        with transaction.atomic():
            for i, rec in enumerate(records, start=1):
                try:
                    action, changes = _write_record(
                        rec, firm, tax_year, form_1040
                    )
                except Exception as exc:  # noqa: BLE001
                    stats["errors"] += 1
                    self.stdout.write(self.style.ERROR(
                        f"[ERR {i:3d}] {rec.full_name_lnf}: {exc}"
                    ))
                    continue
                stats[action] += 1

                tag = {
                    "created": self.style.SUCCESS("[NEW]    "),
                    "updated": self.style.WARNING("[UPDATE] "),
                    "nochange": "[SAME]   ",
                }[action]
                line = (
                    f"{tag}{rec.full_name_lnf[:40]:40}  "
                    f"{rec.filing_status:6} "
                    f"TP={_redact(rec.tp_ssn)} DOB={rec.tp_dob or '---'}  "
                    f"{rec.street}, {rec.city}, {rec.state} {rec.zip_code}"
                )
                self.stdout.write(line)
                for ch in changes:
                    self.stdout.write(f"         - {ch}")

            if not commit:
                transaction.set_rollback(True)

        # Summary
        self.stdout.write("")
        verb = "Imported" if commit else "Would import"
        self.stdout.write(self.style.SUCCESS(
            f"{verb}: created={stats['created']}, updated={stats['updated']}, "
            f"nochange={stats['nochange']}, errors={stats['errors']}"
        ))
        if not commit:
            self.stdout.write(self.style.WARNING(
                "DRY-RUN — no changes written. Re-run with --commit to apply."
            ))
