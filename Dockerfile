# -----------------------------------------------------------------------------
# Shopnoltd Platform API
# Production Dockerfile
# -----------------------------------------------------------------------------

FROM python:3.12-slim

LABEL maintainer="Shopno Database Firm"
LABEL application="Shopnoltd Platform API"
LABEL version="1.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    BRAND_NAME=Shopnoltd \
    COMPANY_NAME="Shopno Database Firm"

WORKDIR /workspace

# -----------------------------------------------------------------------------
# Install required OS packages
# -----------------------------------------------------------------------------

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Install Python packages
# -----------------------------------------------------------------------------

COPY requirements.txt .

RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Copy application
# -----------------------------------------------------------------------------

COPY app_platform ./app_platform

# -----------------------------------------------------------------------------
# Create non-root user
# -----------------------------------------------------------------------------

RUN useradd --create-home --uid 1000 --shell /bin/bash shopno && \
    chown -R shopno:shopno /workspace

USER shopno

# -----------------------------------------------------------------------------
# Network
# -----------------------------------------------------------------------------

EXPOSE 8000

# -----------------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------------

HEALTHCHECK --interval=30s \
            --timeout=5s \
            --start-period=20s \
            --retries=3 \
CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# -----------------------------------------------------------------------------
# Start API
# -----------------------------------------------------------------------------

CMD [
  "uvicorn",
  "app_platform.api.main:app",
  "--host",
  "0.0.0.0",
  "--port",
  "8000",
  "--proxy-headers",
  "--forwarded-allow-ips=*"
]
