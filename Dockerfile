# =========================
# 1️⃣ Build stage: Composer
# =========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy composer files first
COPY backend/composer.json backend/composer.lock ./

# Force composer to install and update if lock is out-of-sync
RUN composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader || \
    composer update --no-dev --prefer-dist --no-interaction --optimize-autoloader

# Copy the rest of the backend files
COPY backend/ ./

# Ensure necessary directories exist
RUN mkdir -p database/seeders database/factories \
    storage/framework/{sessions,views,cache} \
    storage/logs bootstrap/cache

# =========================
# 2️⃣ Final stage: PHP-FPM + Nginx
# =========================
FROM php:8.2-fpm-bullseye

WORKDIR /app

# Install system dependencies and PHP extensions
RUN apt-get update && apt-get install -y \
    nginx git unzip libpng-dev libjpeg-dev libfreetype6-dev \
    libonig-dev libxml2-dev zip curl libicu-dev libpq-dev supervisor \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy application files and vendor from build stage
COPY --from=vendor /app /app

# Nginx configuration
RUN rm -rf /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# PHP-FPM config
COPY docker/php-fpm.conf /usr/local/etc/php-fpm.d/www.conf

# Supervisor config
COPY docker/supervisord.conf /etc/supervisord.conf

# Debug PHP
RUN { \
    echo "display_errors=On"; \
    echo "display_startup_errors=On"; \
    echo "error_reporting=E_ALL"; \
    echo "log_errors=On"; \
    echo "error_log=/var/log/php-fpm/error.log"; \
} > /usr/local/etc/php/conf.d/debug.ini

# Fix permissions
RUN chown -R www-data:www-data storage bootstrap/cache /var/log/php-fpm

# Environment setup
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=local/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=true/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env && \
        echo 'LOG_CHANNEL=single' >> .env; \
    fi

# Laravel key
RUN php artisan key:generate --force || true

# Supervisor processes
RUN echo '[program:laravel-log]' >> /etc/supervisord.conf && \
    echo 'command=/bin/bash -c "mkdir -p /app/storage/logs && touch /app/storage/logs/laravel.log && tail -F /app/storage/logs/laravel.log /var/log/php-fpm/error.log"' >> /etc/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisord.conf && \
    echo 'stdout_logfile=/dev/stdout' >> /etc/supervisord.conf && \
    echo 'stdout_logfile_maxbytes=0' >> /etc/supervisord.conf && \
    echo 'stderr_logfile=/dev/stderr' >> /etc/supervisord.conf && \
    echo 'stderr_logfile_maxbytes=0' >> /etc/supervisord.conf

# Expose port
EXPOSE 80

# Start supervisord (manages PHP-FPM + Nginx + Laravel log)
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisord.conf"]
