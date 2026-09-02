# Shopnoltd PC Executor

Outbound-only Shopnoltd host executor for Shopnoltd-PC-1.

The executor does not expose an inbound network listener.

It polls the Shopnoltd Remote Device Gateway over HTTPS and executes
only explicitly allowlisted operations.

Initial operations are read-only:

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

No arbitrary shell command execution is supported.
