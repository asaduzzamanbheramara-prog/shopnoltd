# ===========================
# 1️⃣ Build Stage: Composer Dependencies
# ===========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend source
COPY backend/ ./

# Ensure Laravel directories exist
RUN mkdir -p database/seeders database/factories

# Install PHP dependencies
RUN composer install --no-dev --no-interaction --prefer-dist --optimize-autoloader


# ===========================
# 2️⃣ Runtime Stage: PHP-FPM + Nginx + Supervisor
# ===========================
FROM php:8.2-fpm-bullseye

WORKDIR /app

# Install system dependencies & PHP extensions
RUN apt-get update && apt-get install -y \
    nginx supervisor git unzip zip curl \
    libpng-dev libjpeg-dev libfreetype6-dev libonig-dev \
    libxml2-dev libicu-dev libpq-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_mysql pdo_pgsql bcmath xml intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy built app from vendor stage
COPY --from=vendor /app /app

# ✅ Correct paths for your structure
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ✅ Generate APP_KEY only if missing
RUN if [ ! -s .env ]; then cp .env.example .env; fi && \
    grep -q '^APP_KEY=' .env || php artisan key:generate --force

# Set permissions
RUN chown -R www-data:www-data /app && chmod -R 775 /app/storage /app/bootstrap/cache

# Expose HTTP port
EXPOSE 80

# Start Nginx + PHP-FPM under Supervisor
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
