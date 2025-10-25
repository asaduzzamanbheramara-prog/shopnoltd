# 1️⃣ Build stage: Composer
FROM composer:2 AS vendor

WORKDIR /app
COPY backend/ ./

RUN composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader

# 2️⃣ Final stage: PHP-FPM + Nginx
FROM php:8.4-fpm-bullseye

RUN apt-get update && apt-get install -y \
        nginx git unzip libpng-dev libjpeg-dev libfreetype6-dev \
        libonig-dev libxml2-dev zip curl libicu-dev libpq-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=vendor /app/vendor ./vendor
COPY backend/ ./

# Writable dirs
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache /var/run \
    && chown -R www-data:www-data storage bootstrap/cache /var/run

# PHP-FPM pool using TCP for Render
RUN { \
    echo "[www]"; \
    echo "user = www-data"; \
    echo "group = www-data"; \
    echo "listen = 9000"; \
    echo "pm = dynamic"; \
    echo "pm.max_children = 5"; \
    echo "pm.start_servers = 2"; \
    echo "pm.min_spare_servers = 1"; \
    echo "pm.max_spare_servers = 3"; \
    echo "chdir = /"; \
} > /usr/local/etc/php-fpm.d/www.conf

# Nginx config
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# Debug PHP
RUN { \
    echo "display_errors=On"; \
    echo "display_startup_errors=On"; \
    echo "error_reporting=E_ALL"; \
    echo "log_errors=On"; \
} > /usr/local/etc/php/conf.d/debug.ini

# Laravel .env
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=local/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=true/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env && \
        echo 'LOG_CHANNEL=single' >> .env; \
    fi

RUN php artisan key:generate --force || true

EXPOSE 80

# Start PHP-FPM + Nginx
CMD service php8.4-fpm start && nginx -g 'daemon off;'
