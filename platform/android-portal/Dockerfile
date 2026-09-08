FROM nginx:1.27-alpine
# ShopnoltdCollect is published by the Android CI release pipeline. The portal
# exposes a stable Shopnoltd URL and redirects to the current public release asset.
COPY platform/android-portal/index.html /usr/share/nginx/html/index.html
COPY platform/android-portal/manifest.json /usr/share/nginx/html/manifest.json
COPY platform/android-portal/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK CMD wget -qO- http://localhost:8080/healthz || exit 1
