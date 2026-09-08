FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends wireguard-tools iproute2 iptables procps && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY services/vpn-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY services/vpn-service/api ./api
RUN mkdir -p /data
EXPOSE 8080 51820/udp
CMD ["uvicorn","api.main:app","--host","0.0.0.0","--port","8080"]
