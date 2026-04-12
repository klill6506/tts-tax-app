#!/usr/bin/env bash
# build.sh — Render build script
# Builds the React SPA + Django static files in one step.
# Render build command: bash build.sh
#
# Migrations run at container START (not build) because the build
# environment may not have database connectivity.

set -o errexit  # exit on error

echo "=== Building React SPA ==="
cd client
npm install
npx vite build --config vite.config.ts
echo "SPA build output:"
ls -la ../client/dist-web/
cd ..

echo "=== Installing Python dependencies ==="
cd server
pip install poetry
pip install --upgrade attrs  # fix cached attrs version conflict
poetry install --only main

echo "=== Running migrations ==="
poetry run python manage.py migrate --noinput

echo "=== Seeding form definitions ==="
poetry run python manage.py seed_1120s
poetry run python manage.py seed_1065
poetry run python manage.py seed_1120
poetry run python manage.py seed_1040
poetry run python manage.py seed_ga600s
poetry run python manage.py seed_default_mapping
poetry run python manage.py seed_1065_mapping
poetry run python manage.py seed_1120_mapping
poetry run python manage.py seed_rules
poetry run python manage.py seed_print_packages

echo "=== Collecting Django static files ==="
poetry run python manage.py collectstatic --noinput

echo "=== Build complete ==="
