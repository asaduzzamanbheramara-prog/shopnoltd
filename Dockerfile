# =========================
# 1️⃣ Build Stage: Composer dependencies
# =========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy composer files first to leverage caching
COPY backend/composer.json backend/composer.lock ./

# Create empty directories Laravel expects
RUN mkdir -p database/seeders database/factories

# Install dependencies; if lock is outdated, update automatically
RUN composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader || \
    composer update --no-dev --prefer-dist --no-interaction --optimize-autoloader

# Copy the full Laravel app
COPY backend/ ./

# =========================
# 2️⃣ Final Stage: PHP-FPM + Nginx
# =========================
FROM php:8.2-fpm-bullseye

# Prevent interactive prompts during apt install
ARG DEBIAN_FRONTEND=noninteractive

# Install system dependencies and PHP extensions
RUN apt-get update && apt-get install -y \
    nginx git unzip libpng-dev libjpeg-dev libfreetype6-dev \
    libonig-dev libxml2-dev zip curl libicu-dev libpq-dev \
    supervisor \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Laravel app and vendor from build stage
COPY --from=vendor /app /app

# Remove default Nginx configs and use custom ones
RUN rm -rf /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# Copy PHP-FPM and supervisor configs
COPY docker/php-fpm.conf /usr/local/etc/php-fpm.d/www.conf
COPY docker/supervisord.conf /etc/supervisord.conf

# Create Laravel storage and cache directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache /var/log/php-fpm \
    && chown -R www-data:www-data storage bootstrap/cache /var/log/php-fpm

# Expose ports
EXPOSE 80 9000

# Start supervisord to manage PHP-FPM + Nginx
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisord.conf"]
