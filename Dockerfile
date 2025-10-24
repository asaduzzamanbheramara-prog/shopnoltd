# ========================================
# 1️⃣ Build Stage: Composer dependencies
# ========================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend code
COPY backend/ ./

# Ensure directories exist to prevent Composer classmap errors
RUN mkdir -p database/seeders database/factories

# Install Composer dependencies (ignore lock file if needed)
RUN composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader || \
    composer update --no-dev --prefer-dist --no-interaction --optimize-autoloader

# ========================================
# 2️⃣ Final Stage: PHP-FPM + Nginx
# ========================================
FROM php:8.4-fpm-bullseye AS app

# Install system dependencies & PHP extensions
RUN apt-get update && apt-get install -y \
        nginx supervisor git unzip libpng-dev libjpeg-dev libfreetype6-dev \
        libonig-dev libxml2-dev zip curl libicu-dev libpq-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j"$(nproc)" gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /var/www/html

# Copy Laravel backend code
COPY backend/ ./

# Copy vendor dependencies
COPY --from=vendor /app/vendor ./vendor

# Remove default Nginx config and use custom
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisord.conf

# Laravel writable directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache

# Copy real .env file (optional: if you want production values)
COPY backend/.env .env

# Laravel optimizations
RUN php artisan key:generate --force \
    && php artisan config:cache \
    && php artisan route:cache \
    && php artisan view:cache

# Expose web port
EXPOSE 80

# Start Supervisor (Nginx + PHP-FPM)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
