FROM node:20-alpine AS build
WORKDIR /src
COPY platform/android-cloud/web/package.json ./package.json
RUN npm install --no-audit --no-fund
COPY platform/android-cloud/web/vite.config.js ./vite.config.js
COPY platform/android-cloud/web/index.html ./index.html
COPY platform/android-cloud/web/src ./src
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /src/dist /usr/share/nginx/html
COPY platform/android-cloud/web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/healthz >/dev/null || exit 1
