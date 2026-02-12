# TTS Tax App — Dev Log

## 2026-02-12 — Project Reset (Ticket 001)
- Cleaned up prior Django skeleton (had nested git repo, flat settings, wrong API path)
- Rebuilt server/ from scratch with proper structure:
  - Settings split: `config/settings/base.py` + `dev.py`
  - Apps under `apps/` namespace
  - Health endpoint at `/api/v1/health/`
  - pytest test suite
  - PowerShell dev launch script
- Created 4 CLAUDE.md instruction files (root, server, client, security)
- Created docs structure (PROJECT_CHARTER, ADRs, DEVLOG)
- Using Python 3.13, Poetry, Docker Compose for Postgres
- Django 5.2 LTS + DRF

## 2026-02-12 — Ticket 002: Firms + Users + Roles
- Created `apps/firms` with `Firm` and `FirmMembership` models (UUID PKs, timestamps)
- Role enum: Admin / Preparer / Reviewer
- Created `apps/accounts` with `/api/v1/me/` endpoint (returns user + firm + role)
- Added `FirmMiddleware` to attach active firm to every request
- Django admin screens for Firm (with inline memberships) and FirmMembership
- Unique constraint: one membership per user per firm
- 10 tests passing (8 new for firms/accounts + 2 existing health tests)

## 2026-02-12 — Ticket 003: Client / Entity / TaxYear Container
- Created `apps/clients` with three models:
  - `Client` (firm-scoped, name, status)
  - `Entity` (S-Corp for now; linked to client)
  - `TaxYear` (year, status, created_by; linked to entity, unique per entity+year)
- Full CRUD via DRF ViewSets: `/api/v1/clients/`, `/api/v1/entities/`, `/api/v1/tax-years/`
- `IsFirmMember` permission class — all endpoints firm-scoped
- Query filters: entities by client, tax-years by entity and year
- Admin screens with inlines (Client→Entities, Entity→TaxYears)
- 34 tests passing (24 new + 10 existing)

## 2026-02-12 — Ticket 004: Audit Log
- Created `apps/audit` with `AuditEntry` model (who, what, when, which record, changes JSON)
- Audit service: `log_create()`, `log_update()`, `log_delete()` with PII field redaction
- `AuditViewSetMixin` — drop into any viewset for automatic audit logging
- Wired into Client/Entity/TaxYear viewsets (create, update, delete all audited)
- Read-only API at `/api/v1/audit-log/` with model/action/record filters
- Admin: immutable audit entries (no add/change/delete in admin)
- 47 tests passing

## 2026-02-12 — Ticket 005: Trial Balance Import Scaffolding
- Created `apps/imports` with `TrialBalanceUpload` and `TrialBalanceRow` models
- File parsers for CSV and XLSX with auto-detect column mapping
  - Handles alternate headers (Acct No, Description, Dr/Cr, etc.)
  - Validates file type (.csv, .xlsx only) and size (50MB max)
- Upload endpoint: `POST /api/v1/tb-uploads/upload/` (multipart file + tax_year UUID)
- List/detail endpoints for uploads and parsed rows
- All uploads firm-scoped and audit-logged
- 64 tests passing (17 new for imports + 47 existing)

## 2026-02-12 — Ticket 006: Mapping Templates
- Created `apps/mappings` with `MappingTemplate` and `MappingRule` models
- Template hierarchy: firm-level default → client-specific override
- Rule match modes: exact account number, prefix, or contains (account name)
- Priority-based rule ordering (highest wins)
- Mapping engine: `apply_template()` classifies TB rows → tax lines
- Apply endpoint: `POST /api/v1/mapping-templates/apply/` (auto-resolve or explicit template)
- CRUD for templates and rules, all firm-scoped and audit-logged
- 81 tests passing

## 2026-02-12 — Ticket 007: Diagnostics Framework
- Created `apps/diagnostics` with `DiagnosticRule`, `DiagnosticRun`, `DiagnosticFinding`
- Pluggable rule engine: rules are Python functions registered by dotted path
- 3 built-in rules: TB_EXISTS, TB_BALANCE, TB_ZERO_ROWS
- Runner executes all active rules, produces findings with severity (error/warning/info)
- `POST /api/v1/diagnostic-runs/run/` triggers diagnostics for a tax year
- `manage.py seed_rules` command to seed/update built-in rules
- 97 tests passing (16 new for diagnostics + 81 existing)

## Step 1 (Platform Spine) — COMPLETE
All 6 planned features delivered:
1. Auth + firms + roles
2. Entities + tax years
3. Audit log + activity feed
4. TB upload + parse + store raw rows
5. Mapping templates (per firm + per client)
6. Minimal diagnostics framework
