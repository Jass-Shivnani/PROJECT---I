@echo off
title Dione AI - Sovereign AI Operating System
cd /d "%~dp0"
echo ========================================================
echo          DIONE AI - SOVEREIGN COMMAND CENTER
echo ========================================================
echo.

:: 1. Check if .venv exists; if not, run setup.bat
if not exist ".venv\Scripts\python.exe" (
    echo [*] Virtual environment not found. Running initial setup...
    call setup.bat
    if errorlevel 1 (
        echo [ERROR] Setup failed.
        pause
        exit /b 1
    )
)

:: 2. Check if .env exists
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [*] Initialized .env template. Please ensure your GEMINI_API_KEY is configured in .env
    )
)

:: 3. Launch Backend on Port 8900
echo [*] Launching Dione AI Backend on http://localhost:8900...
start "Dione Backend (Port 8900)" cmd /k "start_backend.bat"

:: 4. Poll for Backend Health
echo [*] Waiting for Dione Backend to initialize...
set /a attempts=0
:wait_backend
timeout /t 1 /nobreak >nul
set /a attempts+=1
curl -s -f http://127.0.0.1:8900/api/health >nul 2>&1
if errorlevel 1 (
    if %attempts% lss 35 (
        goto wait_backend
    )
)

:: 5. Launch User Interface
echo [OK] Dione AI is online and operational!
echo.
echo Launching VisionOS interface in your default browser...
start http://localhost:8900
echo.
echo ========================================================
echo   Dione is running at http://localhost:8900
echo   To stop, close the "Dione Backend" console window.
echo ========================================================
echo.
