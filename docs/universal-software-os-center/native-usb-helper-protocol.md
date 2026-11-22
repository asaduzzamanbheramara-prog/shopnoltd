# Native USB helper protocol and security contract

Status: design contract only. This document does not implement or enable physical
device access. The browser must never receive raw block-device access.

## Architecture decision

Use the signed Shopnoltd desktop application as the trusted user interface and
a separately packaged, least-privilege native writer service as the only
component permitted to open removable block devices. Prefer the desktop
application's OS-supported native IPC/native-messaging channel. Do not expose an
unauthenticated localhost HTTP server, WebSocket, custom URL handler accepting
write commands, or remotely reachable port.

The desktop UI may request a scan and display results. The helper owns device
enumeration, identity, eligibility checks, image verification, the final
confirmation dialog, opening/closing the device handle, writing, flushing,
read-back verification, and the authoritative operation state.

## IPC framing and envelope

- Use a length-prefixed message frame with a 4-byte unsigned little-endian
  payload length followed by UTF-8 JSON.
- Reject zero-length frames, frames larger than 1 MiB, invalid UTF-8, duplicate
  JSON object keys, unknown protocol versions, unknown message types, and
  messages with unknown fields. Never attempt to recover by truncating input.
- Every request carries protocol version, a cryptographically random request
  identifier, and a command. Every response echoes the request identifier and
  has exactly one of a result or a structured error.
- The transport must authenticate the peer using OS-provided process identity
  and channel ACLs. Do not treat a browser-supplied origin, CORS header, random
  token in JavaScript, or possession of a localhost port as authentication.
- Bind a session to the signed desktop application identity. Reject unexpected
  parent processes, wrong user sessions, remote sessions where unsupported,
  and replayed request identifiers.
- Apply per-message and per-session timeouts, bounded queues, and rate limits.
  The helper must not spawn a shell or interpolate request fields into command
  lines.

## Device selection and confirmation

1. A scan returns read-only descriptors: opaque helper-issued device ID,
   vendor/model, serial when available (redacted in ordinary UI/logs), exact
   capacity in bytes, bus/removable classification, mount state, and stable
   platform identity evidence.
2. Never accept a raw device path, drive letter, disk number, or arbitrary
   device URI from the desktop renderer/browser as a write target.
3. The helper stores the full device identity behind a random, short-lived
   selection handle. Handles expire quickly and are invalidated on rescans,
   device arrival/removal, suspend/resume, identity changes, and session end.
4. Before preparation and again immediately before opening the device, the
   helper re-enumerates and compares the complete stable identity. Fail closed
   on missing fields, duplicate/ambiguous identities, changed capacity,
   changed removable/system-disk classification, mounted system volumes, or
   device replacement.
5. Maintain a platform-specific denylist of every system/boot/recovery disk
   identity and its aliases. Do not rely only on a removable flag or drive
   letter. If the helper cannot prove that the selected target is not a system
   disk, refuse.
6. Preflight validates the official image source, publisher signature/digest,
   image size, target capacity, architecture, firmware mode, Secure Boot
   compatibility, and explicit host/target support matrix. These are separate
   compatibility dimensions; architecture match alone is not sufficient.
7. Immediately before destructive open, the helper itself presents a trusted,
   native confirmation surface showing model, exact capacity, and stable
   identity suffix. Require the user to type a helper-generated phrase that
   includes the target identity. A confirmation accepted by a website or
   renderer is not sufficient.
8. The helper must not silently select the first disk, retry against another
   disk, or substitute a different device if the selected target disappears.

## Image acquisition and provenance

- Prefer a publisher's signed manifest and signature verification with a
  pinned/maintained trust policy. A downloaded checksum file over HTTPS alone
  does not establish publisher authenticity.
- Restrict downloads to reviewed official source hosts and allowed redirects;
  reject private/link-local destinations, downgrade redirects, unexpected
  content types, excessive sizes, and unbounded decompression.
- Verify the exact staged bytes that will be written. Do not hash one stream and
  later reopen or reread a mutable source for writing.
- Record image publisher, version, source URL, signature/digest verification
  result, digest, architecture, firmware requirements, and license metadata.
- Never bundle proprietary OS images or third-party tools without explicit
  redistribution permission. Require license review and provenance for helper
  dependencies and updates.

## Write lifecycle

Use a monotonic operation state machine:

`idle -> scanned -> prepared -> awaiting_native_confirmation -> writing -> flushing -> verifying -> succeeded`

Any error/cancel/device-change transition enters a terminal failed/cancelled
state. A partial write must never be represented as success. Do not automatically
retry destructive writes.

- Open the target only after the final helper-owned confirmation and final
  identity check. Request the narrowest OS access rights possible.
- Unmount only the selected target's volumes after explicit user confirmation;
  never force-unmount system volumes. If safe unmount cannot be established,
  abort before writing.
- Write bounded chunks, report monotonic progress, check cancellation between
  chunks, and check device identity/removal during the operation where the OS
  permits it.
- Cancellation stops further writes, flushes/closes the handle where safe, and
  reports that the media may be partial and must not be booted. Never claim
  rollback unless the original contents were actually backed up and restored.
- Flush using the platform's documented durable-write operation, then read back
  the complete written range and compare its cryptographic digest.
- Re-enumerate after verification and confirm the same physical identity is
  still present. Only then return success.
- On permission, I/O, short-write, device-removal, flush, or read-back failure,
  close handles safely and return a structured error with recovery instructions.

## Temporary storage, privacy, and logging

- The current Python core stages images in a SpooledTemporaryFile (memory up to
  8 MiB, then temporary disk). A production helper must select a dedicated,
  access-controlled temporary location with enough free space; never silently
  spill onto a nearly full system volume.
- Set restrictive permissions, avoid following symlinks/reparse points, defend
  against path replacement, and clean up staged files on success and failure.
  If cleanup fails, report the exact cleanup status without exposing image
  contents.
- Never log access tokens, raw serial numbers, full image contents, or private
  user paths. Logs must include operation ID, helper version, redacted device
  identity, image digest, state transitions, and structured failure codes.
- User cancellation and cleanup status must survive application restart in the
  operation journal. The journal must not enable replay of a destructive
  operation.

## Release and update requirements

- Sign installers and executable artifacts using platform-native signing
  mechanisms; publish checksums, provenance/SBOM, source revision, build
  attestation, and a documented key-rotation/revocation process.
- Verify update signatures before installation and prevent downgrade to
  vulnerable versions unless an explicit recovery procedure is used.
- Run as a standard user whenever possible. Elevation, if required, must be
  narrow, time-bounded, and bound to the already confirmed device identity.
- Keep host support explicit. Windows, Linux, and macOS need separate reviewed
  enumeration, identity, system-disk, unmount, write, flush, and signature
  verification implementations. Phones, tablets, TVs, wearables, and embedded
  devices must use vendor-supported recovery workflows unless a documented
  vendor procedure is validated.

## Required automated and hardware tests

CI uses only fake/in-memory block devices and simulated IPC peers. Required
cases include malformed/oversized frames, duplicate JSON keys, replay,
unauthenticated peer, wrong parent process, wrong user session, expired handle,
device replacement, duplicate identity, missing identity fields, system-disk
aliases, mounted volumes, insufficient temporary storage, symlink/reparse
attacks, unsupported host/target/architecture/firmware/Secure Boot matrix,
signature failure, redirect/downgrade, cancellation at each lifecycle stage,
partial writes, permission errors, flush errors, read-back mismatch, cleanup
failure, and helper restart during an operation.

Before any production-ready claim, publish signed build provenance and a
documented test report for at least one dedicated blank UEFI test device,
including exact host OS, device model, firmware mode, Secure Boot state, image
publisher/version/digest, boot result, and known limitations. Do not use the
existing E2B/multiboot drive or any production/system disk as a test target.

## Implementation gates

- [ ] Protocol parser, framing limits, duplicate-key rejection, and fuzz tests
- [ ] Authenticated native IPC and signed desktop parent verification
- [ ] Windows device enumerator and system-disk deny logic
- [ ] Linux device enumerator and system-disk deny logic
- [ ] macOS device enumerator and system-disk deny logic
- [ ] Trusted native confirmation UI and expiring device handles
- [ ] Signed publisher-manifest verification and official-source allowlist
- [ ] Host/target/architecture/firmware/Secure Boot compatibility catalogue
- [ ] Safe unmount/write/flush/read-back adapter per supported OS
- [ ] Temporary-storage policy, cleanup, and crash-safe operation journal
- [ ] Signed release, SBOM/provenance, update and revocation policy
- [ ] Dedicated blank-USB UEFI boot evidence

Until every applicable gate is implemented and independently verified, the
feature remains experimental and must not offer a real-device write action.
