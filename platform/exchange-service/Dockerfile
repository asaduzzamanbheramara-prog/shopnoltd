FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd -g 10001 shopno && useradd -u 10001 -g shopno -d /app -s /sbin/nologin shopno
WORKDIR /app
COPY platform/exchange-service/requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir --disable-pip-version-check \
    --index-url https://pypi.org/simple \
    -r /app/requirements.txt
COPY platform/exchange-service/app /app/app
COPY shared/libraries/python/shopno_core /app/shopno_core
USER shopno
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen(\"http://127.0.0.1:8080/healthz\").read()"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080","--proxy-headers","--forwarded-allow-ips","*"]

