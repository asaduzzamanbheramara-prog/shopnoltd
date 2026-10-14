# Offline recovery for a non-bootable PC

A browser website cannot run on a computer that cannot boot into an operating system. Shopnoltd must provide a recovery path that starts independently of the installed OS.

## Supported entry paths

1. **Bootable USB (baseline):** on a working computer, download a reviewed Shopnoltd recovery image/build artifact and write it to a USB using a documented, supported writer. Boot the target PC from that USB.
2. **Network/PXE boot (optional):** only for devices and networks where firmware, DHCP/TFTP/HTTP boot infrastructure, and configuration are already supported. This is not universally available and may require administrator access to the network.
3. **Built-in recovery:** when the device vendor/OS provides a functioning recovery environment, link to the vendor's documented workflow.

## Minimum recovery workflow

1. Identify the device model, firmware mode (UEFI/legacy), CPU architecture, storage layout, and intended OS.
2. Prefer read-only hardware/storage diagnostics first.
3. Show the user which disk will be affected and whether the operation can erase data.
4. Offer backup/recovery options before any write operation.
5. Verify image signatures/checksums against publisher-controlled evidence.
6. Require explicit confirmation immediately before partition, format, bootloader, or OS-install operations.
7. Log operation outcomes without collecting unnecessary personal data or secrets.

## Image-build pipeline requirements

- Pin base images and dependencies to reviewed versions.
- Build in CI from version-controlled recipes; do not commit generated ISO/USB images to the source tree.
- Generate checksums and publish release provenance.
- Scan dependencies and keep a software bill of materials (SBOM).
- Sign releases with a protected key stored outside the public repository.
- Test boot in virtual machines before offering an image; test representative physical hardware before claiming hardware support.
- Publish known limitations and supported architectures.

## Important limits

- A USB is not required if a working recovery partition or configured network boot path exists, but one is the most practical general-purpose recovery option.
- Recovery images and OS installers are subject to vendor licences and redistribution restrictions.
- A recovery image cannot guarantee repair of failed hardware, encrypted disks without recovery keys, unsupported firmware, or every PC model.
