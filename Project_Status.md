# TTS Tax App – Project Status (as of today)

## Goal (current direction)
Build a modern, Windows-first professional tax prep replacement for small/mid firms (targeting firms like ours: ~3,000 returns / 9 preparers).
- Desktop client: Electron (Windows first)
- UI kit: Tailwind UI / Tailwind Plus
- Server: Django on an on-prem Windows Server
- Database: Postgres (shared multi-user)
- Remote access: use the firm’s existing VPN (Option 1), not custom remote access
- AI: for now, AI is a help/Q&A layer (like an intelligent help screen), potentially a separate module; internet access is OK
- QuickBooks: mostly QBDT. V1 will rely on exporting Trial Balance to Excel/CSV and importing into the software. QBO direct pull is a later “sweetener.”

## Key architecture decisions (locked for now)
1) Multi-user “real server software” (not file-based return files on a shared drive).
2) Database-first model: returns live as records in Postgres; file exports can exist later for backup/transfer, but not as the primary storage.
3) Bundled installer for the office server:
   - Installs and configures: Django server + Postgres (and later Redis if needed).
   - Workstations install Electron client only.
4) Development DB setup:
   - Use Postgres inside Docker (dev only). End users do NOT install Docker.

## Current local environment status
- Docker Desktop was installed on the dev machine.
- During install it requested WSL update / “Linux install” — this is normal for Docker on Windows.
- Docker now appears up and running.
- Dev folder chosen: `D:\dev\tts-tax-app`
- Machine RAM: 64 GB. Suggested Docker memory cap: 8 GB (optional).

## What we were about to do next (step-by-step)
### Step A — Create Postgres container via Docker Compose
1) Create a `docker-compose.yml` in `D:\dev\tts-tax-app\`:

   services:
     db:
       image: postgres:16
       container_name: tts_tax_db
       environment:
         POSTGRES_DB: tts_tax
         POSTGRES_USER: tts
         POSTGRES_PASSWORD: tts_dev_pw_change_me
       ports:
         - "5432:5432"
       volumes:
         - tts_tax_pgdata:/var/lib/postgresql/data
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U tts -d tts_tax"]
         interval: 5s
         timeout: 5s
         retries: 10

   volumes:
     tts_tax_pgdata:

2) Start it from PowerShell:
   - `cd D:\dev\tts-tax-app`
   - `docker compose up -d`
   - `docker compose ps`

3) Sanity check:
   - `docker exec -it tts_tax_db psql -U tts -d tts_tax -c "SELECT version();"`

### Step B — Install Poetry (not installed yet)
We intended to use Poetry for Python dependency management, but Poetry is not installed yet.

Poetry install plan (PowerShell):
1) `py -m pip install --user pipx`
2) `py -m pipx ensurepath`
3) Close and reopen PowerShell (PATH refresh)
4) `pipx install poetry`
5) `poetry --version` (confirm it works)

Note: Python version reported on the machine: 3.14.0

### Step C — Create Django server skeleton (after Poetry + Postgres are working)
Target folder: `D:\dev\tts-tax-app\server`

High-level steps we planned:
1) `poetry init -n`
2) install Django + Postgres driver + dotenv + pytest
3) `poetry run django-admin startproject config .`
4) add `.env` with DB creds matching docker-compose
5) configure `DATABASES` in Django settings to use Postgres from `.env`
6) run migrations: `poetry run python manage.py migrate`
7) run server: `poetry run python manage.py runserver`

## Items explicitly deferred (do not do yet)
- Redis (only add once we introduce background jobs/queues)
- Installer packaging (later milestone)
- Direct QBDT integration (we’ll do TB export/import first)
- QBO direct pull (later)
- Full AI in-product automation (start as help/Q&A layer)
- Full security hardening (we will enforce “no PII in dev,” but not full enterprise controls immediately)

## Process / governance goals
- Bob acts as “senior developer” and writes Claude Code implementation tickets.
- Add two review supervisors:
  1) Architect/QA supervisor: checks code vs plan, tests, maintainability
  2) Security supervisor: checks PII handling, auth boundaries, logging redaction, secrets, etc.
- Maintain project memory via:
  - docs/PROJECT_CHARTER.md
  - docs/adr/ (architecture decision records)
  - docs/DEVLOG.md

## Next question to resolve when we resume
- Proceed with Docker Postgres container setup (Step A), then install Poetry (Step B), then Django skeleton (Step C).
