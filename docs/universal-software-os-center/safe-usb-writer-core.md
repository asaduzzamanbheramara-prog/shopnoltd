# Safe USB writer core

This PR adds a fail-closed, adapter-injected write core and an in-memory test
double. It does NOT enable physical USB writing.

- No native device discovery, raw disk open, privilege escalation, formatting,
  partitioning, mount/unmount, or installer execution is included.
- System disks and non-removable targets are refused.
- The operator must type the exact target confirmation: ERASE followed by the
  selected device path. A real helper must collect this confirmation in its
  own UI immediately before opening the destructive device handle.
- Device identity is checked immediately before open and again after open.
- A caller must supply a non-empty, reviewed image-architecture/target-
  architecture compatibility matrix. The core rejects malformed, missing and
  unsupported pairs before opening the target. This matrix is not inferred
  from marketing labels or assumed to cover every device.
- The image must match a publisher-sourced SHA-256 digest. The digest source
  URL must be valid HTTPS without embedded credentials or a fragment. Reviewers
  must independently establish publisher authenticity; HTTPS alone is not
  proof of publisher identity, and the core does not fetch or authenticate the
  publisher's digest document.
- Before opening a device, the core copies the image into a bounded
  SpooledTemporaryFile, rejects data beyond the declared size, and hashes the
  staged bytes. The exact staged bytes are then written, preventing a mutable
  source stream from changing between preflight hashing and the write.
- Writes are chunked; cancellation is checked between chunks and again before
  flush; flush and full read-back hash verification are required before success.
- Invalid sizes/flags, permission errors, partial writes, cancellation and
  verification errors are failures. Partial media must not be booted.
- The staging buffer uses memory up to 8 MiB and spills to a temporary file
  above that threshold; deployments must account for temporary-storage space,
  permissions, confidentiality and cleanup.

Tests use only in-memory fake devices and cover successful write/read-back,
system-disk and non-removable-target refusal, wrong confirmation, insufficient
capacity, changed identity before and after open, digest mismatch, invalid
HTTPS URLs, cancellation before and after progress, declared-size mismatch,
oversized input rejection before device open, mutable-source protection,
partial-write failure, permission denial, malformed/unsupported architecture
matrices, boolean size rejection, and read-back corruption. CI must never use
real block devices.

## Still required before physical use

A separately reviewed native adapter and signed desktop helper are still
required for Windows, Linux, and macOS. It must handle platform device identity,
system-disk aliases, ambiguous targets, device removal, permission errors,
progress, cancellation, release provenance, updates, and safe temporary-file
management. The helper must obtain a fresh device scan and explicit confirmation
in the same trusted UI immediately before destructive access. Then use a
dedicated blank test USB for documented UEFI boot evidence. No production-ready
claim is allowed until these gates pass. Never use the existing E2B/multiboot
drive as a test target. Browser pages must never invoke arbitrary disk writes.
