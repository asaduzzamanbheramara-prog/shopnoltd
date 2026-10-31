# Realme / Termux static-site origin (staging)

This directory provides an **optional staging origin** for the already-built
Shopnoltd web portal. It does not move the production domain, API, identity
provider, database, Kubernetes control plane, or any other backend to Android.

## Architecture and safety

- Build the Vite application on the PC or in CI; do not compile it on the phone.
- Copy the resulting `platform/web-portal/dist/` directory to the phone.
- Termux Nginx serves the files on `127.0.0.1:8080` only.
- The loopback-only listener is intentional. Do not change it to
  `0.0.0.0` and do not open router/firewall ports for this service.
- Public access, if later approved, must use an authenticated outbound tunnel
  with access controls. Never tunnel ADB, SSH, Termux shell, or database ports.
- The app continues to call its configured HTTPS API and Keycloak endpoints.
  This static origin does not proxy or replace those services.
- The existing PC/Kubernetes origin remains the production source of truth and
  fallback until a separate acceptance and cutover decision.

## Phone prerequisites

1. Install Termux from its official F-Droid or GitHub distribution. Avoid
   mixing Termux and add-on apps from different signing sources.
2. Open Termux and run:
   ```sh
   pkg update
   pkg install nginx curl
   ```
3. Copy the complete `platform/web-portal/android-hosting/` folder into
   Termux's home directory, preserving the `nginx.conf` and executable
   `termux-site.sh` files.
4. Grant Android shared-storage permission only if you plan to stage the build
   through Downloads: run `termux-setup-storage` and approve the Android prompt.

## Build and transfer from the PC

From the repository root on the PC (or CI), build the normal production bundle:

```sh
cd platform/web-portal
npm ci
npm run build
```

Transfer the complete `dist` directory to the phone's shared Downloads folder
using your existing trusted USB/Wireless ADB connection. Example from the PC:

```sh
adb push dist /sdcard/Download/shopnoltd-dist
```

Do not transfer ADB keys or pairing data. Do not expose the ADB transport to
the internet.

## Deploy inside Termux

Assuming the helper folder was copied to `~/shopnoltd-android-hosting`:

```sh
chmod 700 ~/shopnoltd-android-hosting/termux-site.sh
~/shopnoltd-android-hosting/termux-site.sh deploy ~/storage/downloads/shopnoltd-dist
```

If you copied the build elsewhere, pass that actual directory instead. The
script validates `index.html`, stages a versioned release, switches the
active symlink only after copying, validates Nginx configuration, starts the
server, and checks `/healthz`.

Open the site locally on the phone at:

```
http://127.0.0.1:8080/
```

Useful commands:

```sh
~/shopnoltd-android-hosting/termux-site.sh status
~/shopnoltd-android-hosting/termux-site.sh start
~/shopnoltd-android-hosting/termux-site.sh stop
```

The helper never deletes old releases automatically. Review storage before
manual cleanup.

## Important limitations

Android may stop background processes under battery and background-execution
policies. Keep the first test interactive with Termux open and the phone
charging. Do not rely on this as a production origin yet. Termux:Boot,
wake locks, tunnel startup, restart supervision, thermal/battery behavior,
and long-duration availability require separate phone-side tests.

## Acceptance gates before any public cutover

- Build artifact integrity and route smoke tests pass.
- Home page, all prerendered public routes, static assets, refresh/deep links,
  and browser console are checked on the phone.
- Sign-in, API calls, OAuth redirects, CORS, cookies, and payment flows are
  verified against the existing production services.
- AdSense/Adsterra behavior is checked; do not assume ad-network policy or
  verification remains valid when the origin changes.
- Tunnel access is authenticated and only the website origin is exposed.
- Phone reboot, Wi-Fi loss/reconnect, Android process termination, battery
  saver, and multi-hour uptime are tested.
- A tested rollback to the existing PC origin is documented.

No DNS, Cloudflare/Tunnel, Kubernetes, production ingress, or PC workload
changes are performed by this staging setup.
