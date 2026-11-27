#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

DEVICE_ID="${1:-}"
GATEWAY_URL="${2:-https://devices.shopnoltd.dpdns.org}"

if [[ -z "${PREFIX:-}" || "$PREFIX" != *"/com.termux/"* ]]; then
  echo "Run this installer inside the Termux app on the Android device." >&2
  exit 2
fi
if [[ -z "$DEVICE_ID" || ! "$DEVICE_ID" =~ ^[A-Za-z0-9_-]{10,100}$ ]]; then
  echo "Usage: $0 <device-id> [https://devices.shopnoltd.dpdns.org]" >&2
  exit 2
fi
if [[ "$GATEWAY_URL" != https://* ]]; then
  echo "The Shopnoltd gateway must use HTTPS." >&2
  exit 2
fi

pkg update -y
pkg install -y python curl coreutils

INSTALL_DIR="$HOME/.local/share/shopnoltd-executor"
CONFIG_DIR="$HOME/.config/shopnoltd"
CONFIG_FILE="$CONFIG_DIR/executor.json"
AGENT_SOURCE="$INSTALL_DIR/agent.py"
LOG_FILE="$HOME/shopnoltd-executor.log"
BOOT_DIR="$HOME/.termux/boot"

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"
chmod 0700 "$CONFIG_DIR"
AGENT_URL="https://raw.githubusercontent.com/asaduzzamanbheramara-prog/shopnoltd/main/platform/remote-device/executor/agent.py"
curl --fail --silent --show-error --location "$AGENT_URL" -o "$AGENT_SOURCE"
EXPECTED_AGENT_SHA256="c821f33ce4d9650d042b2ee091e64edf02283c161013fc337fa5bc0294825608"
ACTUAL_AGENT_SHA256="$(sha256sum "$AGENT_SOURCE")"
ACTUAL_AGENT_SHA256="${ACTUAL_AGENT_SHA256%% *}"
if [[ "$ACTUAL_AGENT_SHA256" != "$EXPECTED_AGENT_SHA256" ]]; then
  rm -f "$AGENT_SOURCE"
  echo "Downloaded Shopnoltd agent failed its SHA-256 integrity check." >&2
  exit 1
fi
chmod 0700 "$AGENT_SOURCE"

python3 - "$CONFIG_FILE" "$DEVICE_ID" "$GATEWAY_URL" <<'PY'
import getpass
import json
import os
import sys
from pathlib import Path

path, device_id, gateway_url = sys.argv[1:]
token = getpass.getpass("Paste the one-time Shopnoltd enrollment token (input hidden): ").strip()
if len(token) < 10:
    raise SystemExit("Enrollment token is missing or too short.")
target = Path(path)
temporary = target.with_name(target.name + ".tmp")
config = {
    "gateway_url": gateway_url.rstrip("/"),
    "device_id": device_id,
    "enrollment_token": token,
}
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

mkdir -p "$BOOT_DIR"
chmod 0700 "$BOOT_DIR"
cat > "$BOOT_DIR/shopnoltd-executor.sh" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
nohup env SHOPNOLTD_EXECUTOR_CONFIG="$CONFIG_FILE" SHOPNOLTD_POLL_SECONDS=30 SHOPNOLTD_HEARTBEAT_SECONDS=120 python3 "$AGENT_SOURCE" >> "$LOG_FILE" 2>&1 &
EOF
chmod 0700 "$BOOT_DIR/shopnoltd-executor.sh"

# Start the same lightweight agent now; Termux:Boot can restart it after reboot.
nohup env SHOPNOLTD_EXECUTOR_CONFIG="$CONFIG_FILE" SHOPNOLTD_POLL_SECONDS=30 SHOPNOLTD_HEARTBEAT_SECONDS=120 python3 "$AGENT_SOURCE" >> "$LOG_FILE" 2>&1 &
echo $! > "$INSTALL_DIR/agent.pid"

echo
echo "Shopnoltd Android lightweight agent started."
echo "Heartbeat target: $GATEWAY_URL"
echo "Logs: $LOG_FILE"
echo "For restart after reboot, install and open the official Termux:Boot add-on once."
echo "Allow Termux background activity in Android battery settings."
echo "This agent reports health/network diagnostics only; it does not capture or control the Android screen."
