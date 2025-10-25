# =========================
# 1️⃣ Build Stage: Composer dependencies
# =========================
FROM composer:2 AS vendor

# Set working directory
WORKDIR /app

# Copy composer files from backend
COPY backend/composer.json backend/composer.lock ./

# Ensure directories exist to avoid classmap errors
RUN mkdir -p database/seeders database/factories

# Install PHP dependencies, update if lock is out-of-date
RUN composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader || \
    composer update --no-dev --prefer-dist --no-interaction --optimize-autoloader

# Copy entire backend (full app) to vendor stage
COPY backend/ ./

# =========================
# 2️⃣ Final Stage: PHP-FPM + Nginx
# =========================
FROM php:8.2-fpm-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
        nginx \
        git \
        unzip \
        libpng-dev \
        libjpeg-dev \
        libfreetype6-dev \
        libonig-dev \
        libxml2-dev \
        zip \
        curl \
        libicu-dev \
        libpq-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy compiled vendor files from builder
COPY --from=vendor /app /app

# Remove default Nginx config and add custom one
RUN rm -rf /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# PHP-FPM configuration
COPY docker/php-fpm.conf /usr/local/etc/php-fpm.d/www.conf

# Supervisor configuration
COPY docker/supervisord.conf /etc/supervisord.conf

# Fix Laravel permissions (do NOT touch /var/log/php-fpm)
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache && \
    chown -R www-data:www-data storage bootstrap/cache

# Expose ports
EXPOSE 80 9000

# Start supervisord to manage PHP-FPM + Nginx
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
