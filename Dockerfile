# ========================================
# 1️⃣ Build Stage: Composer dependencies
# ========================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy Laravel backend
COPY backend/ ./

# Ensure directories exist
RUN mkdir -p database/seeders database/factories

# Install Composer dependencies, ignore lock file mismatches
RUN composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader --ignore-platform-reqs || \
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

# Copy backend and vendor
COPY backend/ ./
COPY --from=vendor /app/vendor ./vendor

# Remove default nginx configs
RUN rm -rf /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf

# Copy custom nginx and supervisord configs
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisord.conf

# PHP debug config
RUN { \
        echo "display_errors=On"; \
        echo "display_startup_errors=On"; \
        echo "error_reporting=E_ALL"; \
        echo "log_errors=On"; \
        echo "error_log=/var/log/php-fpm/error.log"; \
    } > /usr/local/etc/php/conf.d/debug.ini

# PHP-FPM pool
COPY docker/php-fpm.conf /usr/local/etc/php-fpm.d/www.conf

# Create writable directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache /var/log/php-fpm \
    && chown -R www-data:www-data storage bootstrap/cache /var/log/php-fpm

# Minimal .env for free Render plan
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=local/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=true/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env && \
        echo 'LOG_CHANNEL=single' >> .env; \
    fi

# Laravel key (skip cache for free plan)
RUN php artisan key:generate --force || true

# Expose port
EXPOSE 80

# Tail logs + start supervisor (nginx + php-fpm)
RUN echo '[program:laravel-log]' >> /etc/supervisord.conf && \
    echo 'command=/bin/bash -c "mkdir -p /app/storage/logs && touch /app/storage/logs/laravel.log && tail -F /app/storage/logs/laravel.log /var/log/php-fpm/error.log"' >> /etc/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisord.conf && \
    echo 'stdout_logfile=/dev/stdout' >> /etc/supervisord.conf && \
    echo 'stdout_logfile_maxbytes=0' >> /etc/supervisord.conf && \
    echo 'stderr_logfile=/dev/stderr' >> /etc/supervisord.conf && \
    echo 'stderr_logfile_maxbytes=0' >> /etc/supervisord.conf

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisord.conf"]
