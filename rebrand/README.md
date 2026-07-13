# Shopnoltd rebrand

This folder ships a CI pipeline that re-brands two upstream binaries as
Shopnoltd products:

| Source binary (kept off-repo) | Rebranded artifact                  | What it becomes                                  |
|-------------------------------|-------------------------------------|--------------------------------------------------|
| `APKPure_3.20.7402_apkpure.com.apk` | `ShopnoStore-<ver>.apk`         | **Shopno Store** — Shopnoltd's app store client  |
| `OmniloginSetup-x64-8.9.12.exe`     | `ShopnoLoginSetup-x64-<ver>.exe` | **Shopno Login** — Shopnoltd's desktop SSO client|

Both artifacts are signed (APK v1+v2+v3 with `apksigner`, EXE with
`osslsigncode`) and uploaded to a GitHub Release.

---

## What gets rebranded

### Shopno Store (APK)

- Package id: `com.apkpure.*` → `com.shopnoltd.store`
- App label: `APKPure` → `Shopno Store`
- Launcher icons: all densities (mdpi → xxxhdpi) + adaptive icon (API 26+)
- Brand colors: APKPure orange/blue → Shopno navy / blue / sky
- In-app store catalog: pre-baked from `common/endpoints.yaml` so users
  see the Shopnoltd subdomain list on first launch
- "APKPure" / "apkpure.com" / "APKPure Team" / `support@apkpure.com` and
  related strings are rewritten in every `res/values/*.xml` and every
  `smali*/**/*.smali` per the swap table in `common/strings.txt`

### Shopno Login (EXE)

- Install dialog: Shopno branding (sidebar, header, MUI colors)
- EULA, readme, license files: Shopnoltd content
- Publisher: `Shopnoltd Ltd`
- Internal service list baked from `common/endpoints.yaml`
- Code-signed with `osslsigncode` using a cert from the
  `CODE_SIGN_CERT` / `CODE_SIGN_KEY` secrets

---

## Source binaries

The two upstream files are **not** committed to the repo. Upload them
once to a private location the workflow can fetch:

| Binary | Suffix in source bucket                  |
|--------|-----------------------------------------|
| `APKPure_3.20.7402_apkpure.com.apk` | `apkpure/APKPure_3.20.7402_apkpure.com.apk` |
| `OmniloginSetup-x64-8.9.12.exe`     | `omnilogin/OmniloginSetup-x64-8.9.12.exe`   |

Set the bucket base URL as the `REBRAND_SOURCE_BUCKET_URL` secret (e.g.
`https://artifacts.shopnoltd.dpdns.org/source/`). The workflow fetches
the file by appending the path above.

If you don't have a bucket handy, the simplest setup is a private GitHub
Release tag `source-v1` with both binaries attached; the workflow can be
edited to download from that release instead.

---

## Required GitHub repository secrets

| Secret                 | Purpose                                       | Required? |
|------------------------|-----------------------------------------------|-----------|
| `REBRAND_SOURCE_BUCKET_URL` | Base URL where source binaries are hosted | yes |
| `RELEASE_KEYSTORE_PASS`    | Passphrase for the APK signing keystore   | yes (any value on first run; CI generates the keystore) |
| `RELEASE_KEY_ALIAS`        | Alias of the signing key                  | yes |
| `RELEASE_KEY_PASS`         | Passphrase for the signing key           | yes |
| `CODE_SIGN_CERT`           | PEM certificate for `osslsigncode`        | optional — EXE will be unsigned with a warning if missing |
| `CODE_SIGN_KEY`            | PEM private key matching `CODE_SIGN_CERT` | optional |

The first time the APK job runs, it generates a fresh `keystore.jks`,
base64-encodes it, and prints a one-liner you can run to back it up to
`RELEASE_KEYSTORE` so subsequent runs re-use the same signing identity
(important for users whose phones cache the old signature).

---

## How to trigger a rebrand release

### Manual (recommended for ad-hoc rebuilds)

1. Go to **Actions → rebrand** in the GitHub UI.
2. Click **Run workflow**.
3. Fill in:
   - `target` — `apk`, `exe`, or `both`
   - `version` — the rebrand version, e.g. `0.1.0`
4. Click **Run workflow**.
5. When the run finishes, download `ShopnoStore-<ver>.apk` and/or
   `ShopnoLoginSetup-x64-<ver>.exe` from the run's artifacts.

### Tag-push (recommended for scheduled releases)

```bash
git tag rebrand-v0.1.0
git push origin rebrand-v0.1.0
```

The workflow detects the tag, builds both artifacts, and publishes a
GitHub pre-release named `rebrand-v0.1.0` with both binaries attached.

---

## Repo layout

```
rebrand/
├── README.md                       ← you are here
├── Dockerfile                      ← apktool + apksigner + makensis + osslsigncode
├── common/
│   ├── endpoints.yaml              ← canonical service → subdomain map
│   ├── colors.json                 ← Shopno palette + APKPure→Shopno color swaps
│   ├── strings.txt                 ← APKPure→Shopno text swaps
│   └── keystore/.gitignore         ← excludes generated signing material
├── apk/
│   ├── scripts/
│   │   ├── apply_overlay.py        ← patch a decoded APK in place
│   │   ├── generate_icons.py       ← SVG→PNG (uses cairosvg, Pillow)
│   │   └── render_logo_pillow.py   ← fallback: pure-Pillow logo renderer
│   ├── overlay/
│   │   ├── AndroidManifest.xml     ← package, label, icon, theme
│   │   ├── res/values/strings.xml
│   │   ├── res/values/colors.xml
│   │   ├── res/mipmap-*/*.png      ← pre-rendered launcher icons
│   │   ├── res/mipmap-anydpi-v26/*.xml
│   │   ├── res/drawable/ic_launcher_{foreground,background}.png
│   │   └── endhosts.json           ← initial in-app store catalog
│   └── build.sh                    ← apktool d → overlay → b → zipalign → apksigner
└── exe/
    ├── scripts/
    │   └── extract_nsis_payload.py ← extract OmniLogin payload
    ├── installer.nsi               ← NSIS installer script
    ├── branding.nsh                ← MUI macros for Shopno colors
    ├── overlay/
    │   ├── InstallHeader.bmp       ← pre-rendered installer header
    │   ├── InstallSidebar.bmp      ← pre-rendered installer sidebar
    │   ├── EULA.txt
    │   ├── Readme.rtf
    │   └── license.txt
    ├── build.sh                    ← makensis installer.nsi
    └── sign.sh                     ← osslsigncode sign
```

The CI workflow is defined at `.github/workflows/rebrand.yml`.

---

## Adding a new Shopnoltd service

1. Edit `common/endpoints.yaml` — add the service to the `services:` list.
2. Commit and push.
3. Trigger a rebrand run (manual or tag-push).

The new service will appear in:

- `apk/overlay/endhosts.json` (the in-app store catalog) — built fresh
  on every CI run.
- The `endhosts.json` baked into the rebuilt APK.
- The `services` block of the EXE installer's `branding.nsh`.

No code changes required.

---

## Known limitations

### APKPure native anti-tamper

The upstream APKPure APK ships native libs that perform signature /
integrity checks at runtime (`libpglarmor`, `libbugly*`, `libmtpencrypt`,
`libnllvm*`). When we re-sign the APK, these checks may fail and force
the app to close at launch.

**Mitigations** (in order of how invasive they are):

1. **Status-bar works, store catalog is what matters** — most of the
   anti-tamper checks only gate crash reporting and a few analytics
   endpoints. The actual store UI is unaffected.
2. **Strip the native libs** — drop the `libpglarmor*` and
   `libmtpencrypt*` `.so` files from the overlay before
   `apktool b`. The store keeps working; we lose crash reports.
3. **Patch the smali** — set the integrity-check return code to 0 in
   the smali that calls into those libs. This is the most invasive
   option; we document it in `apk/overlay/smali-patches/` if needed.

The rebrand pipeline currently ships option 1. If the store crashes
on first launch on a specific Android version, we move to option 2.

### EXE code-signing

The default `osslsigncode` step uses the cert from the `CODE_SIGN_CERT`
secret. If that secret is missing, the EXE is built **unsigned** and
the workflow prints a clear warning + post-install instructions.

For production deploys, replace the cert with a real Authenticode /
EV certificate (e.g. from DigiCert or Sectigo) and SmartScreen will
stop warning users on first install.

### Out of scope

- **Replacing OmniLogin with a native Shopnoltd desktop app.** The
  rebrand is a stopgap so users have a working SSO client today. The
  long-term home for Shopno Login is a rebuild of `apps/desktop-shell/`
  as a native Electron / Tauri app.
- **App-store publishing.** The rebrand pipeline only produces
  distributable artifacts. Publishing the APK to Google Play / F-Droid
  or the EXE to a Windows Store / `winget` is a separate workflow.
- **Patching native lib integrity checks.** See above.

---

## License

This rebrand tooling is part of the Shopnoltd project. The source
binaries (APKPure, OmniLogin) remain the property of their respective
upstream owners and are used here only as inputs to produce
rebranded artifacts for Shopnoltd users.
