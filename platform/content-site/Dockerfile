FROM nginxinc/nginx-unprivileged:1.27-alpine
RUN apk add --no-cache ca-certificates && update-ca-certificates
COPY platform/content-site/nginx.conf /etc/nginx/conf.d/default.conf
COPY platform/content-site/public/ /usr/share/nginx/html/
RUN nginx -t
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
