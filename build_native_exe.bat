@echo off
title Dione AI — Build Native Executable (Dione.exe)
cd /d "%~dp0"
echo ========================================================
echo   Compiling Dione AI into Standalone Native Windows Executable
echo ========================================================
set PYTHONPATH=.
".venv\Scripts\pyinstaller.exe" --noconfirm --onedir --windowed --name "Dione" dione_desktop.py
echo.
echo Build complete! Executable is located in dist\Dione\Dione.exe
pause
