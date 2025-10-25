# =========================
# 1️⃣ Build stage: Composer
# =========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy full backend code first (includes artisan)
COPY backend/ ./

# Ensure folders exist to avoid classmap errors
RUN mkdir -p database/seeders database/factories

# Install dependencies
RUN composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader || \
    composer update --no-dev --prefer-dist --no-interaction --optimize-autoloader

# =========================
# 2️⃣ Final stage: PHP-FPM + Nginx
# =========================
FROM php:8.2-fpm-bullseye

WORKDIR /app

# Install system dependencies and PHP extensions
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    nginx git unzip libpng-dev libjpeg-dev libfreetype6-dev \
    libonig-dev libxml2-dev zip curl libicu-dev libpq-dev supervisor \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy app and vendor from build stage
COPY --from=vendor /app /app

# Nginx configuration
RUN rm -rf /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# PHP-FPM config
COPY docker/php-fpm.conf /usr/local/etc/php-fpm.d/www.conf

# Supervisor config
COPY docker/supervisord.conf /etc/supervisord.conf

# Fix permissions
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache && \
    chown -R www-data:www-data storage bootstrap/cache /var/log/php-fpm

# Laravel environment
RUN if [ ! -f .env ]; then cp .env.example .env; fi
RUN php artisan key:generate --force || true

# Expose HTTP port
EXPOSE 80

# Start all services via supervisor
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisord.conf"]
