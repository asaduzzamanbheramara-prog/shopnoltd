# Shopnoltd PC Executor

Outbound-only Shopnoltd host executor for Shopnoltd-PC-1 and supported desktop hosts.

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

The executor loop continues to send heartbeats and retry transient network
failures. Running it as an OS-managed service/startup task is still required
for unattended operation after reboot; this change does not install or
configure that service.

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
