@echo off
title Dione AI - Quick Environment Setup (Group 19, VESIT)
cd /d "%~dp0"
echo =====================================================================
echo                DIONE AI - AUTOMATED SETUP
echo          Capstone Project - Group 19 (VESIT 2025-26)
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
echo [*] Installing all required dependencies...
"%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
"%~dp0.venv\Scripts\python.exe" -m pip install -r requirements.txt

if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Some dependencies had warnings or issues. Retrying core dependencies...
    "%~dp0.venv\Scripts\python.exe" -m pip install -r server\requirements.txt
)

echo.
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Initializing .env from .env.example...
        copy ".env.example" ".env" >nul
        echo [OK] .env initialized.
    )
) else (
    echo [OK] Active .env configuration verified.
)

echo.
echo =====================================================================
echo               SETUP COMPLETE! READY TO RUN DIONE
echo =====================================================================
echo To start chatting with Dione, double-click:
echo     dione_chat.bat
echo.
pause
