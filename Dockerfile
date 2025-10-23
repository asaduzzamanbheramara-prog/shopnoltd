# ===========================
# Stage 1: Composer dependencies
# ===========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy composer files first for caching
COPY backend/composer.json backend/composer.lock* ./

# Install dependencies
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress --no-scripts

# Copy full backend source
COPY backend/ ./

# ===========================
# Stage 2: PHP + Nginx
# ===========================
FROM php:8.2-fpm-alpine

# Install system dependencies
RUN apk add --no-cache bash nginx supervisor icu-dev oniguruma-dev zlib-dev libzip-dev postgresql-dev \
    && docker-php-ext-install pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache \
    && rm -rf /var/cache/apk/*

WORKDIR /var/www/html

# Copy vendor from build stage
COPY --from=vendor /app/vendor ./vendor

# Copy backend source
COPY backend/ .

# Ensure Laravel directories exist
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache

# Copy .env if missing
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Generate app key
RUN php artisan key:generate --force || true

# Copy Supervisor config
COPY docker/supervisord.conf /etc/supervisord.conf

EXPOSE 80 443 9000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
