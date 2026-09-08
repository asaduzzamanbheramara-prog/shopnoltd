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
