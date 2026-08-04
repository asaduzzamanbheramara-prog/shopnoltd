FROM postgis/postgis:16-3.5

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       git \
       postgresql-server-dev-16 \
    && git clone --branch v0.8.6 --depth 1 \
       https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make \
    && make install \
    && rm -rf /tmp/pgvector \
    && apt-get purge -y \
       build-essential \
       git \
       postgresql-server-dev-16 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

USER postgres
