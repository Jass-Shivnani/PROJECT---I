@echo off
REM ==============================================================================
REM   DIONE AI -- Unified Desktop Application Launcher
REM   Launches Dione Edge WebView2 Desktop App silently without lingering console
REM ==============================================================================

cd /d "%~dp0"

if "%~1"=="" (
    if exist "%~dp0Dione.vbs" (
        start "" wscript.exe "%~dp0Dione.vbs"
        exit /b 0
    )
)

if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" -m server.cli.dione_cli app %*
    exit /b 0
)

python -m server.cli.dione_cli app %*
exit /b 0
