FROM python:3.12-slim

ARG AEMU_REPO=https://github.com/google/android-emulator-container-scripts.git
ARG AEMU_REF=master

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/aemu
RUN git clone --depth 1 --branch "${AEMU_REF}" "${AEMU_REPO}" . \
    && pip install --no-cache-dir ./gateway

COPY entrypoint.sh /usr/local/bin/android-cloud-gateway
RUN chmod 0755 /usr/local/bin/android-cloud-gateway \
    && useradd --system --uid 10001 --create-home gateway

USER 10001
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/android-cloud-gateway"]
