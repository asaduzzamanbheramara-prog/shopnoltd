FROM python:3.11-slim

WORKDIR /app

# System deps required by Playwright's bundled Chromium, plus a virtual
# display + VNC stack so sessions can be watched/interacted with live
# instead of running strictly headless.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gnupg ca-certificates fonts-liberation \
    libnss3 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 \
    xvfb x11vnc novnc websockify \
    && rm -rf /var/lib/apt/lists/*

# NOTE: build context is the repo root (see build-platform.yml: context: .)
# so every COPY below is relative to the repo root, not this folder.
COPY platform/session-manager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium --with-deps

# Bring in the shared branding assets so the UI can reference them
COPY platform/session-manager/branding/ /app/app/static/branding/

COPY platform/session-manager/app/ /app/app/
COPY platform/session-manager/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PROFILE_STORAGE_ROOT=/data
ENV DISPLAY=:99
VOLUME ["/data"]

EXPOSE 8000 6080

ENTRYPOINT ["/entrypoint.sh"]
