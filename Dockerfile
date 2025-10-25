# =========================================
# 1️⃣ Build Stage: Composer dependencies
# =========================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend code
COPY backend/ ./

# Ensure required dirs exist for Laravel
RUN mkdir -p database/seeders database/factories storage/framework storage/logs bootstrap/cache

# Install dependencies
RUN composer install --no-dev --no-interaction --prefer-dist --optimize-autoloader


# =========================================
# 2️⃣ Runtime Stage: PHP + Nginx + Supervisor
# =========================================
FROM php:8.2-fpm-bullseye

WORKDIR /app

# Install system packages & PHP extensions
RUN apt-get update && apt-get install -y \
    nginx supervisor git unzip zip curl libpng-dev libjpeg-dev libfreetype6-dev libonig-dev libxml2-dev libicu-dev libpq-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_mysql pdo_pgsql bcmath xml intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Composer-built vendor files
COPY --from=vendor /app /app

# Copy Nginx and Supervisor configs
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose PHP-FPM port instead of socket
RUN sed -i 's|listen = .*|listen = 9000|' /usr/local/etc/php-fpm.d/zz-docker.conf

# Permissions
RUN chown -R www-data:www-data /app && chmod -R 755 /app

EXPOSE 80

# Launch everything
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
