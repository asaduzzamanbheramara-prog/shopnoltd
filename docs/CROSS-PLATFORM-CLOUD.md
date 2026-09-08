# Shopnoltd Cross-Platform Cloud

Shopnoltd Cloud is a single authenticated device-management and remote-session plane for Windows, Linux, macOS, Android phones/tablets, and iPhone/iPad.

## Supported targets

| Target | Client | Cloud capability | Notes |
|---|---|---|---|
| Windows | Shopnoltd Remote Device Agent | Remote desktop, heartbeat, reconnect, diagnostics | Outbound-only agent |
| Linux | Shopnoltd Remote Device Agent | Remote desktop, heartbeat, reconnect, diagnostics | Outbound-only agent |
| macOS | Shopnoltd Remote Device Agent | Remote desktop, heartbeat, reconnect, diagnostics | macOS permissions are required |
| Android phone | ShopnoltdCollect / mobile shell | Mobile app access and Android Cloud integration | Device capabilities depend on Android permissions |
| Android tablet | ShopnoltdCollect / mobile shell | Same Android capability model, tablet-responsive UI | Same Android package can run on phones/tablets |
| iPhone | Shopnoltd mobile shell | Web/app access and supported device-cloud capabilities | iOS sandbox applies |
| iPad | Shopnoltd mobile shell | Web/app access and supported device-cloud capabilities | iPadOS sandbox applies |
| Browser | Shopnoltd Cloud console | Inventory, enrollment, authorization, sessions | No native installation required |

## Shared architecture

All platforms use the same Shopnoltd identity and device control plane:

1. Keycloak/OIDC authenticates the user.
2. The device is registered against the authenticated account.
3. A one-time enrollment token binds an authorized device agent/app to that registration.
4. The device maintains an authenticated outbound connection and heartbeat where a native agent is supported.
5. The gateway checks ownership and authorization before allocating a session.
6. Browser sessions use the Shopnoltd gateway and Guacamole/guacd where the platform supports remote desktop transport.
7. Audit events record enrollment, connection, disconnection, authorization failures, and device removal.

## Platform rules

- Windows, Linux, and macOS agents must never expose an inbound public port.
- Android, iOS, and iPadOS must use platform-approved APIs and permissions; the system must not claim capabilities the OS does not provide.
- Android phones and tablets share the Android client but report their device form factor accurately.
- iPhone and iPad use the iOS/iPadOS native target because Apple platform restrictions differ from Android.
- Desktop installers are generated independently for Windows, macOS, and Linux.
- Release signing credentials are supplied only through CI secrets; no signing material belongs in Git.
- The web console remains the common control surface even when a native client is unavailable.

## Build outputs

Desktop:

- Windows: NSIS installer (`.exe`)
- macOS: DMG (`.dmg`)
- Linux: AppImage and Debian package (`.AppImage`, `.deb`)

Mobile:

- Android: Gradle/Capacitor application for phones and tablets
- iOS/iPadOS: Xcode/Capacitor application for iPhone and iPad

Apple distribution signing requires Apple-managed credentials. GitHub Actions validates the iOS/iPadOS project without signing; production distribution signing must be configured separately through protected CI secrets.

## Capability truth

"Supported" means the control plane, client architecture, build pipeline, and authorization model exist. A platform is only marked production-ready after runtime enrollment, authentication, connection, and capability-specific end-to-end tests pass. Unsupported OS capabilities must be shown as unavailable instead of simulated.
