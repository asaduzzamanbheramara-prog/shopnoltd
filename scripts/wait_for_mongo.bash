#!/bin/bash
set -e
HOST="${MONGO_HOST:-mongo}"
# Note: intentionally NOT reading $MONGO_PORT here -- Kubernetes auto-injects
# a MONGO_PORT env var for the "mongo" Service (e.g. tcp://10.x.x.x:27017),
# which collides with and overrides any value we'd want to default to.
PORT=27017
echo "Waiting for MongoDB at ${HOST}:${PORT}..."
for i in $(seq 1 60); do
  if (echo > /dev/tcp/${HOST}/${PORT}) >/dev/null 2>&1; then
    echo "MongoDB is up."
    exit 0
  fi
  sleep 2
done
echo "Timed out waiting for MongoDB at ${HOST}:${PORT}."
exit 1
