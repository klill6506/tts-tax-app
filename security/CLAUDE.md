# Security Guidelines — TTS Tax App

## PII / SSN Handling
- **Never log SSN, EIN, ITIN, or full names to application logs**
- Log record UUIDs only; look up details via admin when investigating
- Mask SSN in API responses: return only last 4 digits (`***-**-1234`) unless full value explicitly requested by authorized endpoint
- No PII in error messages, tracebacks, or Sentry-style reporting

## Logging Redaction
- Django logging must use a redaction filter for any field matching SSN/EIN patterns
- Audit log stores "field changed" but NOT the old/new SSN value — store a hash or masked version

## Secrets Management
- All secrets via environment variables (`.env` file, gitignored)
- `.env.example` committed with placeholder values
- No hardcoded passwords, API keys, or tokens in source code
- SECRET_KEY must be unique per environment

## Authentication & Authorization
- Session-based auth (Phase 1)
- Every API endpoint defaults to `IsAuthenticated`
- Firm-scoping: users can only access data for their own firm
- Role-based access: Admin > Reviewer > Preparer

## Encryption
- Postgres connection should use SSL in production
- At-rest encryption: defer to OS/disk-level encryption for now; field-level encryption for SSN planned for later milestone

## File Uploads
- Validate file type (whitelist: .csv, .xlsx, .pdf)
- Validate file size (max 50MB)
- Store uploads outside webroot
- Scan filenames for path traversal attempts

## Dependencies
- Pin all dependency versions via Poetry lockfile
- Review new dependencies before adding (check maintenance status, license, known CVEs)
- Run `poetry audit` (or equivalent) periodically

## Backup & Retention
- Database backups: daily automated (production)
- Retain backups for 90 days minimum
- Test restore procedure quarterly
