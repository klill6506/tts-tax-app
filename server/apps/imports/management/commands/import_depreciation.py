"""
Management command: Import depreciation assets from Lacerte TXT file.

Usage:
    poetry run python manage.py import_depreciation --file path/to/file.txt --return-id <uuid>
    poetry run python manage.py import_depreciation --file path/to/file.txt --return-id <uuid> --dry-run
"""

import datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.imports.importers.lacerte_depr_parser import parse_lacerte_txt


class Command(BaseCommand):
    help = "Import depreciation assets from a tax software TXT export"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", required=True, type=str,
            help="Path to the depreciation TXT file",
        )
        parser.add_argument(
            "--return-id", required=True, type=str,
            help="UUID of the TaxReturn to import into",
        )
        parser.add_argument(
            "--dry-run", action="store_true", default=False,
            help="Parse and preview without creating records",
        )
        parser.add_argument(
            "--format", default="lacerte", choices=["lacerte"],
            help="Parser format (default: lacerte)",
        )

    def handle(self, *args, **options):
        from apps.returns.models import DepreciationAsset, TaxReturn
        from apps.tts_forms.depreciation_engine import suggest_bonus_pct

        file_path = Path(options["file"])
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        return_id = options["return_id"]
        dry_run = options["dry_run"]

        try:
            tax_return = TaxReturn.objects.select_related(
                "tax_year__entity__client"
            ).get(id=return_id)
        except TaxReturn.DoesNotExist:
            raise CommandError(f"TaxReturn not found: {return_id}")

        entity = tax_return.tax_year.entity
        self.stdout.write(
            f"Target: {entity.legal_name or entity.name} "
            f"({tax_return.tax_year.year} {tax_return.form_definition.code})"
        )

        content = file_path.read_text(encoding="utf-8", errors="replace")

        if options["format"] == "lacerte":
            parsed = parse_lacerte_txt(content)
        else:
            raise CommandError(f"Unsupported format: {options['format']}")

        if not parsed:
            self.stdout.write(self.style.WARNING("No assets found in file."))
            return

        # Display preview table
        self.stdout.write(f"\n{'#':>3}  {'Description':<25}  {'Acquired':>10}  "
                          f"{'Cost':>10}  {'Method':>8}  {'Life':>4}  "
                          f"{'Prior':>10}  {'Current':>8}  {'Group':<20}")
        self.stdout.write("-" * 120)

        for a in parsed:
            method_str = f"{a['method']} {a['convention']}" if a['method'] else ""
            self.stdout.write(
                f"{a['asset_number']:>3}  {a['description']:<25}  "
                f"{a['date_acquired'] or '':>10}  "
                f"{a['cost_basis']:>10,}  {method_str:>8}  "
                f"{a['life']:>4}  {a['prior_depreciation']:>10,}  "
                f"{a['current_depreciation']:>8,}  {a['asset_group']:<20}"
            )

        self.stdout.write(f"\nTotal: {len(parsed)} assets")

        if a.get("business_pct", 100) < 100:
            self.stdout.write(self.style.WARNING(
                f"  Note: Asset {a['asset_number']} has "
                f"{a['business_pct']}% business use"
            ))

        if dry_run:
            self.stdout.write(self.style.SUCCESS("\n[DRY RUN] No records created."))
            return

        # Create records
        from apps.returns.views import _auto_calculate_asset
        from apps.returns.compute import aggregate_depreciation

        max_num = (
            DepreciationAsset.objects.filter(tax_return=tax_return)
            .order_by("-asset_number")
            .values_list("asset_number", flat=True)
            .first()
        ) or 0

        created = 0
        for i, a in enumerate(parsed, start=1):
            acq = (
                datetime.date.fromisoformat(a["date_acquired"])
                if a["date_acquired"] else None
            )
            sold = (
                datetime.date.fromisoformat(a["date_sold"])
                if a.get("date_sold") else None
            )

            bonus_pct = Decimal("0")
            if acq:
                bonus_pct = suggest_bonus_pct(
                    acq,
                    group_label=a["asset_group"],
                    is_amortization=False,
                )

            asset = DepreciationAsset.objects.create(
                tax_return=tax_return,
                asset_number=max_num + i,
                description=a["description"],
                group_label=a["asset_group"],
                date_acquired=acq,
                date_sold=sold,
                cost_basis=Decimal(str(a["cost_basis"])),
                business_pct=Decimal(str(a["business_pct"])),
                sec_179_elected=Decimal(str(a["section_179"])),
                prior_depreciation=Decimal(str(a["prior_depreciation"])),
                method=a["method"],
                convention=a["convention"],
                life=Decimal(str(a["life"])) if a["life"] else None,
                bonus_pct=bonus_pct,
                imported_from_lacerte=True,
                lacerte_asset_no=a["asset_number"],
            )
            _auto_calculate_asset(asset, tax_return)
            created += 1

        aggregate_depreciation(tax_return)
        self.stdout.write(self.style.SUCCESS(
            f"\nSuccessfully imported {created} assets."
        ))
