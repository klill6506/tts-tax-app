@echo off
title TTS Tax App Launcher
color 0B
echo.
echo  =============================================
echo   TTS Tax App — Starting All Services
echo  =============================================
echo.

cd /d "D:\dev\tts-tax-app"

:: 1) Start Postgres if not already running
echo [1/3] Checking Postgres...
docker ps --filter "name=tts_tax_db" --format "{{.Status}}" 2>nul | findstr /i "Up" >nul
if errorlevel 1 (
    echo       Starting Postgres container...
    docker compose up -d
    timeout /t 4 /nobreak >nul
) else (
    echo       Postgres already running.
)

:: 2) Start Django server hidden (minimized, no visible window)
echo [2/3] Starting Django server...
start /min "" cmd /c "cd /d D:\dev\tts-tax-app\server && poetry run python manage.py runserver 127.0.0.1:8000"

:: Give Django a moment to start
timeout /t 3 /nobreak >nul

:: 3) Start Electron client (the app window IS the UI — no extra console)
echo [3/3] Starting Electron client...
start /min "" cmd /c "cd /d D:\dev\tts-tax-app\client && npm run dev"

echo.
echo  =============================================
echo   All services launched!
echo   - Postgres:  localhost:5432
echo   - Django:    running in background
echo   - Electron:  opening...
echo  =============================================
echo.
timeout /t 3 /nobreak >nul
exit
