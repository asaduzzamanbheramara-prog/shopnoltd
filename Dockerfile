# Stage 1: vendor
FROM composer:2 AS vendor
WORKDIR /app
# Copy composer files from backend
COPY backend/composer.json backend/composer.lock* /app/
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress

# Stage 2: PHP-FPM
FROM php:8.2-fpm-alpine

# Install system dependencies + PHP extensions
RUN apk add --no-cache bash git icu-dev oniguruma-dev zlib-dev libzip-dev postgresql-dev \
    && docker-php-ext-install pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache

# Set working directory
WORKDIR /var/www/html

# Copy composer binary
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copy vendor from first stage
COPY --from=vendor /app/vendor /var/www/html/vendor

# Copy all backend files
COPY backend/ /var/www/html

# Create storage & bootstrap/cache directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache

# Optimize autoloader
RUN composer install --no-dev --optimize-autoloader

# Create .env if missing
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Generate Laravel application key
RUN php artisan key:generate --force

# Fix permissions
RUN chown -R www-data:www-data storage bootstrap/cache

# Expose PHP-FPM port
EXPOSE 9000

# Start PHP-FPM
CMD ["php-fpm"]
