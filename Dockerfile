# ================================
# Stage 1: Composer dependencies
# ================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend Laravel project
COPY backend/ ./

# Ensure directories exist
RUN mkdir -p database/seeders database/factories

# Install PHP dependencies
RUN composer install --no-dev --optimize-autoloader --no-interaction --prefer-dist

# ================================
# Stage 2: PHP-FPM + Nginx
# ================================
FROM php:8.2-fpm-bullseye

WORKDIR /app

# Copy code & vendor deps from previous stage
COPY --from=vendor /app /app

# Install system dependencies, including envsubst (gettext-base)
RUN apt-get update && apt-get install -y \
    nginx supervisor git unzip libzip-dev zip gettext-base \
    && docker-php-ext-install pdo pdo_mysql \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------
# ✅ PHP-FPM configuration (socket-based)
# -----------------------------------------------------
RUN if [ -f /usr/local/etc/php-fpm.d/www.conf ]; then \
      sed -i 's|^listen = .*|listen = /run/php/php8.2-fpm.sock|' /usr/local/etc/php-fpm.d/www.conf; \
    fi

# -----------------------------------------------------
# ✅ Copy Nginx & Supervisor configs
# -----------------------------------------------------
COPY backend/docker/default.conf.template /etc/nginx/conf.d/default.conf.template
COPY backend/docker/supervisord.conf /etc/docker/supervisord.conf

# Substitute PORT in Nginx config
RUN envsubst '$PORT' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# -----------------------------------------------------
# ✅ Ensure .env and APP_KEY
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
# ✅ Dynamic port support for Render
# -----------------------------------------------------
ENV PORT=10000
EXPOSE 10000

# -----------------------------------------------------
# ✅ Start Supervisor (manages Nginx + PHP-FPM)
# -----------------------------------------------------
CMD ["/usr/bin/supervisord", "-c", "/etc/docker/supervisord.conf"]
