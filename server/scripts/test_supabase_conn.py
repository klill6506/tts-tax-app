"""Test the Supabase Postgres connection using .env credentials."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

import psycopg

HOST = os.getenv("DB_HOST")
PORT = int(os.getenv("DB_PORT", "5432"))
DB = os.getenv("DB_NAME")
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")

print(f"Connecting to {HOST}:{PORT}/{DB} as {USER}...")
try:
    conn = psycopg.connect(
        host=HOST, port=PORT, dbname=DB, user=USER, password=PASSWORD,
        connect_timeout=10,
    )
    cur = conn.cursor()
    cur.execute("SELECT version()")
    print(f"OK! {cur.fetchone()[0]}")
    cur.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    tables = [r[0] for r in cur.fetchall()]
    print(f"\n--- {len(tables)} tables ---")
    for t in tables:
        print(f"  {t}")
    conn.close()
    print("\nConnection test PASSED")
except Exception as e:
    print(f"FAILED: {e}")
