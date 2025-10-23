# ===========================
# Stage 1: Composer dependencies
# ===========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy entire backend (not just composer.json)
# This ensures autoload and local packages work correctly
COPY backend/ /app/

# Install dependencies (no dev, optimized, quiet)
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress


# ===========================
# Stage 2: PHP-FPM (runtime)
# ===========================
FROM php:8.2-fpm-alpine

# Install system dependencies and PHP extensions for Laravel
RUN apk add --no-cache \
        bash git icu-dev oniguruma-dev zlib-dev libzip-dev postgresql-dev \
    && docker-php-ext-install \
        pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache \
    && apk del git

# Set working directory
WORKDIR /var/www/html

# Copy Composer binary
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copy vendor from build stage
COPY --from=vendor /app/vendor /var/www/html/vendor

# Copy backend source code
COPY backend/ /var/www/html

# Ensure necessary Laravel directories exist
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache

# Set proper permissions
RUN chown -R www-data:www-data storage bootstrap/cache

# Copy .env.example → .env if missing, then set production values
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Optimize Laravel autoloader
RUN composer dump-autoload --optimize

# Generate application key
RUN php artisan key:generate --force || true

# Fix permissions one more time (important for runtime)
RUN chown -R www-data:www-data storage bootstrap/cache

# Expose PHP-FPM port
EXPOSE 9000

# Start PHP-FPM
CMD ["php-fpm"]
