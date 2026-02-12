# TTS Tax App — Dev server launcher
# Usage: .\scripts\run_dev.ps1

$ErrorActionPreference = "Stop"

# Ensure we're in the server directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$serverDir = Split-Path -Parent $scriptDir
Set-Location $serverDir

Write-Host "=== TTS Tax App Dev Server ===" -ForegroundColor Cyan

# Check Docker Postgres is running
$container = docker ps --filter "name=tts_tax_db" --format "{{.Status}}" 2>$null
if (-not $container) {
    Write-Host "Starting Postgres container..." -ForegroundColor Yellow
    docker compose -f ../docker-compose.yml up -d
    Start-Sleep -Seconds 3
} else {
    Write-Host "Postgres: $container" -ForegroundColor Green
}

# Run migrations if needed
Write-Host "Checking migrations..." -ForegroundColor Cyan
poetry run python manage.py migrate --check 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Running migrations..." -ForegroundColor Yellow
    poetry run python manage.py migrate
}

# Start dev server
Write-Host "Starting Django on http://127.0.0.1:8000" -ForegroundColor Green
poetry run python manage.py runserver 127.0.0.1:8000
