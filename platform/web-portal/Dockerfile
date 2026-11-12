FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_API_URL=https://api.shopnoltd.dpdns.org
ARG VITE_API_BASE_URL=https://api.shopnoltd.dpdns.org
ARG VITE_API_BASE=https://api.shopnoltd.dpdns.org
ARG VITE_KEYCLOAK_URL=https://auth.shopnoltd.dpdns.org
ARG VITE_KEYCLOAK_REALM=shopnoltd
ARG VITE_KEYCLOAK_CLIENT_ID=shopnoltd-web
ARG VITE_SOCIAL_LOGIN_GOOGLE=false
ARG VITE_SOCIAL_LOGIN_FACEBOOK=false
ARG VITE_SOCIAL_LOGIN_GITHUB=false
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_BASE=$VITE_API_BASE
ENV VITE_KEYCLOAK_URL=$VITE_KEYCLOAK_URL
ENV VITE_KEYCLOAK_REALM=$VITE_KEYCLOAK_REALM
ENV VITE_KEYCLOAK_CLIENT_ID=$VITE_KEYCLOAK_CLIENT_ID
ENV VITE_SOCIAL_LOGIN_GOOGLE=$VITE_SOCIAL_LOGIN_GOOGLE
ENV VITE_SOCIAL_LOGIN_FACEBOOK=$VITE_SOCIAL_LOGIN_FACEBOOK
ENV VITE_SOCIAL_LOGIN_GITHUB=$VITE_SOCIAL_LOGIN_GITHUB
COPY platform/web-portal/package.json platform/web-portal/package-lock.json* ./
RUN npm ci || npm install
COPY platform/web-portal/ ./
RUN npm run build
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY platform/web-portal/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
HEALTHCHECK CMD wget -qO- http://127.0.0.1:3000/healthz || exit 1
