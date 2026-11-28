# Website-first Auto Connect implementation

This work is intentionally isolated from production deployment and existing device data.

## User experience contract

- A signed-in user selects **Auto Connect** on an existing account-owned device.
- The website creates a short-lived pairing session bound to the authenticated user, existing device ID, platform, nonce, expiry, and one-time use.
- The browser never receives a long-lived executor credential and never places a pairing secret in a URL, command line, analytics event, or log.
- The target device completes one OS-authorized first-time bootstrap. A normal website cannot silently install privileged software or bypass UAC, Android package installation, MediaProjection, Accessibility, or other OS consent prompts.
- After bootstrap, the local service reconnects automatically; users do not repeat terminal commands for ordinary reconnects.

## Required implementation stages

### 1. Pairing control plane
- Add authenticated gateway create/status/cancel endpoints.
- Add registry create/consume/status/revoke endpoints.
- Store only a hash of the one-time pairing secret.
- Bind pairing to owner subject, existing device ID, platform, nonce, and a short expiry.
- Consume atomically under the registry lock; reject replay, expiry, wrong owner, wrong platform, and revoked sessions.
- Return the long-lived executor credential only from registry directly to the local agent over TLS.

### 2. Website UI
- Replace token display/copy and shell-command-first controls with an Auto Connect wizard.
- Show pending, installer-required, online, offline, and screen-ready as distinct states.
- Poll authenticated pairing status; do not infer connectivity from session creation.
- Keep all existing device IDs and ownership unchanged.

### 3. Platform bootstrap
- Windows: signed versioned bootstrapper with explicit UAC approval.
- Linux/WSL: signed/package-managed bootstrap helper with explicit local approval.
- Android: reviewed app or Termux flow; clearly request Android installation and runtime permissions.
- Render: determine the actual runtime and use a service-side installation/integration path, not a desktop installer.
- macOS/iOS: show only capabilities that are implemented and supported.

### 4. Remote screen capability
- Keep executor heartbeat separate from MeshCentral enrollment.
- Show Screen Ready only after independently verifying MeshCentral node ownership and reachability.
- Require user consent for screen capture and input capabilities.

## Acceptance tests

- Existing device IDs and owner IDs remain unchanged.
- Cross-user, wrong-device, wrong-platform, expired, revoked, and replayed pairing attempts fail.
- Pairing secrets are stored hashed and never appear in browser-visible responses, URLs, command-line arguments, or logs.
- A fresh signed heartbeat is required for Online.
- MeshCentral ownership and reachability are required for Screen Ready.
- Reconnect after first-time setup requires no repeated manual command.
- CI tests pass before any deployment is considered.

## Rollout boundary

This branch is not deployed. No production database, Kubernetes Secret, PVC, Render service setting, or existing device record is changed by this planning artifact. Production rollout requires separate review and explicit approval.
