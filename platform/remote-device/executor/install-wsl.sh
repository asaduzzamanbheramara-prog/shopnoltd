#!/usr/bin/env bash
set -euo pipefail

# Install the Shopnoltd outbound executor as a systemd service inside WSL.
# The one-time pairing code is requested with hidden input and is never
# accepted as a command-line argument or printed to the terminal.

DEVICE_ID="${1:-}"
GATEWAY_URL="${2:-https://devices.shopnoltd.dpdns.org}"

if [[ -z "$DEVICE_ID" || ! "$DEVICE_ID" =~ ^[A-Za-z0-9_-]{10,100}$ ]]; then
  echo "Usage: $0 <device-id> [https://devices.shopnoltd.dpdns.org]" >&2
  exit 2
fi
if [[ "$GATEWAY_URL" != https://* ]]; then
  echo "The gateway URL must use HTTPS." >&2
  exit 2
fi
if [[ "$(id -u)" -eq 0 ]]; then
  echo "Run this installer as the normal WSL user, not root." >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required inside WSL." >&2
  exit 1
fi
if ! systemctl is-system-running >/dev/null 2>&1; then
  echo "WSL systemd is not running. Enable systemd in /etc/wsl.conf and restart WSL." >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AGENT_SOURCE="$SCRIPT_DIR/agent.py"
if [[ ! -f "$AGENT_SOURCE" ]]; then
  echo "agent.py must be in the same directory as this installer." >&2
  exit 1
fi

CONFIG_DIR="$HOME/.config/shopnoltd"
CONFIG_FILE="$CONFIG_DIR/executor.json"
SERVICE_NAME="shopnoltd-executor"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
INSTALL_DIR="/opt/shopnoltd/executor"
USER_NAME="$(id -un)"
GROUP_NAME="$(id -gn)"
HOME_DIR="$HOME"

install -d -m 0700 "$CONFIG_DIR"
chmod 0700 "$CONFIG_DIR"

python3 - "$CONFIG_FILE" "$DEVICE_ID" "$GATEWAY_URL" <<'PY'
import getpass
import json
import os
import socket
import sys
import urllib.request
from pathlib import Path

path, device_id, gateway_url = sys.argv[1:]
pairing_secret = getpass.getpass("Paste the one-time Shopnoltd pairing code (input hidden): ").strip()
if len(pairing_secret) < 20:
    raise SystemExit("Pairing code is missing or too short.")
payload = json.dumps({
    "pairing_secret": pairing_secret,
    "hostname": socket.gethostname(),
    "platform": "linux",
    "agent_version": "2.1",
}).encode()
request = urllib.request.Request(
    gateway_url.rstrip("/") + "/api/pairing/consume",
    data=payload,
    headers={"Content-Type": "application/json", "Accept": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=20) as response:
        pairing = json.loads(response.read().decode("utf-8"))
except Exception as exc:
    raise SystemExit(f"Pairing failed: {exc}") from exc
token = pairing.get("enrollment_token")
if not isinstance(token, str) or len(token) < 10:
    raise SystemExit("Pairing service did not return an enrollment grant.")
config = {
    "gateway_url": gateway_url.rstrip("/"),
    "device_id": device_id,
    "enrollment_token": token,
}
target = Path(path)
temporary = target.with_name(target.name + ".tmp")
fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(config, stream, indent=2)
        stream.write("\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
finally:
    try:
        temporary.unlink()
    except FileNotFoundError:
        pass
PY
chmod 0600 "$CONFIG_FILE"

sudo install -d -m 0755 "$INSTALL_DIR"
sudo install -m 0644 "$AGENT_SOURCE" "$INSTALL_DIR/agent.py"

SERVICE_TMP="$(mktemp)"
cat > "$SERVICE_TMP" <<UNIT
[Unit]
Description=Shopnoltd Cloud Device Executor
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$USER_NAME
Group=$GROUP_NAME
WorkingDirectory=$HOME_DIR
Environment=SHOPNOLTD_EXECUTOR_CONFIG=$CONFIG_FILE
UMask=0077
ExecStart=/usr/bin/python3 $INSTALL_DIR/agent.py
Restart=always
RestartSec=15
RestartPreventExitStatus=78
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
UNIT

sudo install -m 0644 "$SERVICE_TMP" "$SERVICE_FILE"
rm -f "$SERVICE_TMP"
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"

echo
echo "Shopnoltd Executor service installed and started."
echo "Service: $SERVICE_NAME"
echo "Config:  $CONFIG_FILE (owner-only permissions)"
echo "Check:   sudo systemctl status $SERVICE_NAME"
echo "Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "The one-time token is removed automatically after successful enrollment."
