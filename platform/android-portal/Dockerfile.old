FROM nginx:1.27-alpine
# COPY branding/logos/ /usr/share/nginx/html/assets/logos/  (re-enable once branding/logos/ has real logo assets)
# COPY mobile/release/  /usr/share/nginx/html/downloads/  (re-enable once mobile/release/ has real APK/IPA files)
COPY platform/android-portal/index.html /usr/share/nginx/html/index.html
COPY platform/android-portal/manifest.json /usr/share/nginx/html/manifest.json
COPY platform/android-portal/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK CMD wget -qO- http://localhost:8080/healthz || exit 1
