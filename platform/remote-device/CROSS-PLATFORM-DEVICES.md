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

Mobile/tablet agents use the same enrollment identity but platform-appropriate APIs. Android uses the existing ShopnoltdCollect/Android integration path; iPadOS requires a signed native app because browser JavaScript cannot provide unrestricted device administration or screen control.

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
- Android: ShopnoltdCollect APK/AAB
- iPadOS: Xcode project/app target; App Store/TestFlight distribution when Apple signing credentials are configured

Signing credentials remain GitHub Actions secrets and are never committed.
