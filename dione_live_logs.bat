@echo off
title Dione AI - Live Engine Log Stream (Real-Time System Monitor)
cd /d "%~dp0"
cls
echo =======================================================================
echo   DIONE AI: REAL-TIME ENGINE LOG STREAM
echo   Streaming internal ReAct reasoning, tool execution, and Gemini calls
echo =======================================================================
echo.
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m server.cli.dione_cli logs -f --lines 30
) else (
    python -m server.cli.dione_cli logs -f --lines 30
)
pause
