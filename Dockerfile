# ================================
# Stage 1: Composer dependencies
# ================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy Laravel backend project
COPY backend/ ./

# Ensure required directories exist
RUN mkdir -p database/seeders database/factories

# Install PHP dependencies
RUN composer install --no-dev --optimize-autoloader --no-interaction --prefer-dist

# ================================
# Stage 2: PHP-FPM + Nginx
# ================================
FROM php:8.2-fpm-bullseye

WORKDIR /app

# Copy code and vendor deps from previous stage
COPY --from=vendor /app /app

# -----------------------------------------------------
# ✅ Install system dependencies
# -----------------------------------------------------
RUN apt-get update && apt-get install -y \
    nginx supervisor git unzip libzip-dev zip gettext-base \
    && docker-php-ext-install pdo pdo_mysql \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------
# ✅ Configure PHP-FPM to use socket
# -----------------------------------------------------
RUN if [ -f /usr/local/etc/php-fpm.d/www.conf ]; then \
      sed -i 's|^listen = .*|listen = /run/php/php8.2-fpm.sock|' /usr/local/etc/php-fpm.d/www.conf; \
    fi

# -----------------------------------------------------
# ✅ Nginx configuration
# -----------------------------------------------------
RUN echo "env PORT;" >> /etc/nginx/nginx.conf
COPY backend/docker/default.conf /etc/nginx/conf.d/default.conf

# Supervisor config
COPY backend/docker/supervisord.conf /etc/docker/supervisord.conf

# -----------------------------------------------------
# ✅ Laravel environment & permissions
# -----------------------------------------------------
RUN if [ ! -f .env ]; then \
      cp .env.example .env && \
      sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
      sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env; \
    fi \
 && php artisan key:generate --force \
 && chown -R www-data:www-data /app/storage /app/bootstrap/cache \
 && chmod -R 755 /app/storage /app/bootstrap/cache

# -----------------------------------------------------
# ✅ Dynamic port for Render
# -----------------------------------------------------
ENV PORT=10000
EXPOSE 10000

# -----------------------------------------------------
# ✅ Robust startup command
# (substitutes $PORT into Nginx config before start)
# -----------------------------------------------------
CMD sh -c "\
  envsubst '\$PORT' < /etc/nginx/conf.d/default.conf > /etc/nginx/conf.d/default_runtime.conf && \
  mv /etc/nginx/conf.d/default_runtime.conf /etc/nginx/conf.d/default.conf && \
  mkdir -p /run/php && \
  /usr/bin/supervisord -c /etc/docker/supervisord.conf \
"
