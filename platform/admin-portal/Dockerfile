FROM node:20-alpine AS build
WORKDIR /app
COPY platform/admin-portal/package.json platform/admin-portal/package-lock.json* ./
RUN npm ci || npm install
COPY platform/admin-portal/ ./
RUN npm run build
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY platform/admin-portal/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
HEALTHCHECK CMD wget -qO- http://127.0.0.1:3000/healthz || exit 1
