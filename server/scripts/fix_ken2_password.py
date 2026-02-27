"""Fix Ken2 password to match client .env.local."""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth.models import User

user = User.objects.get(username="Ken2")
user.set_password("Tts580198$99")
user.save()
print("Ken2 password updated.")
