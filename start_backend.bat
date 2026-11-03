@echo off
title Dione AI - Backend Server
cd /d "%~dp0"
echo ========================================================
echo   Launching Dione AI Sovereign Backend on Port 8900
echo ========================================================
set PYTHONPATH=.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m uvicorn server.api.app:app --host 0.0.0.0 --port 8900 --reload
) else (
    python -m uvicorn server.api.app:app --host 0.0.0.0 --port 8900 --reload
)
pause
