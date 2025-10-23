# ============================================
# Stage 1: Composer Dependencies
# ============================================
FROM composer:2 AS vendor
WORKDIR /app
COPY backend/composer.json backend/composer.lock* ./
COPY backend/ ./
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress --no-scripts -vvv || { \
    echo "❌ Composer install failed! Checking PHP syntax..."; \
    find . -type f -name "*.php" -exec php -l {} \; | grep -v "No syntax errors detected"; \
    exit 1; \
}

# ============================================
# Stage 2: Final Runtime Image
# ============================================
FROM php:8.2-fpm-alpine

# Install system dependencies + nginx
RUN apk add --no-cache bash nginx supervisor icu-dev oniguruma-dev libzip-dev zlib-dev postgresql-dev git \
    && docker-php-ext-install pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache

WORKDIR /var/www/html

# Copy application
COPY backend/ ./
COPY --from=vendor /app/vendor ./vendor

# Copy nginx + supervisor configs
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisord.conf

# Create writable directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache

# Ensure .env exists
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Optimize autoloader
RUN composer dump-autoload --optimize

# Laravel app key
RUN php artisan key:generate --force || true

EXPOSE 80

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
