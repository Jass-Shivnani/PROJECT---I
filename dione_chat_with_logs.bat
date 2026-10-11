@echo off
title Dione AI - Live Organic Interactive Chat (Group 19, VESIT)
cd /d "%~dp0"
cls
echo =======================================================================
echo   DIONE AI: DUAL-SCREEN LIVE DEMONSTRATION MODE
echo   Launching Real-Time Engine Log Monitor in a companion window...
echo =======================================================================
echo.
REM Launch live log monitor in separate companion terminal window
start "Dione AI - Live Engine Log Monitor" cmd /c "%~dp0dione_live_logs.bat"

timeout /t 1 /nobreak >nul

REM Launch interactive chat client in this window
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m server.cli.dione_cli client
) else (
    python -m server.cli.dione_cli client
)
pause
