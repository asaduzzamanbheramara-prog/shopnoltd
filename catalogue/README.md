# Software & OS catalogue

Catalogue entries are metadata, not executable scripts. Keep entries reviewed, versioned, and testable. The catalogue is designed to cover many device families and software package formats; coverage is data-driven and does not imply every item runs on every device.

## Device and OS coverage model

- Desktop/laptop/workstation: Windows, Linux distributions, macOS, ChromeOS and supported BSD systems.
- Mobile/tablet: Android APK and compatible package variants; iOS/iPadOS apps only through official publisher/store distribution and supported Apple installation paths.
- TV, wearable, embedded and single-board devices: include only when the publisher provides a supported build and install route.
- Server, virtual machine, browser/web app, containers, firmware and recovery tools: distinct targets with their own compatibility and safety rules.

## Package formats represented by the schema

Windows installers (exe, msi, msix, appx); macOS packages (dmg, pkg); Linux formats (deb, rpm, appimage, flatpak, snap); Android (apk, apks, xapk, aab); Apple mobile (ipa); archives and images (zip, tar, iso, img, bin); plus source, web app, container, firmware and other publisher-defined formats.

Listing a format is not permission to install it. AAB files, for example, are normally store/release inputs rather than directly installable APKs; iOS apps generally require Apple's signed distribution paths; firmware updates require exact device-model matching.

## Rules

- Use official vendor/project download pages wherever possible.
- Do not hotlink unofficial mirrors or redistribute software unless its licence explicitly permits it.
- Include supported platforms, device types and CPU architectures when known.
- Record package format separately from the target OS and architecture.
- Prefer vendor signatures and published checksums. A checksum copied from the same untrusted mirror is not sufficient.
- Distinguish an official download page from a direct binary URL.
- Do not advertise a package as compatible until the support claim has a source.
- Paid catalogue access is not a substitute for the software's own licence.
- For APKs, verify publisher identity, package signing, Android version and CPU ABI; do not silently enable unknown-source installation.
- For Apple platforms, do not claim arbitrary IPA sideloading is supported; respect signing, store, device-management and developer-program requirements.
- For firmware, boot media, drivers and recovery images, require exact model/version targeting and explicit confirmation before any write.

See schema/software-entry.schema.json and entries/ for the metadata contract and reviewed examples.
