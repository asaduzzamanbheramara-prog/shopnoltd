const { app, BrowserWindow, shell, Menu } = require('electron');
const path = require('path');

// Which site this build of the shell points at. `configs/active.json` is
// written by the `prebuild:web` / `prebuild:admin` npm script before
// packaging -- baked in at build time, not read from an env var at runtime,
// since a double-clicked packaged app won't have SHOPNO_TARGET set.
const config = require(path.join(__dirname, 'configs', 'active.json'));

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    icon: path.join(__dirname, '..', 'build', 'icon.png'),
    title: config.title,
    webPreferences: {
      nodeIntegration: false,      // never expose Node APIs to the loaded site
      contextIsolation: true,       // required alongside nodeIntegration:false
      sandbox: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  mainWindow.loadURL(config.url);

  // Anything that isn't your own domain opens in the system browser instead
  // of inside the app -- avoids the app silently becoming a general-purpose
  // browser for arbitrary sites.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (new URL(url).hostname.endsWith(config.allowedHostSuffix)) {
      return { action: 'allow' };
    }
    shell.openExternal(url);
    return { action: 'deny' };
  });
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!new URL(url).hostname.endsWith(config.allowedHostSuffix)) {
      event.preventDefault();
      shell.openExternal(url);
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
