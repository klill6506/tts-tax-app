"""Root conftest — handles Supabase pooler stale sessions during test DB teardown."""
import psycopg
from django.conf import settings


def _kill_test_db_sessions():
    """Terminate all connections to test_postgres so Django can drop it."""
    db = settings.DATABASES["default"]
    try:
        conn = psycopg.connect(
            host=db["HOST"],
            port=db["PORT"],
            dbname="postgres",
            user=db["USER"],
            password=db["PASSWORD"],
            autocommit=True,
        )
        cur = conn.cursor()
        test_db_name = db.get("TEST", {}).get("NAME", f"test_{db['NAME']}")
        for _ in range(5):
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid != pg_backend_pid()",
                (test_db_name,),
            )
            cur.fetchall()
        cur.close()
        conn.close()
    except Exception:
        pass


def pytest_unconfigure(config):
    """Called after all tests finish — kill pooler sessions so DB can be dropped."""
    _kill_test_db_sessions()
