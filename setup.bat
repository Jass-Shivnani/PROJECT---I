@echo off
title Dione AI - Quick Environment Setup
cd /d "%~dp0"
echo =====================================================================
echo                DIONE AI - AUTOMATED SETUP
echo =====================================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please install Python 3.10, 3.11, or 3.12 from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

echo [*] Python detected:
python --version
echo.

if not exist ".venv" (
    echo [*] Creating isolated virtual environment (.venv)...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create .venv.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
) else (
    echo [OK] Existing .venv found.
)

echo.
echo [*] Installing required dependencies...
"%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
"%~dp0.venv\Scripts\python.exe" -m pip install -r server\requirements.txt

if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Some optional packages failed to install. Retrying core dependencies...
    "%~dp0.venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo.
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [OK] Initialized .env configuration.
    )
)

echo.
echo =====================================================================
echo               SETUP COMPLETE! READY TO RUN DIONE
echo =====================================================================
echo.
echo Next steps:
echo 1. Open .env and add your GEMINI_API_KEY (from https://aistudio.google.com/apikey)
echo 2. Double-click start_dione.bat to launch the AI Command Center!
echo.
