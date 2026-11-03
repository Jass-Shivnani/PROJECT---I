@echo off
title Dione AI — Sovereign Native Desktop Application
cd /d "%~dp0"
set PYTHONPATH=.
echo ========================================================
echo   Launching Dione AI Sovereign Native Desktop Application
echo ========================================================
".venv\Scripts\python.exe" dione_native_app.py
pause
