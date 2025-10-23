# ===========================
# Stage 1: Composer dependencies
# ===========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy composer files first for caching
COPY backend/composer.json backend/composer.lock* ./

# Copy backend source
COPY backend/ ./

# Install PHP dependencies without dev packages
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress --no-scripts -vvv

# ===========================
# Stage 2: PHP-FPM + Nginx
# ===========================
FROM php:8.2-fpm-alpine

# Install system dependencies + PHP extensions
RUN apk add --no-cache \
        bash git icu-dev oniguruma-dev zlib-dev libzip-dev postgresql-dev nginx supervisor \
    && docker-php-ext-install \
        pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache \
    && apk del git \
    && rm -rf /var/cache/apk/*

WORKDIR /var/www/html

# Copy Composer binary and vendor
COPY --from=vendor /usr/bin/composer /usr/bin/composer
COPY --from=vendor /app/vendor /var/www/html/vendor
COPY --from=vendor /app/bootstrap /var/www/html/bootstrap
COPY --from=vendor /app/app /var/www/html/app
COPY --from=vendor /app/routes /var/www/html/routes
COPY --from=vendor /app/config /var/www/html/config
COPY --from=vendor /app/resources /var/www/html/resources
COPY --from=vendor /app/database /var/www/html/database

# Copy Nginx configuration
COPY ./docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# Supervisor configuration
COPY ./docker/supervisord.conf /etc/supervisord.conf

# Ensure Laravel directories exist
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache

# Set proper permissions
RUN chown -R www-data:www-data storage bootstrap/cache

# Copy .env if missing
COPY backend/.env.example /var/www/html/.env
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env; \
    fi

# Optimize Composer autoloader and generate app key
RUN composer dump-autoload --optimize
RUN php artisan key:generate --force || true

EXPOSE 80 9000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
