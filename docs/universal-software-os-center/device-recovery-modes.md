# Device Recovery Modes and Data-Preservation Policy

## Purpose

Provide a consistent, honest recovery workflow for Windows PCs, Android phones, and removable recovery media. A website can guide a user and track a checklist; it cannot itself guarantee a device is backed up, repaired, reset, or bootable.

## Recovery modes

### Mode A — OS-only recovery (default)

- Start with read-only device inventory and health checks.
- Explain that reinstalling/resetting the OS can remove apps, local files, device settings, authentication sessions, and encryption keys.
- Preserve the source device until the selected recovery media and required data have been checked.
- Offer vendor-supported repair/reset methods appropriate to the exact model and OS.
- Do not require a full personal-file backup when the user explicitly chooses OS-only recovery, but clearly identify what will not be preserved.
- Never automatically erase, repartition, format, flash, unregister a virtual disk, or compact/repair a virtual disk.

### Mode B — Essential Shopnoltd recovery backup (optional for user data, mandatory before wiping a host that may contain production state)

- Preserve production database backups and the Kubernetes/application secrets/configuration needed for disaster recovery, encrypted at rest.
- Keep credentials, private keys, tokens, and plaintext secret exports out of public repositories and unencrypted removable media.
- Record backup source, timestamp, size, encryption status, and digest in a manifest that does not disclose secret values.
- Verify that each expected file exists and that its digest matches a trusted manifest. A matching hash does not prove decryption or restoreability.
- Where feasible, separately test decryption and restore into an isolated, disposable environment. Do not test by overwriting production.
- Do not delete or overwrite the source or prior known-good backups until the replacement is verified and cleanup is explicitly approved.
- If the host contains the only copy of a production database, secrets, signing material, or a virtual disk that may contain them, block destructive reset until the required recovery set is safely preserved and verified.

### Mode C — Full personal backup (optional)

- Offer a separate opt-in for user files, photos, downloads, and app-exportable data.
- Report source coverage and skipped/online-only files; do not equate a file count or copied byte total with a complete backup.
- Explain that some app-private Android data cannot be copied with ordinary shared-storage access.
- Do not silently upload personal files to GitHub, cloud storage, or the website.

## Windows PC safeguards

- Inventory physical disks, volumes, free space, recovery environment, and relevant virtual disks using read-only checks first.
- If the system volume is nearly full, stop writes that could destabilize Windows and do not attempt a reset or an in-place media build that requires unavailable space.
- Prefer an independently verified recovery medium and external backup destination; do not use a disk that contains the only source copy as the target.
- Never compact, repair, unregister, move, or delete a WSL virtual disk as a space-saving shortcut before its contents are preserved and validated.
- Before any wipe, show the exact model, disk number, capacity, and volume layout, and require a separate confirmation for that exact target.

## Android safeguards

- Identify the exact manufacturer/model/build and use only documented vendor-supported recovery instructions.
- Distinguish shared-storage copies, Android Backup Manager/cloud backup, app-specific backups, and a verified restore set; these are not interchangeable.
- ADB visibility, an enabled backup manager, a copied WhatsApp database, or a successful file hash alone does not prove a full phone backup.
- Before factory reset or flashing, verify the user's access to the Google account, screen lock, authenticator/MFA recovery, and any app-specific restore credentials.
- Never imply that a generic PC bootable USB can reinstall Android on every phone. Do not flash bootloader/firmware or bypass device security.

## USB and recovery-media safeguards

- Read and identify the physical device and partition layout before any write.
- Reuse an existing multi-boot drive only if its owner explicitly chooses it and its existing contents have been preserved; otherwise recommend a separate expendable drive.
- Confirm the selected physical disk by model, capacity, and partition layout immediately before writing. Never infer a disk from a drive letter alone.
- Verify official image source, licensing, signature/checksum, architecture, and firmware compatibility before writing.
- Warn that writing recovery media can erase the selected drive and require a separate final confirmation.
- Do not write to, format, repartition, or overwrite a USB drive during a read-only audit.
- After writing, verify the media and document that a successful write does not by itself prove physical-device boot compatibility.

## Status vocabulary

Every step must be labelled one of:
- **Complete and verified** — evidence for the exact claim is recorded.
- **Partial** — some files or checks succeeded; coverage is incomplete.
- **Failed** — an operation failed with a recorded reason.
- **Unverified** — evidence is missing or only indirect.
- **Blocked** — a safety prerequisite is not satisfied.

Do not report a reset, backup, restore test, USB creation, or boot test as complete based only on an intended plan, a device being detected, a file count, or a checksum.

## Acceptance checklist

- [ ] Device identity and recovery target recorded.
- [ ] Chosen recovery mode and data-loss consequences shown.
- [ ] Required essential production recovery material preserved before host wipe.
- [ ] Encryption and manifest checks completed without exposing secret contents.
- [ ] Restoreability limitations stated; isolated restore test performed where feasible.
- [ ] Exact destructive target and separate confirmation recorded.
- [ ] USB image/source/compatibility verified before writing.
- [ ] Actual reset, restore, USB write, and boot outcomes reported separately.
- [ ] No source backup or user data deleted without explicit approval.
