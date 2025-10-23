# ===========================
# Stage 1: Composer dependencies (debug mode)
# ===========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy all project files so composer can access everything
COPY . /app/

# Install PHP dependencies without running post-autoload scripts
# Fail fast and show problematic files if Composer fails
RUN set -e; \
    composer install --no-dev --prefer-dist --no-interaction --no-progress --no-scripts -vvv || { \
        echo "❌ Composer install failed! Listing PHP files with potential issues:"; \
        find . -type f -name "*.php" -exec php -l {} \; | grep -v "No syntax errors detected"; \
        echo "❌ Stopping Docker build due to Composer errors."; \
        exit 1; \
    }


# ===========================
# Stage 2: PHP-FPM (runtime)
# ===========================
FROM php:8.2-fpm-alpine

# Install system packages and PHP extensions required by Laravel
RUN apk add --no-cache \
        bash git icu-dev oniguruma-dev zlib-dev libzip-dev postgresql-dev \
    && docker-php-ext-install \
        pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache \
    && apk del git \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /var/www/html

# Copy Composer binary (optional, useful for artisan/composer commands)
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copy vendor from build stage
COPY --from=vendor /app/vendor /var/www/html/vendor

# Copy all project files
COPY . /var/www/html

# Ensure necessary Laravel directories exist
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache

# Set proper permissions
RUN chown -R www-data:www-data storage bootstrap/cache

# If .env is missing, create it from example and set production values
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Optimize autoloader
RUN composer dump-autoload --optimize

# Generate application key
RUN php artisan key:generate --force || true

# Final permission fix
RUN chown -R www-data:www-data storage bootstrap/cache

# Expose PHP-FPM port
EXPOSE 9000

# Start PHP-FPM
CMD ["php-fpm"]
