@echo off
REM ================================================================
REM   DIONE AI — Command Line Interface
REM   Usage: dione start | setup | reset | restart | status | ...
REM ================================================================

REM Find the project root (where this .cmd lives)
set "DIONE_ROOT=%~dp0"
set "DIONE_ROOT=%DIONE_ROOT:~0,-1%"

REM Use the project venv if it exists
if exist "%DIONE_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON=%DIONE_ROOT%\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

REM Forward all arguments to the Dione CLI module
"%PYTHON%" -m server.cli.dione_cli %*
