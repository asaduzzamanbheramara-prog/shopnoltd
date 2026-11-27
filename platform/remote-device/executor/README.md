# Shopnoltd Device Executor

Outbound-only Shopnoltd host executor for supported Windows/Linux/macOS desktop hosts and an experimental Termux-based Android lightweight agent.

The executor does not expose an inbound network listener. It polls the Shopnoltd Remote Device Gateway over HTTPS and executes only explicitly allowlisted operations.

## Device profile reporting

Every enrollment/heartbeat can report a single unified profile containing:

- hostname and operating-system profile
- platform/family information
- local interface IP addresses
- observed public/egress IP address
- detected VPN interface/IP addresses when the VPN is visible to the host
- detected VPN provider/interface name when identifiable
- agent version and last-seen timestamp

The browser device console displays the public IP, local IPs and VPN IPs together for each authorized device. IP values are sanitized as valid IP addresses by the registry before storage/display.

A VPN IP is only reported when the VPN interface is visible to the host. A public IP is the observed HTTPS egress address; it may therefore be the VPN exit IP when traffic is routed through a VPN.

## Automatic first enrollment and reconnect

On first start, the executor submits its one-time enrollment token, validates the
response, writes the returned `agent_id` and HMAC secret to its configuration
file, removes the one-time token, and continues directly into the heartbeat/job
poll loop. It no longer exits after a successful first enrollment.

Before consuming the one-time token, the executor restricts the configuration
directory. On Windows it grants access only to LocalSystem and the local
Administrators group; on POSIX systems it uses directory mode `0700` and file
mode `0600`. The credential file is replaced atomically. If secure persistence
fails after the server consumes the token, revoke/reissue the enrollment token
before retrying because the server returns the HMAC secret only once.

The executor loop continues to send heartbeats and retry transient network failures. The Windows installer registers a per-user logon task; the WSL installer registers a systemd service. Termux can restart the lightweight Android agent after reboot when the optional Termux:Boot add-on is installed and Android permits background activity.

## Installers and Android scope

- Windows: run `install-windows.ps1` from an elevated PowerShell session. It downloads the agent, requests the one-time token through a hidden prompt, restricts the credential file with Windows ACLs, and registers a per-user logon task.
- WSL: use `install-wsl.sh` when WSL systemd is enabled and the agent source is beside the installer.
- Android: `install-termux.sh` is an experimental lightweight Termux path. It installs Python, requests the one-time token through a hidden prompt, stores credentials with owner-only permissions, and starts a low-frequency heartbeat/job poll. Install Termux:Boot separately if restart-after-reboot is needed, and exempt Termux from Android battery optimization.
- Android Termux support is inventory/heartbeat/approved diagnostics only. It does not provide screen capture, remote input, accessibility control, or a native Android foreground service.
- Remote desktop screen sessions remain a separate MeshCentral capability and require the platform-specific MeshCentral agent and explicit user authorization.

## Security

- no inbound listener
- no arbitrary shell command execution
- fixed read-only operation allowlist
- one job at a time
- bounded execution time
- HTTPS gateway communication
- HMAC authenticated requests
- timestamp + nonce replay protection
- one-time enrollment token

## Initial operations

- system.info
- windows.info
- wsl.info
- k3s.info
- k8s.pods
- k8s.services
- git.status
- shopnoltd.health
- disk.status
- memory.status
- remote-device.status
