# Android Cloud: Realme Physical Device Bridge

Status: Proposed; implementation must remain behind an explicit feature flag until end-to-end validation.

## Decision

Use the Realme RMX3511 as a **physical Android execution device**, not as a Kubernetes worker node.

The Android phone runs the tested Android application workloads. A small, outbound-connected bridge agent on the trusted Windows host uses the already-authorized ADB connection to control the phone and relay its screen/input stream to the Android Cloud service. The existing Kubernetes controller, authentication, session API, and current x86 emulator path remain available.

Do not attempt to install kubelet/containerd or register Android 13 as a Kubernetes Node. Android's application sandbox and userspace are not a supported drop-in Kubernetes worker environment. ADB-connected physical-device execution is the supported direction for this project.

## Why this is needed

The current implementation is emulator-specific:

- `platform/android-cloud/controller/main.py` creates a privileged x86 Android Emulator pod for every session.
- The pod requests 2 CPU and 1536 MiB memory (limits: 4 CPU and 3 GiB), mounts `/dev/kvm`, and exposes emulator gRPC/ADB ports only inside the cluster.
- The gateway connects to the emulator's gRPC endpoint.
- The browser uses `android-emulator-webrtc`, which speaks the Google emulator WebRTC gateway protocol.
- The Android emulator image is `30-google-x64`; it is not the Realme phone's `arm64-v8a` runtime.

Changing a Deployment replica count cannot move this emulator process onto Android. The execution backend and streaming protocol must be adapted.

## Target architecture

1. **Kubernetes controller (existing):** keeps Shopnoltd authentication, ownership, TTL, session limits, audit, and API contracts.
2. **Windows device bridge agent (new):** runs on the trusted PC, connects to the already-paired Realme device using the local ADB client, reports device health, and accepts only narrowly-scoped session actions. It initiates an authenticated outbound connection to the controller/bridge API; no public ADB listener or inbound router port is required.
3. **Realme phone (execution):** runs the user's Android apps natively. The phone is leased exclusively to one session at a time.
4. **Screen/input transport:** use the scrcpy server/protocol over ADB as the initial transport candidate. The bridge relays H.264 video and control events to a browser-compatible WebRTC endpoint. Do not assume the current emulator gateway is compatible with scrcpy; it is not.
5. **Browser UI:** add an explicit Physical Device session mode and a separate viewer adapter. Keep the current emulator viewer unchanged as the fallback.

Conceptual flow:

```text
Shopnoltd browser
  | HTTPS session API + WebRTC media
  v
Kubernetes controller / WebRTC relay (existing cluster)
  ^ authenticated outbound bridge channel
  |
Windows device bridge agent (trusted PC; low CPU)
  | ADB over private Wi-Fi, paired/authorized
  v
Realme RMX3511 (Android 13, arm64-v8a)
  | native Android app execution + scrcpy screen/control
  +-----------------------------------------------+
```

The phone performs Android app execution and device-side video encoding. The PC remains the network bridge and Kubernetes host; this reduces the x86 emulator CPU/RAM load, but does **not** move the Kubernetes control plane, PostgreSQL, API service, or general-purpose server containers onto Android.

## Session lifecycle and safety requirements

- Device state must be `offline`, `available`, `leased`, or `unhealthy`; only one active lease is allowed for the single Realme phone.
- A lease is granted atomically and tied to the authenticated Shopnoltd user and session ID.
- Heartbeats expire leases after disconnect; recovery must release stale leases without interrupting a live session.
- The bridge must validate every command against a strict allowlist. No arbitrary shell endpoint, public ADB, unauthenticated WebSocket, or arbitrary port forwarding.
- Keep ADB pairing keys on the trusted host. Never log pairing codes, tokens, or private keys.
- Bind bridge communication to private networking and authenticated TLS. Prefer agent-initiated outbound connections to avoid exposing the Windows host.
- Enforce APK size/type checks, package-name validation, per-user authorization, and session TTL at the controller.
- Phone screen lock, battery saver, Wi-Fi loss, reboot, thermal throttling, and Android background-process termination must be reported as device health states.
- Keep PostgreSQL, K3s control plane, API service, and public web portal on the existing infrastructure.
- Never scale down or remove the current emulator path until the physical-device path passes the acceptance tests below.

## Phased implementation

### Phase 0 — compatibility and safety (no production changes)

- Confirm the existing Windows ADB connection can reconnect after a phone/PC restart without exposing ADB beyond the private LAN.
- Confirm the phone remains reachable while charging, screen locked/unlocked, and under normal thermal conditions.
- Measure idle and active phone RAM, CPU, battery temperature, and network latency.
- Confirm whether the Windows host can run the bridge reliably while WSL2/K3s is active.

### Phase 1 — bridge proof of concept

- Add a standalone Windows bridge agent with device discovery, health heartbeat, exclusive lease, and narrowly-scoped ADB operations.
- Add unit tests for lease contention, disconnect, timeout, unauthorized commands, and reconnect.
- Initially test status, screen capture, tap/swipe/text input, APK install, launch, and uninstall against the Realme.
- Do not change the existing controller's default backend.

### Phase 2 — browser streaming

- Validate scrcpy protocol compatibility with Android 13 / this Realme firmware.
- Relay device-encoded H.264 and input through an authenticated WebRTC path.
- Add a separate physical-device viewer component; do not overload the existing emulator WebRTC component.
- Test latency, dropped frames, reconnect, browser refresh, and session ownership.

### Phase 3 — opt-in Android Cloud physical backend

- Add a server-side backend selector: `emulator` (default) or `physical_device` (explicit opt-in).
- Expose physical-device capability only when the bridge is healthy and a lease is available.
- Keep emulator sessions operational as fallback.
- Run production-like tests with one authorized test account before enabling general users.

### Phase 4 — resource reduction

Only after the physical path has passed all tests, compare measured PC CPU/RAM before and after. Then consider reducing the emulator session capacity or scheduling emulator pods away from the PC worker. Do not scale the controller, PostgreSQL, or cluster control plane to zero.

## Acceptance criteria before any production migration

- Device reconnects after Wi-Fi interruption and host/phone reboot.
- One user can lease the phone; a second user is rejected/queued.
- Another user cannot view or control the leased device.
- Video, touch, keyboard/text, APK upload/install, app launch, and uninstall all work.
- Invalid package names and unapproved commands are rejected.
- Session stop/TTL expiry releases the device and cleans up temporary state.
- No public ADB port, public scrcpy endpoint, or arbitrary shell API exists.
- Android thermal/battery/network failures are visible and do not corrupt session ownership.
- Existing emulator backend and production services remain healthy throughout.

## Explicit non-goals

- Running Kubernetes kubelet/containerd on stock Android 13.
- Moving PostgreSQL, K3s control plane, API service, or the public web portal to the phone.
- Disabling the current emulator backend before physical-device acceptance tests.
- Exposing ADB, scrcpy, or the bridge directly to the public internet.
- Deploying this proposal automatically to the live cluster.
