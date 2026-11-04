# Android Cloud Physical Device Host Architecture

Status: Proposed implementation plan  
Scope: Add a physical Android device backend without changing or removing the existing Kubernetes x86-64 emulator backend.

## Goals

- Let an enrolled Android 13+ ARM64 phone act as a Shopnoltd Android Cloud device.
- Keep the existing Keycloak-authenticated Controller and browser product.
- Avoid provisioning an emulator Pod and emulator Gateway Pod for a physical-device session.
- Keep device connectivity outbound-only from the phone; never expose Android Debug Bridge (ADB) to the public internet.
- Preserve the emulator backend as the default until the physical-device path passes end-to-end tests.

## Current implementation constraints

The current Controller provisions an x86-64 emulator Pod with `/dev/kvm`, a separate WebRTC Gateway Pod, a Service, and an Ingress for every session. The current browser uses `android-emulator-webrtc` and expects the Google Android Emulator gRPC/WebRTC protocol. The APK, app-list, launch, and uninstall handlers execute ADB commands inside the emulator Pod. Those assumptions do not apply to a physical Android phone.

The Realme RMX3511 test device is Android 13 (SDK 33), ARM64. It can run a native Android agent, but it cannot run the existing x86-64 emulator image natively. This backend therefore uses the phone's real Android OS; it is not a software emulator.

## Target architecture

1. **Controller (Kubernetes):** retain Keycloak user authentication and session ownership. Add an explicit backend selector: `emulator` (default) or `physical_device`. Physical-device session creation must fail closed unless the user owns an online, paired device with available capacity.
2. **Device enrollment:** authenticated, one-time pairing challenge; device generates a private key locally. Controller stores only the public key and device metadata. Issue short-lived, revocable device credentials after proof-of-possession. Do not reuse ADB pairing credentials.
3. **Device Agent (Android/Kotlin):** foreground service with persistent notification, explicit user consent for MediaProjection, explicit permission/consent for remote input, heartbeat, reconnect with backoff, and secure outbound TLS connection. Android OS restrictions may stop background work; do not promise unattended 24/7 availability.
4. **Media transport:** use WebRTC with an authenticated signalling/control channel. TURN is optional for NAT traversal. Never publish an unauthenticated device stream or accept arbitrary signalling peers.
5. **Input control:** map browser touch/key events to a narrowly scoped, user-approved Android control mechanism. Prefer Android AccessibilityService with explicit user enablement and clear disclosure; do not silently inject input or bypass OS protections.
6. **App management:** use Android-supported PackageInstaller/user confirmation for APK installation. Launch and inventory operations must be performed by the agent under its app permissions. Do not claim emulator-only features (mock GPS, snapshots, virtual sensors) are supported on physical devices.
7. **Browser:** add a device-session client and transport adapter. Do not route physical sessions through `android-emulator-webrtc` or the emulator gRPC gateway.

## API and lifecycle contract

- `POST /api/v1/android-cloud/devices/pairing-challenges`: authenticated user requests a short-lived one-time challenge.
- `POST /api/v1/android-cloud/devices/enroll`: agent proves possession of its generated key and consumes the challenge.
- `POST /api/v1/android-cloud/devices/heartbeat`: agent reports online state, agent version, capabilities, and battery/network diagnostics; credentials are revocable and scoped to one device.
- `GET /api/v1/android-cloud/devices`: authenticated user lists only their enrolled devices.
- `POST /api/v1/android-cloud/sessions`: optional `backend` and `device_id`; preserve `emulator` as default. For `physical_device`, reserve an owned online device and do not create emulator/gateway Pods, Services, or Ingresses.
- `DELETE /api/v1/android-cloud/sessions/{session_id}`: release the device reservation and signal the agent to stop streaming; never uninstall apps or erase user data as a side effect.

All device and session operations must verify Keycloak user ownership. Device credentials must not be accepted as user credentials. Do not put long-lived secrets in URLs, browser storage, logs, or Android shared storage.

## Session and resource safety

- A physical device can serve only one interactive session at a time unless explicit multi-session isolation is designed and tested.
- Device offline, revoked, expired, or consent withdrawn => session transitions to unavailable/stopped; no fallback that silently allocates an x86 emulator.
- Session TTL and heartbeat must be enforced server-side.
- Existing emulator session recovery/cleanup must not interpret physical sessions as emulator Pod sessions.
- Do not remove or scale down existing emulator resources as part of enabling this backend.

## Rollout plan

1. Add data models, ownership checks, device registry, challenge/heartbeat APIs, and backend-aware session lifecycle with unit tests.
2. Build the Android Kotlin agent and enrollment/foreground-service flow.
3. Implement authenticated WebRTC signalling and media transport.
4. Implement browser device-session adapter and supported device capabilities.
5. Run tests with the Realme RMX3511 while retaining the emulator backend.
6. Measure actual PC/K3s CPU and memory before and after a controlled physical-device session.
7. Only after explicit operator approval, change default routing or reduce emulator capacity. No production workload is removed automatically.

## Non-goals for the first release

- Running the existing x86-64 emulator image on ARM64 Android.
- Rooting the phone or enabling privileged ADB access.
- Exposing TCP 5555, Wireless Debugging, or ADB over the public internet.
- Silent screen capture, hidden remote control, bypassing Android permission prompts, or unattended installation of arbitrary APKs.
- Claiming parity for mock GPS, virtual sensors, emulator snapshots, or other emulator-specific APIs.

## Acceptance criteria

- Existing emulator sessions continue to work unchanged.
- A user can enroll only a device they physically approve and control.
- Another user cannot list, reserve, control, or stream an enrolled device.
- Physical-device sessions create zero emulator Pods, gateway Pods, Services, or per-session Ingresses.
- Device stream/control works only after explicit Android consent and is terminated on session stop, consent withdrawal, credential revocation, or TTL expiry.
- No public ADB endpoint exists.
- Automated tests cover pairing expiry/replay, ownership, concurrent reservation, heartbeat expiry, device offline, stop/release, and backend isolation.
- PC/K3s workload reduction is measured rather than assumed.
