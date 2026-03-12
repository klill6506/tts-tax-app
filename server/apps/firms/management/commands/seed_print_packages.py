"""
Seed default print packages for all active firms.

Run: poetry run python manage.py seed_print_packages
"""

from django.core.management.base import BaseCommand

from apps.firms.models import Firm, PrintPackage

DEFAULT_PACKAGES = [
    ("all",       "All Forms",          "Complete return with all forms",    0),
    ("client",    "Client Copy",        "Letter + Invoice + all forms",      10),
    ("filing",    "Filing Copy",        "All return forms (no letter/invoice)", 20),
    ("extension", "Extension Package",  "Form 7004 only",                    30),
    ("state",     "State Only",         "State return only",                 40),
    ("k1s",       "K-1 Package",        "All K-1s only",                     50),
    ("invoice",   "Invoice Only",       "Invoice only",                      60),
    ("letter",    "Letter Only",        "Letter only",                       70),
]


class Command(BaseCommand):
    help = "Seed default print packages for all active firms."

    def handle(self, *args, **options):
        firms = Firm.objects.filter(is_active=True)
        if not firms.exists():
            self.stdout.write(self.style.WARNING("No active firms found."))
            return

        for firm in firms:
            count = 0
            for code, name, description, sort_order in DEFAULT_PACKAGES:
                _, created = PrintPackage.objects.update_or_create(
                    firm=firm,
                    code=code,
                    defaults={
                        "name": name,
                        "description": description,
                        "sort_order": sort_order,
                        "is_active": True,
                    },
                )
                if created:
                    count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"  {firm.name}: {count} new packages "
                    f"({len(DEFAULT_PACKAGES)} total)"
                )
            )
