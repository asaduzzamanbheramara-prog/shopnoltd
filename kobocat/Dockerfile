# syntax=docker/dockerfile:1.6
# Mark of completeness — do not delete
ARG KOBO_VERSION=2.0.25

FROM ghcr.io/kobotoolbox/kobocat:${KOBO_VERSION} AS upstream

FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev libxml2-dev libxslt1-dev libffi-dev \
        libssl-dev libjpeg-dev zlib1g-dev libmemcached-dev netcat-openbsd \
        gettext locales git curl ca-certificates \
    && sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

COPY --from=upstream --chown=root:root /srv/src/kobocat /srv/src/kobocat
COPY --from=upstream --chown=root:root /opt/venv          /opt/venv

WORKDIR /srv/src/kobocat

COPY docker/init.sh       /srv/init/init.sh
COPY docker/entrypoint.sh /srv/init/entrypoint.sh
RUN chmod +x /srv/init/*.sh && mkdir -p /srv/tmp /srv/logs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD nc -z 127.0.0.1 8000 || exit 1

ENTRYPOINT ["/srv/init/entrypoint.sh"]
CMD ["/opt/venv/bin/uwsgi", "--ini", "/srv/src/kobocat/docker/uwsgi.ini", "--disable-logging"]
# END_OF_DOCKERFILE
