@echo off
title Dione AI - Capstone Stage-2 Live Teacher Demonstration (Group 19)
cd /d "%~dp0"
cls
echo =======================================================================
echo   DIONE AI: PRIVACY-PRESERVING LOCAL LARGE ACTION MODEL (LAM)
echo   B.E. Final Year Capstone Project Review Demonstration (2025-26)
echo   Department of Computer Engineering, VESIT
echo =======================================================================
echo.
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0tests\demo_live_interactive.py"
) else (
    python "%~dp0tests\demo_live_interactive.py"
)
pause
