# Server — Django Conventions

## App Layout
- All Django apps live under `apps/` (e.g., `apps/firms`, `apps/accounts`, `apps/core`)
- App config `name` must be `apps.<appname>`, `label` must be `<appname>`
- Register every app in `config/settings/base.py` INSTALLED_APPS

## Settings
- `config/settings/base.py` — shared, no secrets, no DEBUG
- `config/settings/dev.py` — DEBUG=True, local overrides
- `config/settings/prod.py` — (future) production hardening
- `manage.py` defaults to `config.settings.dev`

## Database Rules
- **Postgres only** — no SQLite, no fallback
- UUID primary keys for domain models (use `models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`)
- Every table gets `created_at` and `updated_at` timestamps
- Soft delete: add `is_deleted` + `deleted_at` where business requires undo; hard-delete for dev/admin only
- Every model change = new migration. Never edit existing migrations.

## Audit Logging
- All create/update/delete on domain models must be logged
- Audit log stores: who, what, when, which record, old/new values
- **Never log SSN, EIN, or other PII in audit entries** — log record IDs only

## API Style
- REST endpoints under `/api/v1/`
- Use Django REST Framework serializers and viewsets
- Auth: session auth for now (JWT or token auth in later ticket)
- Permissions: default `IsAuthenticated`; health endpoint is `AllowAny`
- Return consistent JSON: `{"data": ...}` for success, `{"error": ...}` for failures

## Testing
- pytest + pytest-django
- Test files in `server/tests/` (named `test_*.py`)
- Every endpoint needs at least: happy path + auth check + validation error case
