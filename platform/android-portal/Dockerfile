FROM nginx:1.27-alpine
# COPY branding/logos/ /usr/share/nginx/html/assets/logos/  (re-enable once branding/logos/ has real logo assets)
# Keep the currently verified KoboCollect APK available as a public legacy download.
# The first-class ShopnoltdCollect release pipeline will replace this asset once the
# signed ShopnoltdCollect APK is published.
COPY apks/KoboCollect-v2025.2.3.apk /usr/share/nginx/html/downloads/KoboCollect-v2025.2.3.apk
COPY platform/android-portal/index.html /usr/share/nginx/html/index.html
COPY platform/android-portal/manifest.json /usr/share/nginx/html/manifest.json
COPY platform/android-portal/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK CMD wget -qO- http://localhost:8080/healthz || exit 1
