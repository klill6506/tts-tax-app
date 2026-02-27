"""Create Ken2 superuser and The Tax Shelter firm in Supabase."""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth.models import User
from apps.firms.models import Firm, FirmMembership

# Create The Tax Shelter firm
firm, created = Firm.objects.get_or_create(name="The Tax Shelter")
print(f"{'Created' if created else 'Found'} firm: The Tax Shelter (id={firm.id})")

# Create Ken2 superuser
if not User.objects.filter(username="Ken2").exists():
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "changeme")
    user = User.objects.create_superuser("Ken2", "", password)
    FirmMembership.objects.create(user=user, firm=firm, role="admin")
    print(f"Created superuser Ken2 (id={user.id})")
else:
    user = User.objects.get(username="Ken2")
    print(f"User Ken2 already exists (id={user.id})")
    if not FirmMembership.objects.filter(user=user, firm=firm).exists():
        FirmMembership.objects.create(user=user, firm=firm, role="admin")
        print("Linked Ken2 to The Tax Shelter")

print("\nDone! Ken2 can log in to the tax app.")
