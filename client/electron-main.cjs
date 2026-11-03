const { app, BrowserWindow, Tray, Menu, globalShortcut, screen, session, ipcMain } = require('electron');

// IPC Handlers for non-intrusive autonomous window control
ipcMain.on('window:minimize', () => {
  if (mainWindow && !mainWindow.isMinimized()) {
    mainWindow.minimize();
  }
});
ipcMain.on('window:hide', () => {
  if (mainWindow) {
    mainWindow.hide();
  }
});
ipcMain.on('window:show', () => {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  }
});
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

// Optimize Chromium rendering flags for Windows 10/11 & custom OS setups
app.commandLine.appendSwitch('no-sandbox');
app.commandLine.appendSwitch('ignore-gpu-blocklist');

let mainWindow = null;
let hudWindow = null;
let tray = null;
let pythonProcess = null;
let isQuitting = false;
let monitorInterval = null;

const BACKEND_URL = 'http://127.0.0.1:8900';
const HEALTH_URL = 'http://127.0.0.1:8900/api/health';
const STATUS_URL = 'http://127.0.0.1:8900/api/desktop/status';
const ABORT_URL = 'http://127.0.0.1:8900/api/desktop/abort';
const PROJECT_ROOT = path.resolve(__dirname, '..');
const ICON_PATH = path.join(__dirname, 'icon.png');
const SPLASH_PATH = path.join(__dirname, 'splash.html');

// Check if backend is alive
function checkBackendHealth() {
  return new Promise((resolve) => {
    http.get(HEALTH_URL, (res) => {
      resolve(res.statusCode === 200);
    }).on('error', () => {
      resolve(false);
    });
  });
}

// Fetch desktop status
function checkDesktopStatus() {
  return new Promise((resolve) => {
    http.get(STATUS_URL, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(null);
        }
      });
    }).on('error', () => {
      resolve(null);
    });
  });
}

// Post emergency abort
function triggerEmergencyAbort() {
  return new Promise((resolve) => {
    const req = http.request(ABORT_URL, { method: 'POST' }, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.end();
  });
}

// Spawn Python backend if needed
async function ensureBackendRunning() {
  const isAlive = await checkBackendHealth();
  if (isAlive) {
    console.log('[Electron] Connected to existing Dione backend on 8900.');
    return true;
  }

  const pythonExe = process.platform === 'win32'
    ? path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe')
    : path.join(PROJECT_ROOT, '.venv', 'bin', 'python');

  console.log('[Electron] Spawning Dione Python backend at:', pythonExe);
  pythonProcess = spawn(
    pythonExe,
    ['-m', 'uvicorn', 'server.api.app:app', '--host', '127.0.0.1', '--port', '8900'],
    {
      cwd: PROJECT_ROOT,
      stdio: 'pipe',
      detached: false,
    }
  );

  pythonProcess.stdout.on('data', (d) => process.stdout.write(`[Backend] ${d}`));
  pythonProcess.stderr.on('data', (d) => process.stderr.write(`[Backend] ${d}`));

  return false;
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1080,
    minHeight: 700,
    title: 'Dione AI — Sovereign Local Workspace',
    icon: ICON_PATH,
    backgroundColor: '#07080f',
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.cjs'),
    },
  });

  // Forward renderer console output to terminal
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[Renderer] ${message}`);
  });

  // Immediate high-tech splash load: ensures window is never black
  mainWindow.loadFile(SPLASH_PATH);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  // Minimize to tray instead of closing
  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });
}

function createHudWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { x, y, width, height } = primaryDisplay.bounds;

  // Full-Monitor Security Shield Overlay covering the entire physical display
  hudWindow = new BrowserWindow({
    x: x,
    y: y,
    width: width,
    height: height,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    focusable: false,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.cjs'),
    },
  });

  hudWindow.setAlwaysOnTop(true, 'screen-saver');
  // Forward mouse clicks so AI actions pass through directly to background windows
  hudWindow.setIgnoreMouseEvents(true, { forward: true });

  const hudHtml = `
  <!DOCTYPE html>
  <html>
  <head>
    <meta charset="utf-8">
    <style>
      * { box-sizing: border-box; }
      body {
        margin: 0;
        padding: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(6, 8, 16, 0.28);
        border: 4px solid rgba(239, 68, 68, 0.75);
        box-shadow: inset 0 0 60px rgba(239, 68, 68, 0.3), inset 0 0 120px rgba(168, 85, 247, 0.2);
        user-select: none;
        pointer-events: none;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        animation: borderPulse 2s ease-in-out infinite alternate;
      }
      @keyframes borderPulse {
        0% { border-color: rgba(239, 68, 68, 0.65); box-shadow: inset 0 0 40px rgba(239, 68, 68, 0.25); }
        100% { border-color: rgba(168, 85, 247, 0.85); box-shadow: inset 0 0 80px rgba(168, 85, 247, 0.4); }
      }
      .top-banner {
        margin-top: 18px;
        display: flex;
        align-items: center;
        gap: 16px;
        background: rgba(9, 11, 22, 0.96);
        border: 1px solid rgba(239, 68, 68, 0.6);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.9), 0 0 35px rgba(239, 68, 68, 0.35);
        border-radius: 9999px;
        padding: 10px 28px;
        backdrop-filter: blur(24px);
      }
      .pulse-ring {
        position: relative;
        width: 14px;
        height: 14px;
      }
      .pulse-ring::before {
        content: '';
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: #ef4444;
        opacity: 0.85;
        animation: ping 1s cubic-bezier(0, 0, 0.2, 1) infinite;
      }
      .pulse-ring::after {
        content: '';
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: #f87171;
      }
      @keyframes ping {
        75%, 100% {
          transform: scale(2.4);
          opacity: 0;
        }
      }
      .text-col {
        display: flex;
        flex-direction: column;
      }
      .title {
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: #ffffff;
      }
      .sub {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 2px;
      }
      .sub strong {
        color: #fca5a5;
      }
      .badge {
        background: rgba(239, 68, 68, 0.25);
        border: 1px solid rgba(239, 68, 68, 0.7);
        color: #fca5a5;
        font-size: 10px;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 8px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }
      .abort-pill {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #f1f5f9;
        font-size: 10px;
        font-weight: 700;
        padding: 4px 8px;
        border-radius: 6px;
      }
    </style>
  </head>
  <body>
    <div class="top-banner">
      <div class="pulse-ring"></div>
      <div class="text-col">
        <span class="title">Dione Autonomous Computer Control Active</span>
        <span class="sub">Hands off mouse & keyboard &bull; Press <span class="abort-pill">ESC</span> or <span class="abort-pill">Ctrl+Alt+X</span> to <strong>STOP IMMEDIATELY</strong></span>
      </div>
      <span class="badge">Station Shield Active</span>
    </div>
  </body>
  </html>
  `;

  hudWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(hudHtml)}`);
}

function createTray() {
  try {
    tray = new Tray(ICON_PATH);
    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Open Dione Workspace',
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          }
        },
      },
      {
        label: 'Toggle Visibility (Ctrl+Shift+D)',
        click: () => toggleWindow(),
      },
      {
        label: 'Emergency Abort (Esc)',
        click: () => triggerEmergencyAbort(),
      },
      { type: 'separator' },
      {
        label: 'Quit Dione',
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ]);

    tray.setToolTip('Dione AI — Sovereign Local Workspace');
    tray.setContextMenu(contextMenu);
    tray.on('double-click', () => {
      if (mainWindow) {
        mainWindow.show();
        mainWindow.focus();
      }
    });
  } catch (err) {
    console.debug('[Electron] Tray initialization note:', err.message);
  }
}

function toggleWindow() {
  if (!mainWindow) return;
  if (mainWindow.isVisible()) {
    mainWindow.hide();
  } else {
    mainWindow.show();
    mainWindow.focus();
  }
}

function startStatePolling() {
  monitorInterval = setInterval(async () => {
    try {
      const status = await checkDesktopStatus();
      const isAutonomous = status && (status.ai_active || status.autonomous_active);
      if (isAutonomous) {
        // Non-intrusive Headless / Background Operation:
        // Automatically minimize Dione main window so target app/game is 100% unobstructed
        if (mainWindow && mainWindow.isVisible() && !mainWindow.isMinimized()) {
          mainWindow.minimize();
        }
      }
    } catch {
      // ignore transient poll errors
    }
  }, 250);
}

app.whenReady().then(async () => {
  // Ensure microphone, audio, and media permissions are approved
  if (session && session.defaultSession) {
    session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
      if (permission === 'media') {
        return callback(true);
      }
      callback(true);
    });
    session.defaultSession.setPermissionCheckHandler((webContents, permission, requestingOrigin) => {
      if (permission === 'media') {
        return true;
      }
      return true;
    });
  }

  createMainWindow();
  createHudWindow();
  createTray();
  startStatePolling();
  ensureBackendRunning();

  // Register Global Hotkeys
  try {
    globalShortcut.register('CommandOrControl+Shift+D', toggleWindow);
    const onEmergencyStop = () => {
      console.log('[Electron] Emergency Stop Hotkey triggered! Aborting AI control...');
      triggerEmergencyAbort();
      if (hudWindow) hudWindow.hide();
    };
    globalShortcut.register('Escape', onEmergencyStop);
    globalShortcut.register('CommandOrControl+Alt+X', onEmergencyStop);
    globalShortcut.register('CommandOrControl+Alt+Q', onEmergencyStop);
  } catch (err) {
    console.debug('Hotkey registration skipped:', err);
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    } else if (mainWindow) {
      mainWindow.show();
    }
  });
});

app.on('will-quit', () => {
  if (monitorInterval) clearInterval(monitorInterval);
  globalShortcut.unregisterAll();
  if (pythonProcess) {
    console.log('[Electron] Terminating Python backend subprocess...');
    try {
      pythonProcess.kill('SIGTERM');
    } catch (e) {
      // ignore
    }
  }
});
