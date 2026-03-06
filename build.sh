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
poetry install --only main

echo "=== Running migrations ==="
poetry run python manage.py migrate --noinput

echo "=== Collecting Django static files ==="
poetry run python manage.py collectstatic --noinput

echo "=== Build complete ==="
