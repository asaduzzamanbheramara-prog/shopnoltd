# ================================
# Stage 1: Composer dependencies
# ================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend Laravel project
COPY . ./

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

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nginx supervisor git unzip libzip-dev zip gettext \
    && docker-php-ext-install pdo pdo_mysql \
    && rm -rf /var/lib/apt/lists/*

# Configure PHP-FPM to use socket
RUN if [ -f /usr/local/etc/php-fpm.d/www.conf ]; then \
      sed -i 's|^listen = .*|listen = /run/php/php8.2-fpm.sock|' /usr/local/etc/php-fpm.d/www.conf; \
    fi

# Copy Nginx & Supervisor configs
COPY backend/docker/default.conf.template /etc/nginx/conf.d/default.conf.template
COPY backend/docker/supervisord.conf /etc/docker/supervisord.conf

# Laravel .env setup and permissions
RUN if [ ! -f .env ]; then \
      cp .env.example .env && \
      sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
      sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env; \
    fi \
 && php artisan key:generate --force \
 && mkdir -p storage/logs \
 && touch storage/logs/laravel.log \
 && chown -R www-data:www-data /app/storage /app/bootstrap/cache \
 && chmod -R 755 /app/storage /app/bootstrap/cache

# Render dynamic port (fallback)
ENV PORT=8080
EXPOSE 8080

# Copy startup script
COPY backend/docker/start.sh /start.sh
RUN chmod +x /start.sh

# Start Supervisor via startup script
CMD ["/start.sh"]
