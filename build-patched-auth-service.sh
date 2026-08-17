#!/bin/bash
# Fix auth-service startup issue
# This script patches the auth-service image to handle database connection gracefully

set -e

PROJECT_DIR="${1:-.}"
DOCKER_IMAGE="ghcr.io/asaduzzamanbheramara-prog/shopnoltd/auth-service"
IMAGE_TAG="${2:-latest}"

echo "Building patched auth-service image..."

# Create temporary build directory
BUILD_DIR=$(mktemp -d)
trap "rm -rf $BUILD_DIR" EXIT

# Copy the fixed main.py
cp "${PROJECT_DIR}/auth-service-main-FIXED.py" "${BUILD_DIR}/main.py"

# Create Dockerfile for patching
cat > "${BUILD_DIR}/Dockerfile" << 'EOF'
ARG BASE_IMAGE=ghcr.io/asaduzzamanbheramara-prog/shopnoltd/auth-service:latest
FROM ${BASE_IMAGE}

# Copy the fixed main.py
COPY main.py /app/app/main.py

# Ensure permissions
RUN chown -R shopno:shopno /app/app/main.py && \
    chmod 644 /app/app/main.py

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
EOF

# Build the patched image
docker build -t "${DOCKER_IMAGE}:fixed" \
  --build-arg BASE_IMAGE="${DOCKER_IMAGE}:${IMAGE_TAG}" \
  "${BUILD_DIR}"

echo "Patched image built: ${DOCKER_IMAGE}:fixed"
echo ""
echo "To use the patched image:"
echo "1. Tag it for push: docker tag ${DOCKER_IMAGE}:fixed ${DOCKER_IMAGE}:fixed-$(date +%s)"
echo "2. Push to registry: docker push ${DOCKER_IMAGE}:fixed-\$(date +%s)"
echo "3. Update Kubernetes deployment to use the new tag"
