# Shopnoltd Native App Shells

Two directories, both "thin shell" apps that load the real, live
web-portal/admin-portal over HTTPS -- the same architecture Slack/Discord
desktop apps use. Nothing here bundles a copy of the React app; it always
shows whatever is actually deployed.

## Desktop (`apps/desktop-shell/`) -- Windows, Mac, Linux

Electron. One codebase, two configs (`src/configs/web-portal.json` and
`src/configs/admin-portal.json`), selected at build time.

```bash
cd apps/desktop-shell
npm install

# Run locally without packaging
npm start          # loads web-portal
npm run start:admin

# Package installers (run on the matching OS, or use electron-builder's
# Docker image for cross-compiling Windows/Linux from Linux -- macOS
# builds still need a real Mac due to Apple's codesigning requirements)
npm run build:web    # -> release/web-portal/*.exe / *.dmg / *.AppImage / *.deb
npm run build:admin   # -> release/admin-portal/*
```

Security notes baked in: `nodeIntegration: false`, `contextIsolation: true`,
`sandbox: true`, and any link outside `*.shopnoltd.dpdns.org` opens in the
system browser instead of inside the app.

## Mobile (`apps/mobile-shell/`) -- Android, iOS

Capacitor, configured with `server.url` pointing at the live site (see
`configs/web-portal.json` / `configs/admin-portal.json`) rather than a
bundled web build.

```bash
cd apps/mobile-shell
npm install

# Pick a target, then scaffold/sync the native project
node scripts/select-config.js web-portal
npx cap sync

# Android: open in Android Studio, or build from the CLI with the Android
# SDK installed
npx cap open android

# iOS: needs an actual Mac with Xcode + CocoaPods
npx cap open ios
```

The `android/` and `ios/` native projects in this archive were generated
and verified once already (`npx cap add android` / `npx cap add ios` both
succeeded cleanly) -- `applicationId`/bundle ID is `org.shopnoltd.app` (or
`org.shopnoltd.admin` for the admin build).

## Icons

Both shells use `branding/1024 × 1024_Logo_Final.png` as the base icon.
Capacitor apps typically want a full icon/splash set generated per
resolution -- run `npx @capacitor/assets generate` from `apps/mobile-shell`
once you've dropped that source image (already copied to
`apps/mobile-shell/resources/icon.png`) alongside a splash image.

## What this doesn't include

- **VPN management** -- wasn't built. A legitimate version of this (e.g. an
  admin-facing WireGuard config generator/dashboard for your own
  infrastructure) is a separate, scoped feature; ask for it specifically if
  that's still wanted, distinct from the anti-detect-browser bundling
  request I've declined a few times now.
- **Deep linking / custom protocol handlers** (`shopnoltd://...`) -- not
  wired up yet, straightforward to add to both shells if needed.
- **Auto-update** -- Electron (`electron-updater`) and Capacitor
  (App Store/Play Store native updates) both support this; not configured
  yet since it needs a release-hosting endpoint decided first.
