# Shopnoltd Cross-Platform Device Cloud

Shopnoltd Remote Devices supports one device-control protocol across desktop and mobile form factors.

## Supported device families

- Windows desktop/laptop
- Linux desktop/laptop/server
- macOS desktop/laptop
- Android phone and Android tablet
- iPadOS tablet (native agent/app integration point)

## Architecture

All devices use the same gateway, enrollment, heartbeat, job, result, ownership and authorization model. The agent reports a normalized platform value and device capabilities. The browser UI presents one device inventory rather than separate products.

Desktop agents are outbound-only and execute a fixed allowlist of safe operations. They must never expose an inbound shell or arbitrary command endpoint.

Android can use the experimental Termux-based lightweight executor for outbound heartbeat, device/network inventory and the fixed diagnostics allowlist. It is not a native remote-control agent and does not capture or control the Android screen; Android background execution is subject to Termux setup and battery-optimization settings. iPadOS requires a signed native app because browser JavaScript cannot provide unrestricted device administration or screen control.

## Capability levels

1. **Inventory** — OS, device model, architecture, health, connectivity.
2. **Managed diagnostics** — disk, memory, network and approved Shopnoltd diagnostics.
3. **Application integration** — ShopnoltdCollect, browser/deep-link launch and approved app actions.
4. **Interactive screen** — only where the platform and user-granted accessibility/screen-capture APIs permit it.

The control plane must advertise capabilities instead of pretending every platform has identical APIs.

## Security requirements

- OIDC/Keycloak user authentication at the control plane.
- Per-device enrollment token, then per-agent credential.
- HMAC request authentication for desktop executor traffic.
- Timestamp/nonce replay protection.
- Owner/admin authorization on every device action.
- Fixed operation allowlist; no arbitrary shell execution.
- Secrets stored in OS-appropriate secure storage where available.
- Device revocation immediately invalidates its runtime credential.

## Installer targets

The repository should publish platform-specific packages from CI:

- Windows: MSI/EXE installer
- Linux: DEB, RPM and portable tarball/AppImage where practical
- macOS: signed/notarized DMG when Apple signing credentials are configured
- Android: experimental Termux executor bootstrap for lightweight heartbeat/diagnostics; a native signed APK/AAB is still required for full background service and screen capabilities
- iPadOS: Xcode project/app target; App Store/TestFlight distribution when Apple signing credentials are configured

Signing credentials remain GitHub Actions secrets and are never committed.
