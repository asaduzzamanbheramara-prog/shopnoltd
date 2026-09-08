#!/usr/bin/env bash
set -euo pipefail

# Provision the VPN admin token into Kubernetes without committing it to Git.
# The token is read only from the environment and is never echoed.
: "${VPN_ADMIN_TOKEN:?Set VPN_ADMIN_TOKEN in the shell before running this script}"

encoded_token="$(printf '%s' "$VPN_ADMIN_TOKEN" | base64 -w0)"

cat <<EOF | kubectl -n shopno-apps apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: vpn-service-secret
type: Opaque
data:
  admin-token: ${encoded_token}
EOF

unset VPN_ADMIN_TOKEN
printf '%s\n' 'vpn-service-secret provisioned in namespace shopno-apps.'
