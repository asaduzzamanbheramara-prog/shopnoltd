# Shopnoltd Android Cloud

Shopnoltd Android Cloud provides a browser-accessible Android device workspace backed by the official Android Emulator container runtime and Google's WebRTC gateway.

## Architecture

```text
Browser
  -> https://android.shopnoltd.dpdns.org
  -> Shopnoltd Android Cloud UI
  -> Android Cloud Controller (authenticated session API)
       -> ephemeral Android Emulator pod (/dev/kvm)
       -> per-session WebRTC Gateway pod
            -> Android Emulator gRPC :8554
  -> WebRTC media/data -> Browser
```

The Android Emulator container exposes gRPC/WebRTC on 8554 and ADB on 5555. The browser uses the `android-emulator-webrtc` client and the gateway translates HTTP/WebSocket signaling to the emulator's native gRPC RTC service.

## Security model

- Every session is bound to the authenticated Shopnoltd JWT subject.
- Session IDs are high-entropy opaque identifiers and are never Kubernetes names supplied by users.
- The controller only creates/deletes pods and services in the dedicated `shopno-android` namespace.
- Emulator ADB and gRPC ports are cluster-internal; they are never exposed by an Ingress.
- The emulator pod is isolated by NetworkPolicy.
- Arbitrary remote shell execution is not exposed by the controller.
- APK installation is handled through the authenticated device workspace rather than embedding merchant/payment secrets in an APK.
- Default capacity is one active emulator session on the current single-node cluster. Increase only after KVM, CPU, RAM, and storage capacity are verified.

## WebRTC / TURN

The emulator's WebRTC media path is peer-to-peer after signaling. A public TURN service is therefore recommended for users behind NAT/firewalls. The controller accepts `ANDROID_CLOUD_TURN_URLS`, `ANDROID_CLOUD_TURN_USERNAME`, and `ANDROID_CLOUD_TURN_CREDENTIAL` and passes the configured ICE/TURN information to the browser workspace.

Cloudflare Realtime TURN supports UDP, TCP, and TLS TURN transports. Configure its temporary credentials as Kubernetes secrets rather than committing them to Git.

## Runtime requirements

The official Google emulator container images require Linux/KVM. Docker Desktop on Windows/macOS is not a supported KVM runtime for these hosted emulator containers. The Shopnoltd k3s node therefore needs `/dev/kvm` available to the Kubernetes workload.

## Initial device profile

- Android API 30 Google image
- x86_64
- 2 vCPU request / 4 vCPU limit
- 3 GiB memory request / 4 GiB limit
- 8 GiB ephemeral storage
- no public ADB
- one active session on the current single-node cluster
- automatic cleanup after 30 minutes of inactivity

The hosted image is pinned to Google's published `30-google-x64:30.1.2` image.

## Current deployment boundary

The GitOps manifests and controller/UI are included here, but the first rollout must pass a node preflight for `/dev/kvm` and WebRTC/TURN connectivity. If KVM is unavailable, the Android Cloud service must report capacity unavailable rather than pretending that an ordinary Kubernetes container is a physical Android device.
