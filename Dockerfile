# ========================================
# 1️⃣ Build Stage: Composer dependencies
# ========================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend for full context
COPY backend/ ./

# Ensure directories exist
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
        nginx git unzip libpng-dev libjpeg-dev libfreetype6-dev \
        libonig-dev libxml2-dev zip curl libicu-dev libpq-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j"$(nproc)" gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Laravel app
COPY backend/ ./

# Copy vendor dependencies from build stage
COPY --from=vendor /app/vendor ./vendor

# Remove default Nginx HTML and config
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

# Copy custom configs
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/php-fpm.conf /usr/local/etc/php-fpm.d/www.conf

# PHP-FPM global error log
RUN echo "error_log = /var/log/php-fpm/error.log" > /usr/local/etc/php-fpm.conf

# Create writable directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache /var/log/php-fpm \
    && chown -R www-data:www-data storage bootstrap/cache /var/log/php-fpm

# Debug-friendly Laravel .env
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=local/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=true/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env && \
        echo 'LOG_CHANNEL=single' >> .env; \
    fi

# Generate key
RUN php artisan key:generate --force || true

# Expose port
EXPOSE 80

# Start PHP-FPM and Nginx
CMD ["sh", "-c", "php-fpm -F & nginx -g 'daemon off;'"]
