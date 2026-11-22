# Safe USB writer core

This PR adds a fail-closed, adapter-injected write core and an in-memory test
double. It does NOT enable physical USB writing.

- No native device discovery, raw disk open, privilege escalation, formatting,
  partitioning, mount/unmount, or installer execution is included.
- System disks and non-removable targets are refused.
- The operator must type the exact target confirmation: ERASE followed by the
  selected device path.
- Device identity is checked immediately before open and again after open.
- The image must match a publisher-sourced SHA-256 digest. The digest source
  URL must be HTTPS; reviewers must independently establish publisher
  authenticity because HTTPS alone is not proof of publisher identity.
- Writes are chunked; cancellation is checked between chunks; flush and full
  read-back hash verification are required before success is returned.
- Cancellation and I/O errors are failures. Partial media must not be booted.

Tests use only an in-memory fake and cover successful write/read-back,
system-disk and non-removable-target refusal, wrong confirmation, insufficient
capacity, changed identity before and after open, digest mismatch, non-HTTPS
digest source, cancellation before and after progress, declared-size mismatch,
partial-write failure, and read-back corruption. CI must never use real block
devices.

## Still required before physical use

A separately reviewed native adapter and signed desktop helper are still
required for Windows, Linux, and macOS. It must handle platform device identity,
system-disk aliases, ambiguous targets, removal, permission errors, progress,
cancellation, release provenance, and updates. Then use a dedicated blank test
USB for documented UEFI boot evidence. No production-ready claim is allowed
until these gates pass. Never use the existing E2B/multiboot drive as a test
target. Browser pages must never invoke arbitrary disk writes.
