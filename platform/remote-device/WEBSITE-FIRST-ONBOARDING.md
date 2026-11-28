# Website-first device onboarding

## Product contract

A signed-in user should be able to start pairing from **My Devices** without
manually composing or typing shell commands. The browser must never claim a
device is connected merely because a device record or executor process exists.

The user-visible state machine is:

1. `not_added` — show Add device.
2. `pending_pairing` — account-owned device record and one-time pairing session exist.
3. `agent_install_required` — explain the minimum OS-authorized install step.
4. `executor_connected` — authenticated executor enrollment and fresh heartbeat verified.
5. `remote_agent_required` — desktop executor is online but MeshCentral agent is not linked.
6. `screen_ready` — MeshCentral node is linked and reachable; only then enable desktop Connect/Show screen.
7. `offline` / `revoked` — show last-seen/revocation state and recovery action.

Executor heartbeat and remote-screen availability are separate capabilities.

## Browser security boundary

A normal website cannot silently install or start privileged software on another
computer or phone. Do not implement hidden shell execution, browser permission
bypass, arbitrary command execution, or a static reusable pairing secret.

The website-first experience should therefore use:

- **Windows:** download a signed, versioned bootstrapper from My Devices. The
  user opens it and approves the OS/UAC prompt. It obtains a short-lived,
  single-use pairing challenge from the already-authenticated website flow,
  exchanges it for the device credential, installs the approved executor and
  separately offers the official MeshCentral desktop agent.
- **Linux / WSL:** provide a signed/package-managed installer where possible.
  For WSL, detect the distro and offer a downloadable bootstrap script that
  requests elevation only for systemd service installation. The user should
  not have to copy a command containing a token. Do not assume a browser can
  invoke WSL or sudo without a local helper and explicit user action.
- **macOS:** signed/notarized package, explicit installer and Screen Recording
  / Accessibility permission guidance. Do not report remote-control ready
  until the MeshCentral agent is online and linked.
- **Android:** signed Android app or a reviewed Termux onboarding path with
  QR/deep-link pairing. MediaProjection requires user approval and a visible
  foreground service. Touch control requires a separately reviewed,
  user-enabled AccessibilityService. Termux inventory is not screen sharing.
- **iOS/iPadOS:** clearly mark native unattended control unsupported; offer
  only capabilities Apple permits.

## Pairing protocol

1. Authenticated user creates an account-owned pending device record.
2. Gateway creates a short-lived pairing session bound to user ID, device ID,
   platform, nonce, expiry and one-time use. Do not expose long-lived HMAC
   credentials to the browser.
3. Browser displays a QR/deep link or downloads a bootstrap package containing
   only a pairing-session reference, never the long-lived device secret.
4. Local installer confirms device ownership locally and exchanges the
   one-time session over HTTPS.
5. Registry consumes the session atomically and returns the agent credential
   directly to the local agent. Replay, expired, wrong-user, wrong-device and
   wrong-platform attempts fail closed.
6. Device reports signed heartbeat. UI displays Online only after a fresh
   heartbeat, with last-seen and stale thresholds.
7. Desktop screen capability is enabled only after a MeshCentral node is
   independently authenticated, linked to the same account-owned device, and
   reachable. Executor enrollment alone never enables screen controls.

## Implementation sequence

### Phase A — safe UX and state correctness
- Replace the current token-copy/terminal-command-centric flow with a
  step-by-step pairing panel and explicit platform capability matrix.
- Add polling/refresh for pending enrollment, fresh heartbeat and stale state.
- Never call pending/registered/agent-installed a live screen connection.
- Preserve per-user ownership, share permissions, revocation and audit events.
- Keep existing clients, Kubernetes Secrets and production data untouched.

### Phase B — pairing service
- Add pairing-session create/status/consume/revoke APIs to gateway and registry.
- Store only a hash of the one-time pairing secret; enforce TTL and atomic
  single-use consumption.
- Bind every operation to the authenticated owner and device record.
- Add unit, integration, replay, expiry, cross-user and wrong-platform tests.

### Phase C — native bootstrap/installers
- Build signed Windows, Linux/WSL and macOS bootstrap packages.
- Build Android app/Termux pairing with explicit permissions and honest
  capability reporting.
- Never pass tokens in command-line arguments, URLs, logs or analytics.
- Verify install signatures and update channels.

### Phase D — screen/control readiness
- Integrate MeshCentral SSO/session establishment without static credentials.
- Verify node ownership before linking.
- Test real video, keyboard and mouse on supported desktops.
- Treat Android screen viewing and touch control as separate opt-in features.
- Keep iOS unsupported until a genuinely supported native capability exists.

## Acceptance criteria

- A normal user can add a device from the website and gets a platform-specific
  pairing experience without manually constructing a command.
- Another user's device cannot be enrolled, listed, linked, shared or controlled
  without an explicit authorized share.
- Replayed/expired pairing sessions fail and cannot mint another credential.
- Device is Online only with a fresh signed heartbeat.
- Screen Ready only after a linked, reachable remote-screen agent is verified.
- Desktop screen and input are tested on real devices; UI presence alone is not
  acceptance.
- Android and iOS capability labels match actual platform support.
- Existing production Keycloak clients, Secrets, databases and PVCs are not
  modified as part of the UX work.


## Current implementation gaps found during review

- The current WSL installer expects the pending **device ID** as its first
  argument; it asks for the one-time enrollment token separately through hidden
  input. A token must never be supplied as the first argument.
- **Still open:** the current Devices page exposes a copied shell command
  for Windows/Android; Linux/WSL and macOS do not have a complete website-guided
  installer flow. This branch adds heartbeat polling and truthful executor
  online/offline labels, but does not yet eliminate the OS-authorized installer
  step or provide native signed installers.
- **Implemented in this branch:** newly issued executor enrollment tokens
  are stored as SHA-256 hashes, expire after 20 minutes, are single-use, and
  are cleared after successful enrollment. Legacy plaintext tokens are accepted
  only for 20 minutes from device creation; older pending records must regenerate
  a token. This is a short-lived enrollment-token improvement, not yet the full
  browser-to-native pairing-session protocol described above.
- The current registry executor-enroll route returns the long-lived HMAC secret
  to the local executor after successful token exchange. Preserve that
  server-to-agent exchange, but do not route the long-lived secret through the
  browser or a downloadable script.
- The current MeshCentral link API accepts a node ID from the authenticated
  user flow, but the system still needs an independently verified ownership
  and reachability check before it can advertise Screen Ready.
