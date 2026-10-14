# Desktop integration plan: safe progression from web catalogue

## Existing implementation found

The repository already contains `apps/desktop-shell`, an Electron wrapper for the Shopnoltd web/admin portals. The reviewed `src/main.js` sets `nodeIntegration: false`, `contextIsolation: true`, and `sandbox: true`. Its `src/preload.js` explicitly exposes no privileged bridge. The navigation boundary now trusts only the exact HTTPS origin baked into the selected build (not all hostname suffix matches) and opens only HTTPS external links in the system browser. Node's built-in test runner covers lookalike hosts, sibling portals, unsafe protocols, credential-bearing URLs, and malformed input. This is a good security boundary for a web portal, but it means the current shell cannot install software, inspect disks, change boot settings, or repair an operating system.

## Do not turn the portal into an administrator shell

Do not expose generic `exec`, arbitrary PowerShell/Bash, filesystem-wide access, package-manager arguments, disk formatting, or bootloader operations to the website. Catalogue metadata and remote API responses must never become commands.

## Proposed staged implementation

### Stage A — web-only (current)
- Browse official download pages and documentation.
- Explain supported platform/architecture, licences, verification status, and backup steps.
- No local execution and no claim that a download was verified by Shopnoltd.

### Stage B — optional diagnostics companion
- Build a separate, versioned desktop companion with a narrow, typed API.
- Start with read-only facts only: OS name/version, CPU architecture, available disk space, and app version.
- Do not enumerate file contents, collect serial numbers, read browser credentials, or upload diagnostics automatically.
- Show exactly what will be shared and require consent before any network upload.
- Package and sign installers; publish checksums and release provenance.
- Keep updates signed and reject downgrade/tampered packages.

### Stage C — allow-listed install actions
- Use a locally installed, signed helper with explicit per-action confirmation.
- The server may return only a catalogue product ID and policy metadata; local code maps reviewed product IDs to fixed installer sources and arguments.
- Verify publisher signature/checksum before launch where supported.
- Never allow a web page or user-generated catalogue entry to provide raw commands.
- Explain licence terms, required privileges, disk space, restart requirements, and rollback options before execution.
- Log result status without logging secrets or full command lines that may contain secrets.

### Stage D — recovery environment
- Build from pinned, reviewable source; scan dependencies; generate SBOM, checksums, and signed release provenance.
- Test the image in virtual machines and on representative hardware before publishing supported-device claims.
- Use a USB or a supported, preconfigured network-boot path for devices that cannot boot the installed OS.
- Require backup-first guidance and a separate confirmation immediately before any destructive storage operation.

## Acceptance gates

- Unit tests for product-ID allow-lists, signature/checksum failure, platform mismatch, cancellation, and downgrade rejection.
- Security review of Electron navigation and preload permissions.
- Installer signing and release pipeline reviewed.
- VM tests prove the image boots without writing to the host disk by default.
- No paid action is unlocked by a browser flag; server-side entitlement must be verified after the billing contract is fixed.
