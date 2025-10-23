# ===========================
# Stage 1: Composer dependencies
# ===========================
FROM composer:2 AS vendor

# Set working directory
WORKDIR /app

# Copy only composer files for caching
COPY backend/composer.json backend/composer.lock* ./

# Install PHP dependencies without dev packages
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress --no-scripts -vvv

# Copy the rest of the backend for vendor autoload discovery
COPY backend/ .

# ===========================
# Stage 2: PHP-FPM
# ===========================
FROM php:8.2-fpm-alpine

# Install system dependencies
RUN apk add --no-cache \
        bash git icu-dev oniguruma-dev zlib-dev libzip-dev postgresql-dev \
    && docker-php-ext-install \
        pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache \
    && apk del git \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /var/www/html

# Copy Composer binary
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copy backend source code
COPY backend/ ./

# Copy vendor directory from build stage
COPY --from=vendor /app/vendor ./vendor

# Ensure Laravel directories exist
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache

# Set permissions
RUN chown -R www-data:www-data storage bootstrap/cache

# Copy .env if missing
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Optimize Composer autoloader
RUN composer dump-autoload --optimize

# Generate Laravel application key
RUN php artisan key:generate --force || true

# Final permissions fix
RUN chown -R www-data:www-data storage bootstrap/cache

EXPOSE 9000
CMD ["php-fpm"]
