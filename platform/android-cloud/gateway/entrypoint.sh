#!/bin/sh
set -eu

mkdir -p /tmp/android-emulator
printf '%s\n' "grpc.port=8554" > /tmp/android-emulator/discovery.ini

if [ -n "${GRPC_TOKEN:-}" ]; then
  printf '%s\n' "grpc.token=${GRPC_TOKEN}" >> /tmp/android-emulator/discovery.ini
fi

exec videobridge-gateway \
  --port=8080 \
  --discovery_file=/tmp/android-emulator/discovery.ini
