"""Ensure the superuser has a FirmMembership."""
import os
import sys
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
django.setup()

from django.contrib.auth.models import User
from apps.firms.models import Firm, FirmMembership, Role

for u in User.objects.all():
    memberships = FirmMembership.objects.filter(user=u)
    print(f"  {u.username}: {memberships.count()} memberships")

# Get the firm and superuser
firm = Firm.objects.first()
if not firm:
    print("No firm found!")
    sys.exit(1)

superusers = User.objects.filter(is_superuser=True)
for su in superusers:
    membership, created = FirmMembership.objects.get_or_create(
        user=su,
        firm=firm,
        defaults={"role": Role.ADMIN},
    )
    if created:
        print(f"Created ADMIN membership for {su.username} in {firm.name}")
    else:
        print(f"{su.username} already has membership in {firm.name}")
