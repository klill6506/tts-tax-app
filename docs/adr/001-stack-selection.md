# ADR 001 — Stack Selection

**Status**: Accepted
**Date**: 2026-02-12

## Context
Building a multi-user tax preparation app for small firms. Needs to run on-prem
on a Windows Server, support ~9 concurrent preparers, and handle sensitive PII.

## Decision
- **Backend**: Django 5.2 LTS + Django REST Framework
- **Database**: PostgreSQL 16 (multi-user, ACID, mature)
- **Desktop client**: Electron (cross-platform potential, Windows first)
- **UI framework**: Tailwind UI / Tailwind Plus
- **Dev tooling**: Poetry (deps), Docker Compose (dev Postgres), pytest (testing)
- **Python version**: 3.13 (stable, good dependency support)

## Rationale
- Django: battle-tested for data-heavy apps, excellent ORM, built-in admin, auth, migrations
- Postgres: required for real multi-user concurrency; SQLite cannot handle concurrent writers
- Electron: allows web tech skills for desktop; firm already plans Windows deployment
- Poetry: reproducible dependency management with lockfile

## Consequences
- Server requires Postgres installation on production (bundled installer planned)
- Electron adds some overhead vs native, but simplifies UI development
- Django's synchronous model is fine for ~9 users; async can be added later if needed
