"""Drop leftover test_postgres database and terminate stale sessions."""
import sys
import os

# Ensure server/ is on the path so Django can find config.settings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.dev"

import django
django.setup()

from django.db import connection

with connection.cursor() as cur:
    cur.execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = 'test_postgres' AND pid <> pg_backend_pid()"
    )
    terminated = cur.fetchall()
    print(f"Terminated {len(terminated)} stale sessions")

    cur.execute("DROP DATABASE IF EXISTS test_postgres")
    print("Dropped test_postgres")
