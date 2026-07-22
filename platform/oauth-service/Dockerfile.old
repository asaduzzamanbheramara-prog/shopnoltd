FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd -g 10001 shopno && useradd -u 10001 -g shopno -d /app -s /sbin/nologin shopno
WORKDIR /app
COPY platform/oauth-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY platform/oauth-service/app /app/app
COPY shared/libraries/python /app/shared
USER shopno
EXPOSE 3000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:3000/healthz').read()"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","3000","--proxy-headers","--forwarded-allow-ips","*"]
