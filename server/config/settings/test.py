"""
Test settings — inherits from base.py and uses whatever DB_* env vars are set.

Today that points at the shared Supabase project (same as dev), so Django will
create and drop a `test_postgres` database on the shared Supabase project for
each test run. That works because conftest.py kills lingering pooler sessions
after teardown, but it's not ideal long-term — a dedicated test Supabase project
or a local Postgres would isolate test runs from prod.

TODO (Ken + Claude): decide on a permanent test DB strategy. Options:
  (a) A second Supabase project (e.g., `sherpa-tax-dev`) for tests.
  (b) Supabase branching (Pro tier feature) to spin up schema copies.
  (c) A local test Postgres (independent of the Docker setup we retired).

Until then, any `pytest` run creates/drops `test_postgres` on the prod project.
Prefer tests that use Django's TransactionTestCase rollback and minimal fixture
data to limit the surface area.
"""

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
