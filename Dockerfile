# ===========================
# Stage 1: Composer dependencies
# ===========================
FROM composer:2 AS vendor

# Set working directory to Laravel root
WORKDIR /app

# Copy composer files first for caching
COPY backend/composer.json backend/composer.lock* ./

# Copy the rest of the backend folder
COPY backend/ ./

# Install PHP dependencies without post-autoload scripts
RUN set -e; \
    composer install --no-dev --prefer-dist --no-interaction --no-progress --no-scripts -vvv || { \
        echo "❌ Composer install failed! Listing PHP files with potential issues:"; \
        find . -type f -name "*.php" -exec php -l {} \; | grep -v "No syntax errors detected"; \
        echo "❌ Stopping Docker build due to Composer errors."; \
        exit 1; \
    }

# ===========================
# Stage 2: PHP-FPM
# ===========================
FROM php:8.2-fpm-alpine

RUN apk add --no-cache \
        bash git icu-dev oniguruma-dev zlib-dev libzip-dev postgresql-dev \
    && docker-php-ext-install \
        pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache \
    && apk del git \
    && rm -rf /var/cache/apk/*

WORKDIR /var/www/html

# Copy Composer binary
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copy vendor from build stage
COPY --from=vendor /app/vendor /var/www/html/vendor

# Copy backend source code
COPY backend/ /var/www/html

# Ensure Laravel directories exist
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache

# Set proper permissions
RUN chown -R www-data:www-data storage bootstrap/cache

# Copy .env if missing
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Optimize autoloader
RUN composer dump-autoload --optimize

# Generate Laravel application key
RUN php artisan key:generate --force || true

# Final permissions fix
RUN chown -R www-data:www-data storage bootstrap/cache

EXPOSE 9000
CMD ["php-fpm"]
