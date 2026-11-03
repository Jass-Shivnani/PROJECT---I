@echo off
title Dione AI - VisionOS Web Interface
cd /d "%~dp0\client"
echo ========================================================
echo   Launching Dione VisionOS Spatial Interface on Port 5173
echo ========================================================
call npm run dev
pause
