# ===========================
# Stage 1: Composer dependencies
# ===========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy composer files first for caching
COPY backend/composer.json backend/composer.lock* ./

# Copy the rest of backend
COPY backend/ ./

# Install dependencies
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress --no-scripts -vvv

# ===========================
# Stage 2: PHP-FPM + Nginx
# ===========================
FROM php:8.2-fpm-alpine

# Install PHP extensions
RUN apk add --no-cache bash git icu-dev oniguruma-dev zlib-dev libzip-dev postgresql-dev \
    && docker-php-ext-install pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache \
    && apk del git \
    && rm -rf /var/cache/apk/*

WORKDIR /var/www/html

# Copy composer binary
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copy vendor from build stage
COPY --from=vendor /app/vendor /var/www/html/vendor

# Copy backend source code including composer.json
COPY backend/ /var/www/html
COPY backend/composer.json /var/www/html/composer.json

# Ensure directories exist
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache

# Set permissions
RUN chown -R www-data:www-data storage bootstrap/cache

# Copy .env
COPY backend/.env.example /var/www/html/.env
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env; \
    fi

# Run Composer autoload optimization
RUN composer dump-autoload --optimize

# Generate Laravel key
RUN php artisan key:generate --force

# Final permissions fix
RUN chown -R www-data:www-data storage bootstrap/cache

EXPOSE 9000
CMD ["php-fpm"]
