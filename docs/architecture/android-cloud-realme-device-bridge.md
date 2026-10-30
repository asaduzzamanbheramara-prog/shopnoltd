# Android Cloud: Realme Physical Device Bridge

Status: Proposed; implementation must remain behind an explicit feature flag until end-to-end validation.

## Product decision

Build toward **Multi-user Android Cloud**: authenticated Shopnoltd customers access an Android device from a browser. The Realme RMX3511 is the first physical execution device, not a Kubernetes worker node.

Important capacity boundary: **one physical phone can host only one actively controlled customer session at a time** in the initial design. Multiple customers may sign in, but sessions must be queued or shown as temporarily unavailable while the device is leased. This is not concurrent, isolated virtual Android instances. True simultaneous sessions require multiple physical devices or the existing emulator backend.

The phone runs Android applications natively. A lightweight bridge agent on the trusted Windows host uses the already-authorized ADB connection and relays screen/input to the Android Cloud service. Existing Kubernetes authentication, session API, controller, and x86 emulator path remain available.

Do not attempt to install kubelet/containerd or register Android 13 as a Kubernetes Node. Android is not a drop-in Kubernetes worker environment.

## Current implementation constraints

The current implementation is emulator-specific:

- `platform/android-cloud/controller/main.py` creates a privileged x86 Android Emulator pod for every session.
- The pod requests 2 CPU and 1536 MiB memory (limits: 4 CPU and 3 GiB), mounts `/dev/kvm`, and exposes emulator gRPC/ADB ports only inside the cluster.
- The gateway connects to the emulator's gRPC endpoint.
- The browser uses `android-emulator-webrtc`, which speaks the Google emulator WebRTC gateway protocol.
- The Android emulator image is `30-google-x64`; it is not the Realme phone's `arm64-v8a` runtime.

Changing a Deployment replica count cannot move this emulator process onto Android. The execution backend and streaming protocol must be adapted.

## Multi-user target architecture

1. **Shopnoltd identity and authorization:** reuse the existing authenticated customer identity; derive user and tenant ownership on the server, never trust a browser-supplied owner ID.
2. **Session API/controller:** create, queue, lease, renew, stop, and expire sessions. Enforce per-user/per-tenant quotas and audit actions.
3. **Device scheduler:** maintain device states `offline`, `available`, `leased`, and `unhealthy`. Atomically grant one exclusive lease for the single Realme phone. Queue or reject other customers while it is busy; do not silently let them share control.
4. **Windows device bridge agent (new):** runs on the trusted PC, connects to the already-paired Realme using local ADB, reports device health, and accepts only narrowly-scoped session actions. It initiates an authenticated outbound connection; no public ADB listener or inbound router port is required.
5. **Realme phone (execution):** runs the selected Android app natively. The phone is leased exclusively to one customer session at a time.
6. **Screen/input transport:** use the scrcpy server/protocol over ADB as the initial transport candidate. The bridge relays H.264 video and control events to a browser-compatible WebRTC endpoint. The current emulator gateway is not assumed to be compatible with scrcpy.
7. **Browser UI:** add an explicit physical-device viewer adapter and customer session status (queued, starting, active, reconnecting, ended). Keep the current emulator viewer unchanged as fallback.

Conceptual flow:

```text
Shopnoltd customer browser
  | authenticated HTTPS session API + WebRTC media
  v
Kubernetes controller / scheduler / WebRTC relay
  ^ authenticated outbound bridge channel
  |
Windows device bridge agent (trusted PC)
  | private, paired ADB connection
  v
Realme RMX3511 (Android 13, arm64-v8a)
  | native app execution + scrcpy screen/control
  +---------------------------------------------+
```

The phone performs Android app execution and device-side video encoding. The PC remains the bridge host and Kubernetes host. This can reduce x86 emulator CPU/RAM use, but does **not** move the Kubernetes control plane, PostgreSQL, API service, or general-purpose server containers onto Android.

## Multi-user isolation and app/data policy

- A single shared phone is a serialized device pool, not a collection of independent Android VMs. Only the lease owner may see or control its screen.
- Before enabling customer access, define a tested per-session cleanup policy for app data, downloaded files, accounts, browser state, notifications, clipboard, and temporary storage. Do not assume clearing one app is sufficient.
- Never expose a previous customer's app data or signed-in accounts to the next customer. If reliable cleanup/isolation cannot be demonstrated, do not reuse the phone across customers; use dedicated devices or isolated emulator instances instead.
- Do not rely on Android multi-user/profile support until verified on this exact Realme firmware and tested for app compatibility.
- APK installation must be controlled: enforce file size/type checks, malware scanning where available, package-name validation, tenant/user authorization, and an explicit allowlist or review policy. Do not offer unrestricted arbitrary APK execution on a shared customer device.
- Define whether customer-installed apps persist for that customer or are removed after each session. Default to ephemeral session data until a secure persistence design exists.
- Enforce per-user/per-tenant quotas, maximum session duration, queue limits, rate limits, and auditable install/launch/uninstall operations.
- Prevent customers from accessing ADB, bridge credentials, host filesystem, arbitrary shell, other sessions, or internal cluster services.

## Session lifecycle and security

- A lease is granted atomically and tied to the authenticated Shopnoltd user, tenant, and session ID.
- Heartbeats expire leases after disconnect; recovery must release stale leases without interrupting a live session.
- Validate every command against a strict allowlist. No arbitrary shell endpoint, public ADB, unauthenticated WebSocket, or arbitrary port forwarding.
- Keep ADB pairing keys on the trusted host. Never log pairing codes, tokens, or private keys.
- Bind bridge communication to authenticated TLS. Prefer agent-initiated outbound connections to avoid exposing the Windows host.
- Screen lock, battery saver, Wi-Fi loss, reboot, thermal throttling, and Android background-process termination must be reported as device health states.
- Keep PostgreSQL, K3s control plane, API service, and public web portal on existing infrastructure.
- Never scale down or remove the current emulator path until physical-device acceptance tests pass.

## Phased implementation

### Phase 0 — compatibility and safety (no production changes)

#### Verified local test results (2026-10-31)

The first Windows-to-Realme connectivity check has been completed:

- Device: Realme RMX3511 / RE87BAL1, Android 13.
- Wireless ADB pairing and direct TCP connection succeeded on the private LAN.
- `adb devices -l` showed both a direct TCP serial and an ADB mDNS alias for the same physical phone; these are not two devices.
- scrcpy 5.0.1 installed successfully on the Windows host.
- Local screen mirroring and mouse/keyboard input both work.
- The default full-resolution stream was usable but noticeably laggy.
- A reduced stream using `--max-size=1024 --max-fps=30 --video-bit-rate=4M` improved responsiveness, but was not fully smooth. The scrcpy log reported a 464x1024 encoded texture after downscaling.
- The scrcpy log reported Direct3D 11 rendering and D3D11 video decoding on the Windows host.

This validates only local ADB + scrcpy compatibility. It does **not** validate a persistent bridge agent, browser streaming, WebRTC transport, multi-user leasing, session cleanup, or production readiness. The phone's dynamic LAN address and ADB pairing material must not be committed to repository documentation.

Remaining Phase 0 checks:

- Compare Wi-Fi performance with a USB-connected baseline.
- Measure latency, dropped frames, phone CPU/RAM, battery temperature, and host resource use during a representative app workload.
- Test reconnect after Wi-Fi interruption and after host/phone restart.
- Confirm stable operation while charging and under normal thermal conditions.
- Keep the ADB endpoint private; never expose it through router port forwarding or public ingress.

- Confirm the Windows ADB connection can reconnect after phone/PC restart without exposing ADB beyond the private LAN.
- Confirm the phone remains reachable while charging, screen locked/unlocked, and under normal thermal conditions.
- Measure idle and active phone RAM, CPU, battery temperature, and network latency.
- Confirm whether the Windows host can run the bridge reliably while WSL2/K3s is active.
- Confirm the exact Realme firmware's app install, screen capture, input, and scrcpy compatibility.

### Phase 1 — single-device bridge proof of concept

- Add a standalone Windows bridge agent with device discovery, health heartbeat, exclusive lease, and narrowly-scoped ADB operations.
- Add unit tests for lease contention, disconnect, timeout, unauthorized commands, and reconnect.
- Initially test status, screen capture, tap/swipe/text input, APK install, launch, and uninstall against the Realme.
- Do not change the existing controller's default backend.

### Phase 2 — browser streaming

- Validate scrcpy protocol compatibility with Android 13 / this Realme firmware.
- Relay device-encoded H.264 and input through an authenticated WebRTC path.
- Add a separate physical-device viewer component; do not overload the existing emulator WebRTC component.
- Test latency, dropped frames, reconnect, browser refresh, and session ownership.

### Phase 3 — multi-user customer workflow (one active phone session)

- Add backend selector `emulator` (default) or `physical_device` (explicit opt-in).
- Add queue/availability UX for the single physical device; a second customer must never take over an active lease.
- Add tenant/user quotas, session TTL, audit trail, upload policy, and verified session cleanup before enabling customer access.
- Run production-like tests with separate test customer accounts and verify cross-user data isolation.
- Keep emulator sessions operational as fallback and as the path for concurrent isolated Android sessions.

### Phase 4 — capacity expansion and resource reduction

- If concurrent customer sessions are required, add more independently managed physical devices or use isolated emulator instances; do not pretend one phone provides multiple concurrent Android environments.
- Only after acceptance tests pass, compare measured PC CPU/RAM before and after. Then consider reducing emulator capacity or scheduling emulator pods away from the PC worker.
- Do not scale the controller, PostgreSQL, or cluster control plane to zero.

## Acceptance criteria before customer rollout

- Device reconnects after Wi-Fi interruption and host/phone reboot.
- One customer can lease the phone; a second customer is queued/rejected and cannot view/control the active session.
- Another tenant/user cannot access the lease, stream, uploaded APK, or previous customer's app/account data.
- Video, touch, keyboard/text, approved APK upload/install, app launch, and uninstall work.
- Invalid package names and unapproved commands are rejected.
- Session stop/TTL expiry releases the device and verified cleanup prevents data leakage to the next customer.
- No public ADB port, public scrcpy endpoint, or arbitrary shell API exists.
- Android thermal/battery/network failures are visible and do not corrupt session ownership.
- Existing emulator backend and production services remain healthy throughout.

## Explicit non-goals

- Running Kubernetes kubelet/containerd on stock Android 13.
- Moving PostgreSQL, K3s control plane, API service, or public web portal to the phone.
- Claiming concurrent isolated Android instances from one shared physical phone.
- Allowing unrestricted APK execution or persistent cross-customer app data on a shared phone.
- Disabling the current emulator backend before physical-device acceptance tests.
- Exposing ADB, scrcpy, or the bridge directly to the public internet.
- Deploying this proposal automatically to the live cluster.
