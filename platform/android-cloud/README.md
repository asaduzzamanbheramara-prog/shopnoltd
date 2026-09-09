# Shopnoltd Android Cloud

Browser-accessible Android emulator workspace for Shopnoltd.

## Architecture

- `controller`: authenticated session control-plane API.
- `gateway`: Google Android Emulator WebRTC gateway pinned to a reviewed upstream commit.
- `web`: branded browser workspace using `android-emulator-webrtc`.
- Kubernetes creates an isolated emulator and gateway pair per user session.
- Public ADB is not exposed and arbitrary remote shell execution is not provided.

## Runtime prerequisites

- Linux k3s node with `/dev/kvm` and sufficient emulator CPU/memory capacity.
- `api-service-secret` containing the platform JWT secret available to the controller.
- `android-cloud-turn-secret` provisioned through the cluster secret manager for NAT/firewall-friendly WebRTC when required.
- DNS/tunnel routing for `android.shopnoltd.dpdns.org` and the per-session gateway host.

The current single-node cluster defaults to one active session and cleans up inactive sessions automatically.
