# Device-specific recovery profiles: Shopnoltd reference devices

This document records read-only observations from the user's PC and Android phone and maps them to safe online/offline recovery paths. It does not authorize a reset, firmware flash, disk format, USB write, or data deletion.

## 1. Windows PC reference device

### Observed hardware and OS
- Manufacturer/model family: HP Laptop 14s-cf2xxx (exact HP product number still required).
- OS: Windows 11 Home Single Language, 64-bit, build 26200.
- RAM: approximately 16 GB.
- Internal system storage: WD PC SN810 256 GB NVMe, GPT.
- Windows Recovery Environment: enabled.
- C: volume: fully decrypted; BitLocker protection is off.
- The currently connected 120 GB USB is the existing E2B multiboot drive, not a blank recovery target:
  - Disk 1, USB, 125,829,120,000 bytes, MBR.
  - D: E2B NTFS partition, about 125.1 GB, about 110.9 GB free at inspection.
  - E: E2B_PTN2 FAT32 partition, about 711 MB.
- **Preservation rule:** do not format, repartition, overwrite, or run a USB installer against this E2B disk. It contains existing boot infrastructure and must remain intact.

### Online recovery path
1. Use Windows Settings > System > Recovery while Windows is bootable.
2. For startup issues, use Windows Recovery Environment and try Startup Repair / System Restore / uninstall updates before reinstalling.
3. Obtain Windows installation media only from Microsoft's official download page.
4. Obtain drivers only from HP's support portal after confirming the exact product number/serial family locally; never guess drivers from the family name alone.
5. Back up user files and verify the encrypted recovery vault before any Reset this PC or clean installation.

### Offline / pendrive path
1. On a working PC, prepare Windows recovery/install media from Microsoft's official workflow.
2. Prefer a separate blank USB for destructive media creation. Do not use the existing E2B drive until the user explicitly approves a specific non-destructive E2B-compatible copy operation and a backup of its boot files is verified.
3. A compatible ISO may be stored as a file on an E2B data partition only if the E2B configuration and available space are confirmed; copying an ISO is not the same as writing/formatting a USB.
4. Before booting, confirm UEFI mode, Secure Boot compatibility, target disk identity, and backup status.
5. The 256 GB internal NVMe is the system disk and must never be selected as the USB writer target.

## 2. Android phone reference device

### Observed hardware and OS
- Manufacturer/model: realme C35, model RMX3511.
- Device codename: RE87BAL1; board: ums9230_nico.
- OS: Android 13 / API 33.
- Build: RMX3511PU_13.F.89.
- Security patch: 2025-05-01.
- ADB reports slot _a, flash locked, verified boot state green.
- Internal storage: about 47 GB total, 23 GB used, 24 GB available at inspection.

### Online recovery path
1. While Android runs, back up personal files and verify app-specific backups. WhatsApp Business needs its own in-app backup check; do not assume generic Android backup includes its chat database.
2. Check Settings > About device / Software update for an OTA offered to this exact device and region.
3. Follow realme's official Recovery Mode instructions only when needed. realme's general support guide documents Power + Volume Down after power-off, then Install from storage when a compatible official package is available.
4. Ask realme Bangladesh support to confirm the exact RMX3511 regional build and official recovery package before any manual firmware installation.
5. If recovery mode cannot update/repair the phone, use an authorized realme service center rather than a guessed third-party flash package.

### Offline / USB path
- A generic Windows/Linux bootable pendrive does not boot this Android phone.
- The practical offline media role is to carry backed-up personal files or a vendor-confirmed official update package, where the phone's recovery supports that package and exact build.
- A PC-assisted USB cable workflow is a separate device/vendor-specific process; ADB sideload is available only if the exact recovery explicitly exposes Apply update from ADB.
- Do not unlock the bootloader, erase data, use fastboot flashing, or install a third-party ROM as part of this profile.

## 3. Official support links
- Microsoft recovery options: https://support.microsoft.com/en-us/windows/recovery-options-in-windows-31ce2444-7de3-818c-d626-e3b5a3024da5
- Microsoft Windows downloads: https://www.microsoft.com/software-download/
- HP support: https://support.hp.com/us-en
- realme Bangladesh support: https://www.realme.com/bd/support
- realme software update portal: https://www.realme.com/bd/support/software-update
- realme Recovery Mode guidance: https://www.realme.com/global/support/troubleshooting

## 4. Validation boundaries
- These are read-only inventory observations and safe recovery plans, not successful restore tests.
- No OS reinstall, reset, factory wipe, firmware flash, USB format/write, or production deployment was performed.
- The existing E2B pendrive is preserved.
- The exact HP product number and the realme regional firmware authorization remain unresolved prerequisites.
