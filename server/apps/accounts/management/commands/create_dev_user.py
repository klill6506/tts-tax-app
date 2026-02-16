"""
Create a dev user with a firm membership for local development.

Run: poetry run python manage.py create_dev_user
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.firms.models import Firm, FirmMembership, Role

User = get_user_model()

DEV_USERNAME = "dev"
DEV_PASSWORD = "dev"
DEV_EMAIL = "dev@localhost"
DEV_FIRM_NAME = "Dev Tax Firm"


class Command(BaseCommand):
    help = "Create a dev user with firm membership for local development."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username=DEV_USERNAME,
            defaults={
                "email": DEV_EMAIL,
                "first_name": "Dev",
                "last_name": "User",
                "is_staff": True,
            },
        )
        if created:
            user.set_password(DEV_PASSWORD)
            user.save()
            self.stdout.write(f"Created user '{DEV_USERNAME}' with password '{DEV_PASSWORD}'.")
        else:
            self.stdout.write(f"User '{DEV_USERNAME}' already exists.")

        firm, _ = Firm.objects.get_or_create(
            name=DEV_FIRM_NAME,
            defaults={"is_active": True},
        )

        membership, mem_created = FirmMembership.objects.get_or_create(
            user=user,
            firm=firm,
            defaults={"role": Role.ADMIN, "is_active": True},
        )
        if mem_created:
            self.stdout.write(f"Added '{DEV_USERNAME}' to '{DEV_FIRM_NAME}' as admin.")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDev login ready:  username={DEV_USERNAME}  password={DEV_PASSWORD}"
            )
        )
