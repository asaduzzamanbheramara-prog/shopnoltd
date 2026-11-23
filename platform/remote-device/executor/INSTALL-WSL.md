# Install Shopnoltd Executor in WSL2

This installer runs the outbound-only executor as a system-level systemd service inside the current WSL2 distribution. The Windows WSL distribution must be started at boot for the service to reconnect after a Windows restart.

## Requirements

- WSL2 distribution with systemd enabled and running
- Python 3 in WSL
- sudo access
- A pending Cloud Devices record and its fresh one-time enrollment token

## Install

From the platform/remote-device/executor directory, run:

```bash
bash install-wsl.sh '<device-id>'
```

The gateway defaults to https://devices.shopnoltd.dpdns.org. The script asks for the one-time token using hidden terminal input. Do not pass the token as a command-line argument or send it in chat.

The script writes the initial configuration to ~/.config/shopnoltd/executor.json with owner-only permissions, installs agent.py under /opt/shopnoltd/executor, and enables shopnoltd-executor.service. After the first successful enrollment, the executor replaces the initial config with the returned agent ID and HMAC secret and removes the one-time token.

## Verify

```bash
sudo systemctl status shopnoltd-executor
sudo journalctl -u shopnoltd-executor -f
```

The registry should show the device as online only after the executor's enrollment/heartbeat succeeds. A running MeshCentral service is a separate requirement for remote desktop sessions; this executor does not create a MeshCentral node link automatically.
