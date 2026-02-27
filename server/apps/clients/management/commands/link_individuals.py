"""
Create ClientEntityLink records for all individual entities.

For every Entity with entity_type=individual, creates a link:
    ClientEntityLink(client=entity.client, entity=entity, role=taxpayer, is_primary=True)

This is a one-time seeder for existing data.  Safe to re-run — skips
links that already exist.

Usage:
    poetry run python manage.py link_individuals
    poetry run python manage.py link_individuals --dry-run
"""

from django.core.management.base import BaseCommand

from apps.clients.models import ClientEntityLink, Entity, EntityType, LinkRole


class Command(BaseCommand):
    help = "Create taxpayer links for all individual entities."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without writing to DB.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        individuals = Entity.objects.filter(
            entity_type=EntityType.INDIVIDUAL
        ).select_related("client")

        created = 0
        skipped = 0

        for entity in individuals:
            exists = ClientEntityLink.objects.filter(
                client=entity.client,
                entity=entity,
                role=LinkRole.TAXPAYER,
            ).exists()

            if exists:
                skipped += 1
                continue

            if not dry_run:
                ClientEntityLink.objects.create(
                    client=entity.client,
                    entity=entity,
                    role=LinkRole.TAXPAYER,
                    is_primary=True,
                )
            created += 1

        action = "Would create" if dry_run else "Created"
        self.stdout.write(self.style.SUCCESS(f"  {action}: {created} taxpayer links"))
        if skipped:
            self.stdout.write(self.style.WARNING(f"  Skipped (already exist): {skipped}"))
