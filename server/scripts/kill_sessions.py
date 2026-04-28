"""Kill stale test_postgres sessions on Supabase."""
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.db import connection
connection.ensure_connection()
cur = connection.cursor()
cur.execute(
    "SELECT pid, state, query FROM pg_stat_activity WHERE datname = 'test_postgres'"
)
rows = cur.fetchall()
print(f"Found {len(rows)} sessions on test_postgres:")
for pid, state, query in rows:
    print(f"  pid={pid} state={state} query={query[:60]}")

cur.execute(
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
    "WHERE datname = 'test_postgres' AND pid <> pg_backend_pid()"
)
terminated = cur.fetchall()
print(f"Terminated {len(terminated)} sessions")
