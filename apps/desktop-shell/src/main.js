const { app, BrowserWindow, shell, Menu, dialog } = require('electron');
const path = require('path');
const { isTrustedPortalUrl, isSafeExternalUrl } = require('./navigation-policy');

const config = require(path.join(__dirname, 'configs', 'active.json'));
const isBrowserApp = config.appId === 'org.shopnoltd.browser';

let mainWindow;

function openSafeExternalUrl(url) {
  if (isSafeExternalUrl(url, config.url)) {
    void shell.openExternal(url).catch(() => {});
  }
}

function focusBrowserAddressBar() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  void mainWindow.webContents.executeJavaScript(
    "document.querySelector('input[aria-label=\\\"Browser address\\\"]')?.focus()"
  ).catch(() => {});
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 960,
    minHeight: 640,
    icon: path.join(__dirname, '..', 'build', 'icon.png'),
    title: config.title,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      webviewTag: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  mainWindow.loadURL(config.url);

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isTrustedPortalUrl(url, config.url)) return { action: 'allow' };
    openSafeExternalUrl(url);
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!isTrustedPortalUrl(url, config.url)) {
      event.preventDefault();
      openSafeExternalUrl(url);
    }
  });

  // Every download requires a user-selected destination; never silently write files.
  mainWindow.webContents.session.on('will-download', async (_event, item) => {
    item.pause();
    try {
      const { canceled, filePath } = await dialog.showSaveDialog(mainWindow, {
        defaultPath: path.join(app.getPath('downloads'), path.basename(item.getFilename())),
        title: 'Save download',
      });
      if (canceled || !filePath) {
        item.cancel();
        return;
      }
      item.setSavePath(filePath);
      item.resume();
    } catch {
      item.cancel();
    }
  });

  Menu.setApplicationMenu(buildMenu());
}

function buildMenu() {
  const navigation = [
    { label: 'Back', accelerator: 'Alt+Left', click: () => { if (mainWindow?.webContents.canGoBack()) mainWindow.webContents.goBack(); } },
    { label: 'Forward', accelerator: 'Alt+Right', click: () => { if (mainWindow?.webContents.canGoForward()) mainWindow.webContents.goForward(); } },
    { label: 'Home', accelerator: 'Alt+Home', click: () => mainWindow?.loadURL(config.url) },
    { label: 'Reload', accelerator: 'CmdOrCtrl+R', click: () => mainWindow?.reload() },
  ];
  if (isBrowserApp) {
    navigation.push({ label: 'Focus address bar', accelerator: 'CmdOrCtrl+L', click: focusBrowserAddressBar });
  }
  navigation.push({ type: 'separator' });
  if (!app.isPackaged) {
    navigation.push({ label: 'Toggle DevTools', accelerator: 'CmdOrCtrl+Shift+I', click: () => mainWindow?.webContents.toggleDevTools() });
  }
  navigation.push({ type: 'separator' }, { role: 'quit' });
  return Menu.buildFromTemplate([{ label: config.title, submenu: navigation }]);
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
