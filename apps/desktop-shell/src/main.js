const { app, BrowserWindow, shell, Menu } = require('electron');
const path = require('path');
const { isTrustedPortalUrl, isSafeExternalUrl } = require('./navigation-policy');

// Which site this build of the shell points at. `configs/active.json` is
// written by the `select-config.js` script before packaging -- baked in at
// build time, not read from an env var at runtime.
const config = require(path.join(__dirname, 'configs', 'active.json'));

let mainWindow;

function openSafeExternalUrl(url) {
  if (isSafeExternalUrl(url, config.url)) {
    // Electron's external opener is only reached for HTTPS URLs.
    void shell.openExternal(url);
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    icon: path.join(__dirname, '..', 'build', 'icon.png'),
    title: config.title,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  mainWindow.loadURL(config.url);

  // Trust only the exact HTTPS origin selected for this build. Do not accept
  // arbitrary sibling subdomains based on hostname suffix matching.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isTrustedPortalUrl(url, config.url)) {
      return { action: 'allow' };
    }
    openSafeExternalUrl(url);
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!isTrustedPortalUrl(url, config.url)) {
      event.preventDefault();
      openSafeExternalUrl(url);
    }
  });

  Menu.setApplicationMenu(buildMenu());
}

function buildMenu() {
  return Menu.buildFromTemplate([
    {
      label: config.title,
      submenu: [
        { label: 'Reload', accelerator: 'CmdOrCtrl+R', click: () => mainWindow.reload() },
        { label: 'Toggle DevTools', accelerator: 'CmdOrCtrl+Shift+I', click: () => mainWindow.webContents.toggleDevTools() },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
  ]);
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
