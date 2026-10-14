# Shopnoltd Universal Software & OS Center

## Goal

Add a discoverable Software & OS Center to Shopnoltd without replacing the current website, authentication, billing, gateway, or GitOps deployment architecture.

This first increment is architecture and catalogue scaffolding only. It does not expose privileged repair APIs, modify production, charge customers, or claim that a device has been repaired.

## Two operating modes

### 1. Online mode (no USB required when the OS is running)

- Browse a curated catalogue of operating systems, applications, drivers, and recovery utilities.
- Link to official vendor downloads and publish installation instructions.
- Show supported operating systems, architecture, licensing notes, version, and verification metadata.
- Provide guided installation recipes for supported desktop-helper workflows.
- Gate paid features through the existing Shopnoltd server-side billing/entitlement system only after its integration is reviewed.

### 2. Offline recovery mode (for a PC that cannot boot)

- Build a bootable recovery image from versioned, reviewed source and configuration.
- Offer instructions to create a bootable USB from another working computer.
- Where supported and already configured, document network/PXE boot as an alternative.
- Provide diagnostics, backup-first workflows, and OS installation options.
- Never promise USB-free recovery for a device with no working boot environment or configured network boot.

## Repository responsibilities

- Keep source code, manifests, build recipes, tests, and documentation in GitHub.
- Prefer vendor-owned official download URLs for large installers/ISO images rather than committing large binary payloads.
- Record checksums/signature-verification instructions only when they are sourced from a trusted release publisher.
- Keep payment credentials, signing private keys, and other secrets in the existing secret-management system, never in this public repository.
- Treat every downloaded executable and recovery image as untrusted until its signature/checksum and source are verified.

## Safety requirements

- No silent disk writes, partition changes, bootloader changes, formatting, or OS reinstall.
- Before destructive actions: show the target disk/device, explain data-loss risk, require explicit confirmation, and recommend a backup.
- Default to read-only diagnostics.
- Do not run arbitrary shell commands supplied by catalogue content.
- Desktop helper commands must be allow-listed, signed/released, least-privilege, and auditable.
- Do not allow a web page to obtain unrestricted administrator/root execution.
- Do not mark paid entitlement from a browser-only flag; verify entitlement on the server.
- Keep logs free of payment secrets, tokens, and unnecessary personal data.

## Proposed incremental delivery

1. Catalogue schema and reviewed sample entries.
2. Read-only catalogue API/UI integrated into the existing app after frontend architecture is confirmed.
3. Billing entitlement integration using existing server-side billing, with tests and demo/live status handled honestly.
4. Desktop helper prototype for non-destructive diagnostics and explicitly approved tasks.
5. Reproducible recovery-image build pipeline and documented USB creation workflow.
6. Security review, automated tests, staging validation, then production deployment through existing GitOps.

## Not in this scaffold

- No production deployment.
- No direct billing-engine modifications.
- No bootable image binary.
- No unreviewed OS redistribution.
- No privileged repair execution.
