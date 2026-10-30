# Android Cloud hybrid PC + Realme device architecture

Status: implementation plan; no production behavior changes are enabled by this document.

## Goal

Keep the existing Shopnoltd control plane on the PC-hosted K3s runtime while using the owner's already-paired Realme Android phone as the physical Android execution device. This is a hybrid design: the PC remains the control plane and secure bridge host; the phone performs Android app execution, display capture, touch/key input, and device testing.

This is not a proposal to run Kubernetes, PostgreSQL, or a general Linux server on the phone.

## Current implementation boundary

The current Android Cloud controller creates an emulator Pod, an emulator Service, a Google Android Emulator WebRTC gateway Pod, a gateway Service, and a per-session Ingress. The gateway expects the emulator gRPC endpoint (port 8554) through `EMULATOR_HOST`. A physical Android device does not expose that emulator gRPC API. Therefore the current gateway cannot be pointed at an ADB serial or phone IP and expected to work.

The existing emulator implementation must remain available as a fallback until physical-device acceptance is complete.

## Target topology

```text
Shopnoltd browser
      | HTTPS / authenticated WebRTC signaling
      v
Shopnoltd Android Cloud controller + session API (existing PC K3s)
      | authenticated, outbound-initiated agent channel
      v
PC device bridge agent (Windows host; uses existing ADB installation)
      | Android Wireless Debugging / ADB over TLS
      v
Realme physical Android device
```

The browser-facing media/signaling relay must be designed separately from the Google emulator gRPC gateway. A device agent should initiate its connection outbound so the design does not require opening inbound ADB ports on the PC or phone.

## Security requirements

- Never publish ADB (including the Wireless Debugging TLS port) through Ingress, a public tunnel, or a public load balancer.
- Never place ADB private keys, pairing codes, bearer tokens, or agent credentials in Git, ConfigMaps, browser storage, logs, or CI artifacts.
- Reuse the owner's existing trusted ADB pairing on the PC; do not silently pair, revoke authorizations, or change phone developer settings.
- Authenticate the agent with a short-lived, revocable, least-privilege credential. Bind each session to the authenticated Shopnoltd user and one registered device.
- Require explicit device registration/approval and a visible busy/connected state. Permit one interactive owner session by default.
- Restrict agent commands to a documented allowlist (screen stream, input events, package install/launch/list/uninstall where authorized). Do not provide arbitrary shell execution.
- Validate APK size/type and retain the existing package-name validation and per-user authorization checks.
- Use TLS for all network hops. Apply origin checks, session authorization, rate limits, and bounded frame/input message sizes.
- Stop media capture and release the device lease on session stop, expiry, agent disconnect, or controller restart.

Android Wireless Debugging uses authenticated TLS after pairing. The integration must preserve that protection and must not downgrade to legacy unauthenticated `adb tcpip 5555`.

## Device bridge responsibilities

The PC-side agent is the only component that talks to the local ADB server/device. It should:

1. Discover the already-authorized device using `adb devices -l`; require an explicit configured serial/device registration rather than selecting the first device.
2. Report sanitized model, Android version, online state, and capabilities to the controller.
3. Acquire an exclusive device lease for a session.
4. Start and supervise a pinned, verified scrcpy-server process over the existing ADB transport; relay encoded video and input events through the authenticated session channel.
5. Proxy only approved package-management operations and return structured results.
6. Reconnect safely after Wi-Fi changes without printing pairing secrets or killing/restarting the global ADB server.
7. Expose a local health endpoint bound to loopback only; never expose a local unauthenticated control API to the LAN.

The agent must run on the PC host where the existing ADB authorization is available. Running it inside an ordinary Kubernetes Pod would not automatically inherit the Windows ADB server or its trusted key store.

## Controller and browser changes

- Introduce an explicit session backend discriminator: `emulator` or `physical_device`.
- Keep the current emulator provisioning and cleanup path unchanged.
- Add device registration/heartbeat/lease endpoints with strict user and agent authorization; device sessions must not create privileged emulator Pods or KVM hostPath mounts.
- Persist enough session/device ownership metadata to recover leases safely after controller restart.
- Add a physical-device streaming adapter. Do not reuse `android-emulator-webrtc` against a phone: that component expects the emulator WebRTC gateway protocol.
- Keep browser API responses backend-neutral where possible, and render the correct stream adapter based on the returned backend type.
- Return `503 physical_device_unavailable` when no approved, connected, idle device agent is registered; do not silently fall back to an emulator because that would consume the PC resources the owner wants to save.

## Resource and operational policy

- Physical-device mode is opt-in and feature-flagged until accepted.
- Do not change production replica counts, GitOps image tags, DNS, Ingress, or tunnel routing as part of initial development.
- Do not delete emulator manifests or images. Preserve emulator mode as a fallback.
- The Realme phone is a single-device worker with limited memory/battery; enforce one active session and conservative frame-rate/resolution defaults.
- This migration only moves Android execution off the PC. Existing Kubernetes control-plane, databases, and other Linux services remain on the PC unless separately migrated to an independently persistent remote Linux host.

## Required implementation and acceptance gates

1. **Protocol spike:** prove a local agent can use the existing ADB connection to launch scrcpy-server, receive a video stream, and send a touch event without changing device pairing.
2. **Agent security:** tests for device allowlisting, lease exclusivity, credential rejection/revocation, origin restrictions, payload limits, and disconnect cleanup.
3. **Controller:** unit tests for registration, heartbeat, session ownership, lease expiry, recovery, and backend-specific cleanup using fake Kubernetes/agent clients.
4. **Browser:** build and tests for backend selection, connection errors, stop/reconnect behavior, and no emulator component loaded for physical-device sessions.
5. **CI:** Python tests, frontend production build, image builds, Kubernetes render, and security/static checks must pass.
6. **Owner-device test:** use the owner's already-connected Realme device to verify sign-in, live video, touch/key input, APK install/launch, disconnect/reconnect, and session cleanup.
7. **Production rollout:** only after all prior gates pass, deploy behind a feature flag with emulator fallback and documented rollback. Do not scale down or remove existing workloads until the physical path is stable.

## Current verified prerequisites (operator-provided)

- Device: Realme RMX3511, Android 13, device ID RE87BAL1.
- Windows ADB reports the paired Wireless Debugging device as `device`.
- Phone Wi-Fi address at the last check: `192.168.0.103/24`.
- Windows has scrcpy 5.0.1 installed.
- These checks prove local ADB/scrcpy tooling availability only; they do not yet prove browser streaming or Shopnoltd integration.

## External protocol references

- Android Developers: ADB wireless debugging and device pairing: https://developer.android.com/tools/adb
- Android Open Source Project: ADB Wi-Fi TLS architecture: https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/dev/adb_wifi.md
- Genymobile scrcpy project: https://github.com/Genymobile/scrcpy
