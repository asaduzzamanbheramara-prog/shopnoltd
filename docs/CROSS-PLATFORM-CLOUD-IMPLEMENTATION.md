# Cross-platform implementation checklist

This checklist tracks the native application and cloud-device targets without treating unsupported operating-system capabilities as successful.

- [x] Windows desktop packaging target
- [x] Linux desktop packaging targets
- [x] macOS desktop packaging target
- [x] Android phone/tablet mobile target
- [x] iPhone/iPad iOS target
- [x] Shared OIDC identity architecture
- [x] Shared remote-device enrollment architecture
- [x] GitHub Actions matrix for desktop builds
- [x] GitHub Actions Android build validation
- [x] GitHub Actions iOS/iPadOS simulator build validation
- [ ] Production runtime enrollment E2E on every target
- [ ] Production remote-session E2E on every target where OS APIs permit it
- [ ] Apple distribution signing and App Store/TestFlight release
- [ ] Windows/macOS/Linux signed production installers

The remaining unchecked items require real platform devices, platform permissions, or protected signing/distribution credentials. They must not be represented as complete by source-code presence alone.
