@echo off
title Dione AI - Live Organic Interactive Chat (Group 19, VESIT)
cd /d "%~dp0"
cls
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m server.cli.dione_cli client
) else (
    python -m server.cli.dione_cli client
)
pause
