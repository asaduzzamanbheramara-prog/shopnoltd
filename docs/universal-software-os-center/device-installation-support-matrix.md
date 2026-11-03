# Universal OS and Software Installation Support Matrix

This matrix defines what the Shopnoltd Software & OS Center may safely guide. It distinguishes a **bootable USB installer**, a **USB cable transfer/restore**, and **software stored on a USB drive**. These are not interchangeable.

## Device and operating-system support

| Target | Supported installation/recovery path | Does a pendrive boot/install it directly? | Required constraints |
|---|---|---:|---|
| Windows PC / laptop / workstation | Official Microsoft installation or recovery media | Yes, on supported PCs | Match edition, licence, CPU architecture, UEFI/Legacy mode, Secure Boot, storage and drivers |
| Linux desktop / laptop / server | Official distribution ISO/live image written to USB | Yes, on supported hardware | Match architecture, firmware, Secure Boot, image signature/checksum and hardware support |
| macOS on Intel Mac | Apple-created bootable macOS installer USB; macOS Recovery | Yes, for compatible Mac models | Installer version must support exact Mac; T2/external boot policy may apply |
| macOS on Apple silicon Mac | Apple-created bootable installer USB; built-in macOS Recovery | Yes, for compatible Mac models | Hold power for startup options; model-specific firmware and internet requirements may apply |
| iPhone | Finder on Mac or Apple Devices on Windows; Apple recovery/update workflow | **No** generic bootable pendrive | USB cable connects the phone to a Mac/PC; restore can erase data; Apple Account/Activation Lock still applies |
| iPad | Finder on Mac or Apple Devices on Windows; Apple recovery/update workflow | **No** generic bootable pendrive | USB cable connection and exact Apple restore procedure; backup first |
| Android phone / tablet | Vendor OTA/recovery, supported ADB sideload, or exact-model vendor flashing tool | **Usually no** generic bootable pendrive | Exact model/region/build, signed package, bootloader state and vendor policy; USB cable may be used |
| Google Pixel | Google full OTA sideload or exact-model factory image / Android Flash Tool | **No** generic PC-style pendrive boot | Factory image flashing can erase all user data; use exact model/build |
| Chromebook | Built-in internet recovery or Google USB recovery media | Yes, using a model-specific ChromeOS recovery USB | Recovery erases local data; older/newer models have different recovery paths |
| Raspberry Pi | Raspberry Pi Imager writes OS to microSD or compatible USB/NVMe media; supported models may network-install | Yes, to supported boot media | Boot medium and supported boot mode vary by model; most models commonly use microSD |
| Smart TV / streaming device | Manufacturer recovery menu, signed firmware update, service tool, or OTA | **Model-specific; do not assume** | Exact model, region, board revision and signed firmware are mandatory |
| Router / NAS / embedded device | Manufacturer recovery, documented TFTP/USB/serial/service recovery | **Model-specific; do not assume** | Wrong firmware can brick the device; require exact hardware revision |
| Wearables / consoles / appliances | Manufacturer update/recovery service | **Usually no** generic pendrive OS install | Use documented manufacturer process only |

## Software installation sources and package formats

| Platform | Common package formats / methods | Safe source preference |
|---|---|---|
| Windows | Microsoft Store, WinGet, MSIX/APPX, MSI, EXE | Microsoft Store, WinGet source metadata, publisher's HTTPS site and signed installers |
| macOS | Mac App Store, PKG, DMG, APP/ZIP | Mac App Store or developer's official signed/notarized download |
| Debian / Ubuntu | APT repositories, DEB, Snap, Flatpak, AppImage | Distribution repositories first; then official vendor repository |
| Fedora / RHEL family | DNF repositories, RPM, Flatpak | Distribution repositories first; then official vendor repository |
| Other Linux | Distribution-native package manager, Flatpak, Snap, AppImage, tar archives | Exact distribution and architecture-specific official source |
| Android | Google Play, OEM app store, APK / split APK where explicitly supported | Google Play or publisher's official source; verify signer, package identity and ABI |
| iPhone / iPad | App Store, managed deployment, Apple-supported restore/update | App Store or Apple Business/School Manager where applicable; no generic USB APK/IPA sideload |
| ChromeOS | Google Play where supported, web apps, Linux environment on supported devices | Google Play / Chrome Web Store / publisher sources subject to device policy |

A USB drive can **carry** offline installers and driver packages for many platforms, but the target OS must already be running or have a compatible recovery/installer environment. A file copied to a USB drive is not automatically bootable or installable.

## Shopnoltd catalogue rules

1. Every catalogue record must identify its platform, device class, architecture, package format, publisher, official source, licence note, and verification state.
2. An official landing page must never be presented as a direct binary download.
3. A catalogue entry marked `documented-method-device-dependent` is not proof that Shopnoltd has tested the method on every device.
4. Record verification evidence per release/build. Re-check current publisher hashes/signatures at download time; do not hard-code stale hashes as permanent truth.
5. Do not mirror, repackage, or bundle proprietary installers, firmware, ISO files, APKs, or third-party binaries without explicit redistribution rights.
6. Do not collect licence keys, Apple/Google credentials, device unlock codes, or recovery secrets.
7. Keep browser UI read-only. A future local USB writer must be a separately signed, least-privilege helper with device identity/capacity display, system-disk protection, explicit final confirmation, write progress, cancellation/error handling, flush and post-write verification.
8. Do not describe phone USB sideload, iPhone restore over cable, or a USB containing software files as "booting the device from pendrive".
9. Do not claim universal support. Publish only the exact device/OS/architecture/firmware combinations actually validated.

## Official starting points

- Apple macOS bootable installer: https://support.apple.com/101578
- Apple macOS Recovery (Apple silicon): https://support.apple.com/guide/mac-help/macos-recovery-a-mac-apple-silicon-mchl82829c17/mac
- Apple iPhone/iPad computer restore: https://support.apple.com/en-la/118107
- Android recovery ADB sideload: https://source.android.com/docs/core/ota/nonab/device_code
- Google Pixel factory images: https://developers.google.com/android/images
- Google Pixel full OTA images: https://developers.google.com/android/ota
- Chromebook recovery: https://support.google.com/chromebook/answer/1080595
- Raspberry Pi OS installation and boot media: https://www.raspberrypi.com/documentation/computers/getting-started.html
- Microsoft Windows downloads: https://www.microsoft.com/software-download/
- Fedora Workstation: https://fedoraproject.org/workstation/download
- Debian installation media: https://www.debian.org/distrib/
- FreeBSD downloads: https://www.freebsd.org/where/

## Validation status

This document and catalogue describe official starting points and supported method categories. They do **not** mean Shopnoltd has already downloaded, verified, installed, or physically boot-tested every listed OS or device. The USB writer remains a separate implementation and validation task tracked in issue #447.
