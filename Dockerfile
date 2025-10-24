# ========================================
# 1️⃣ Build Stage: Composer dependencies
# ========================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend for full context
COPY backend/ ./

# Ensure directories exist to prevent Composer classmap errors
RUN mkdir -p database/seeders database/factories

# Install/update dependencies
RUN composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader || \
    composer update --no-dev --prefer-dist --no-interaction --optimize-autoloader

# ========================================
# 2️⃣ Final Stage: PHP-FPM + Nginx
# ========================================
FROM php:8.4-fpm-bullseye AS app

# Install system dependencies & PHP extensions
RUN apt-get update && apt-get install -y \
        nginx supervisor git unzip libpng-dev libjpeg-dev libfreetype6-dev \
        libonig-dev libxml2-dev zip curl libicu-dev libpq-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j"$(nproc)" gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Laravel application
COPY backend/ ./

# Copy vendor dependencies from build stage
COPY --from=vendor /app/vendor ./vendor

# Remove default Nginx HTML and config, use custom
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisord.conf
COPY docker/php-fpm.conf /usr/local/etc/php-fpm.d/www.conf

# Set global PHP-FPM error log (must NOT be in pool file)
RUN echo "error_log = /var/log/php-fpm/error.log" > /usr/local/etc/php-fpm.conf

RUN ln -sf /etc/nginx/conf.d/default.conf /etc/nginx/sites-enabled/default

# Create writable directories and log folder
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache /var/log/php-fpm \
    && chown -R www-data:www-data storage bootstrap/cache /var/log/php-fpm

# Ensure .env exists and configured for production
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Laravel optimizations
RUN php artisan key:generate --force \
    && php artisan config:cache \
    && php artisan route:cache \
    && php artisan view:cache

# Expose web port
EXPOSE 80

# Start supervisor (Nginx + PHP-FPM)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
