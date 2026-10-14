# Device and package coverage roadmap

## Product requirement

The catalogue and tooling should accept software metadata for any device/OS/package family that can be supported safely. “Any device” means broad discovery and explicit compatibility checks—not a promise that one installer can run everywhere.

## Required metadata per entry

- Target OS/platform and supported versions where known.
- Device class (desktop, laptop, phone, tablet, TV, wearable, server, embedded, etc.).
- CPU architecture/ABI where relevant.
- Package format and whether the source is an official page, release, repository, or documentation.
- Publisher, licence note, compatibility evidence, and verification status.
- Installation route and recovery/removal guidance where appropriate.

## Platform-specific guardrails

- Windows/macOS/Linux/BSD/ChromeOS: use publisher-supplied packages and supported package managers.
- Android: APK support must include publisher/source, Android minimum version, ABI, signing verification, and clear sideloading consent. APKS/XAPK may need a trusted installer; AAB is not generally a direct end-user install package.
- iOS/iPadOS/watchOS/tvOS: direct installation is constrained by Apple signing and approved distribution mechanisms. Link to the official store/publisher path; never promise generic sideloading.
- Web apps: use HTTPS and browser security boundaries; no claim of native device installation.
- Firmware, drivers, bootloaders and recovery images: exact model matching, signed artifacts, backups and explicit confirmation are mandatory.
- Unknown or unsupported platform: label “not yet supported” rather than inventing compatibility.

## Delivery phases

1. Extend the catalogue schema and test package/platform coverage.
2. Add official-source entries incrementally, each with publisher evidence and honest verification status.
3. Make the UI filter by OS, device type, architecture and package format.
4. Add read-only device detection in the local helper, with user consent and no upload by default.
5. Add platform-specific install flows only after signed releases, least privilege, rollback and tests exist.
6. Build and test recovery media for supported architectures; maintain a compatibility matrix instead of claiming universal boot.

The current PR is a foundation. This roadmap does not mean every platform or installer is already implemented.
