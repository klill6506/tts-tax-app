"""Re-parent business entities from S-Corp Client records to shareholder Clients.

After re-parenting, S-Corp Client records with no remaining entities are deleted.

Usage:
    python manage.py reparent_business_entities --dry-run   # preview
    python manage.py reparent_business_entities             # execute
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.clients.models import (
    Client,
    ClientEntityLink,
    Entity,
    EntityType,
    LinkRole,
)


# Entity types that are "business" entities (not individuals)
BUSINESS_TYPES = [EntityType.SCORP, EntityType.PARTNERSHIP, EntityType.CCORP]

# Map entity type -> link role used to find the primary owner
TYPE_ROLE_MAP = {
    EntityType.SCORP: LinkRole.SHAREHOLDER,
    EntityType.PARTNERSHIP: LinkRole.PARTNER,
    EntityType.CCORP: LinkRole.OFFICER,
}


class Command(BaseCommand):
    help = "Re-parent business entities to their primary shareholder/partner client."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without making changes.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print detailed output for each entity.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN — no changes ===\n"))

        # Find all business entities whose parent Client has NO individual entity
        # (i.e. the Client is purely a business placeholder)
        business_entities = Entity.objects.filter(
            entity_type__in=BUSINESS_TYPES,
        ).select_related("client")

        reparented = 0
        skipped_no_links = 0
        skipped_conflict = 0
        clients_to_delete = set()

        for entity in business_entities:
            old_client = entity.client

            # Check if this Client also owns an individual entity
            # (meaning it's a real person, not a business placeholder)
            has_individual = Entity.objects.filter(
                client=old_client, entity_type=EntityType.INDIVIDUAL,
            ).exists()
            if has_individual:
                if verbose:
                    self.stdout.write(
                        f"  SKIP {entity.name} — parent client "
                        f"'{old_client.name}' has individual entity"
                    )
                continue

            # Find the primary shareholder/partner/officer link
            role = TYPE_ROLE_MAP.get(entity.entity_type, LinkRole.SHAREHOLDER)
            links = ClientEntityLink.objects.filter(
                entity=entity,
                role=role,
            ).select_related("client").order_by(
                "-is_primary",                  # primary first
                "-ownership_percentage",        # highest ownership
                "client__name",                 # alphabetical tiebreak
            )

            # Also check for any link role if the specific role has none
            if not links.exists():
                links = ClientEntityLink.objects.filter(
                    entity=entity,
                ).exclude(
                    role=LinkRole.TAXPAYER,
                ).select_related("client").order_by(
                    "-is_primary",
                    "-ownership_percentage",
                    "client__name",
                )

            if not links.exists():
                skipped_no_links += 1
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  SKIP {entity.name} — no shareholder/partner links"
                        )
                    )
                continue

            new_client = links.first().client

            # Check for UniqueConstraint conflict
            conflict = Entity.objects.filter(
                client=new_client,
                name=entity.name,
                entity_type=entity.entity_type,
            ).exclude(id=entity.id).exists()

            if conflict:
                skipped_conflict += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"  CONFLICT {entity.name} — '{new_client.name}' already "
                        f"has entity with same name+type"
                    )
                )
                continue

            if verbose:
                self.stdout.write(
                    f"  RE-PARENT {entity.name}: "
                    f"'{old_client.name}' -> '{new_client.name}'"
                )

            if not dry_run:
                entity.client = new_client
                entity.save(update_fields=["client", "updated_at"])

            reparented += 1
            clients_to_delete.add(old_client.id)

        # Delete orphaned business Client records
        # (only those with no remaining entities pointing at them)
        deleted_count = 0
        for client_id in clients_to_delete:
            remaining = Entity.objects.filter(client_id=client_id).count()
            if remaining == 0:
                if verbose:
                    client = Client.objects.get(id=client_id)
                    self.stdout.write(
                        self.style.NOTICE(
                            f"  DELETE client '{client.name}' (no remaining entities)"
                        )
                    )
                if not dry_run:
                    Client.objects.filter(id=client_id).delete()
                deleted_count += 1

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Re-parented: {reparented}"))
        self.stdout.write(f"Skipped (no links): {skipped_no_links}")
        self.stdout.write(f"Skipped (conflict): {skipped_conflict}")
        self.stdout.write(
            self.style.SUCCESS(f"Clients deleted: {deleted_count}")
        )
        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nDry run complete — no changes made.")
            )
