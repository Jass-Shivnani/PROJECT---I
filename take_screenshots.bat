@echo off
title Dione AI — Focused Live Window Capture
cd /d "%~dp0"
echo ================================================================
echo   DIONE AI: CAPTURING FOCUSED LIVE WINDOWS (NOT FULL DESKTOP)
echo ================================================================
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0docs\run_and_capture_live_windows.py"
) else (
    python "%~dp0docs\run_and_capture_live_windows.py"
)
pause
