# ========================================
# 1️⃣ Build stage: Composer dependencies
# ========================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend (Laravel project)
COPY backend/ ./

# Ensure directories exist to prevent errors
RUN mkdir -p database/seeders database/factories

# Use composer update to fix lock file mismatch
RUN composer update --no-dev --prefer-dist --no-interaction --optimize-autoloader

# ========================================
# 2️⃣ Final stage: PHP-FPM + Nginx
# ========================================
FROM php:8.2-fpm-bullseye

# Install system dependencies & PHP extensions
RUN apt-get update && apt-get install -y \
        nginx git unzip libpng-dev libjpeg-dev libfreetype6-dev \
        libonig-dev libxml2-dev zip curl libicu-dev libpq-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Laravel app
COPY backend/ ./

# Copy vendor from build stage
COPY --from=vendor /app/vendor ./vendor

# Remove default Nginx config, copy custom
RUN rm -rf /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# Create PHP-FPM pool config
RUN echo "[www]" > /usr/local/etc/php-fpm.d/www.conf && \
    echo "user = www-data" >> /usr/local/etc/php-fpm.d/www.conf && \
    echo "group = www-data" >> /usr/local/etc/php-fpm.d/www.conf && \
    echo "listen = 9000" >> /usr/local/etc/php-fpm.d/www.conf && \
    echo "pm = dynamic" >> /usr/local/etc/php-fpm.d/www.conf && \
    echo "pm.max_children = 5" >> /usr/local/etc/php-fpm.d/www.conf && \
    echo "pm.start_servers = 1" >> /usr/local/etc/php-fpm.d/www.conf && \
    echo "pm.min_spare_servers = 1" >> /usr/local/etc/php-fpm.d/www.conf && \
    echo "pm.max_spare_servers = 2" >> /usr/local/etc/php-fpm.d/www.conf

# Create writable directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache

# Debug-friendly PHP
RUN { echo "display_errors=On"; echo "display_startup_errors=On"; echo "error_reporting=E_ALL"; echo "log_errors=On"; echo "error_log=/var/log/php-fpm.log"; } > /usr/local/etc/php/conf.d/debug.ini

# .env setup
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=local/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=true/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Laravel minimal setup
RUN php artisan key:generate --force

# Expose web port
EXPOSE 80

# Start services without supervisord (simpler for free hosting)
CMD ["sh", "-c", "php-fpm -R -F -y /usr/local/etc/php-fpm.conf & nginx -g 'daemon off;'"]
