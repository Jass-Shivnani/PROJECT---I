@echo off
REM ==============================================================================
REM   DIONE AI -- Sovereign Local Workspace (Native Desktop Launcher)
REM   Hosts React Command Center inside Electron with Autonomous HUD Dock
REM ==============================================================================

cd /d "%~dp0"
title Dione AI Sovereign Native Desktop

echo ==============================================================================
echo   Launching Dione AI Sovereign Workspace (Native Desktop Station)...
echo ==============================================================================

if not exist "client\node_modules" (
    echo [Setup] Installing client desktop dependencies...
    cd client && npm install && cd ..
)

if not exist "client\dist" (
    echo [Build] Building React VisionOS frontend...
    cd client && npm run build && cd ..
)

echo [Launch] Starting Electron Native Workspace Window...
cd client
npx electron electron-main.cjs
cd ..
