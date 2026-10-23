# Bootable USB / Pendrive Recovery System

## Product requirement

The Universal Software & OS Recovery Center must include a guided bootable USB workflow for supported devices. This is a planned capability, not a claim that the current web page can already write a pendrive or repair a machine.

A bootable USB is normally created on a working computer and then used to start the target computer. If the target device cannot boot, the workflow must explain that a second working device, a pre-existing recovery environment, or a supported network-boot setup is needed.

## Initial supported workflow

1. Identify the target device model, operating system, CPU architecture, firmware mode (UEFI/legacy BIOS), Secure Boot state, and intended recovery goal.
2. Recommend only an official OS/recovery image and a compatible tool for the user's working OS. Clearly distinguish an official download page from a direct image download.
3. Verify the downloaded image against a publisher-provided checksum or signature when available. A checksum proves equality to the supplied digest, not that the digest itself came from a trustworthy source.
4. Explain the selected USB-writing tool and show the exact target drive identity/capacity before writing.
5. Require an explicit, separate confirmation immediately before any destructive write. Warn that creating boot media usually erases all data on the selected USB drive. Never infer the target drive automatically.
6. Explain how to open the device's one-time boot menu, select the USB, and troubleshoot UEFI/Secure Boot/architecture mismatch.
7. Offer a recovery-specific path: startup repair, live environment, backup/data rescue, OS reinstall, or vendor recovery. Warn users to back up data before repair/reinstall and distinguish data-preserving actions from destructive actions.
8. After use, explain how to restore the USB to ordinary storage if desired.

## Initial image/tool categories

- Official Windows installation or recovery media, subject to Microsoft's current supported creation process and licensing.
- Official Linux distribution live/install images and publisher-supported USB-writing instructions.
- Vendor-specific recovery images for exact supported models.
- Trusted rescue environments only after source, licence, signature/checksum and maintenance status have been reviewed.

Do not redistribute proprietary ISO files or bundle third-party binaries without licensing approval. Prefer linking to official publisher instructions and downloads.

## Compatibility checks

Track at least: device manufacturer/model; target OS and version; x86/x64/ARM architecture; UEFI/legacy boot; Secure Boot requirements; partition scheme/filesystem requirements; minimum USB capacity; image verification status; and known limitations. Never describe one image as universal across all devices.

Android phones/tablets, iOS/iPadOS devices, TVs, wearables and embedded hardware do not generally use the same PC bootable-USB workflow. For those device families, provide only documented vendor-supported recovery methods. USB OTG or service/recovery modes must not be assumed to support OS installation.

## Safety and implementation boundaries

- The current catalogue and checksum checker are metadata/read-only tools; they do not write a USB drive.
- A future USB writer must be a separately reviewed local helper, not a browser page issuing arbitrary disk commands.
- The helper should use least privilege, display the physical device and size, refuse ambiguous targets, verify image integrity, report progress, and verify the written media where technically possible.
- Require a final destructive-action confirmation after the target device is selected; provide no unattended disk formatting or silent overwrite.
- Do not run downloaded images or installers as part of checksum verification.
- Log only the minimum diagnostic details needed; do not upload disk identifiers or file contents by default.
- Test the writer and recovery images in disposable VMs and on documented test hardware before advertising support. A VM boot test alone does not prove compatibility with all physical devices.
- Keep recovery media generation, privileged writing, and actual OS repair out of the web frontend.

## Release acceptance checklist

- [ ] Official source and licence/distribution terms reviewed.
- [ ] Publisher checksum/signature verification path documented and tested.
- [ ] Device/OS/architecture/firmware compatibility stated.
- [ ] USB target is selected explicitly and independently re-confirmed.
- [ ] Destructive-write warning and backup guidance shown before writing.
- [ ] Interrupted-write/error handling and post-write verification tested.
- [ ] VM boot tests pass for each claimed image/architecture; physical-device limits documented.
- [ ] Recovery steps distinguish non-destructive repair from data-erasing reinstall.
- [ ] No claim of universal compatibility; unsupported devices receive an honest limitation message.

## Available non-destructive planner prototype

The repository now includes a command-line checklist generator at
`tools/software-os-diagnostics/recovery_media_plan.py`. It accepts the target OS,
architecture, firmware mode, Secure Boot state, recovery goal, USB capacity, and
whether image verification has already been completed. It emits JSON with safety
checks and warnings. It does not detect physical drives, download images, or write
to a USB. When `--image-verified` is omitted, the CLI returns exit code 2 and marks
the plan blocked pending verification.

Example (planning only; no disk is modified):

```sh
python tools/software-os-diagnostics/recovery_media_plan.py \
  --target-os linux --architecture x86_64 --firmware uefi \
  --secure-boot unknown --goal rescue-data --usb-capacity-gib 16
```

Automated regression tests are in
`tests/software-os-diagnostics/test_recovery_media_plan.py`. Passing these tests
validates checklist logic only; it does not prove that a USB writer or bootable
recovery image exists. Physical USB writing remains intentionally unimplemented
until a separately reviewed, least-privilege local helper and destructive-action
test plan are available.
