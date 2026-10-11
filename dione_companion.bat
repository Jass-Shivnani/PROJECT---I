@echo off
REM ================================================================
REM   DIONE AI -- Next-Gen Native Dynamic Island Desktop Companion
REM ================================================================

set "DIONE_ROOT=%~dp0"
set "DIONE_ROOT=%DIONE_ROOT:~0,-1%"

if exist "%DIONE_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON=%DIONE_ROOT%\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo Starting Dione Next-Gen Desktop Companion...
"%PYTHON%" -m server.cli.dione_cli companion
