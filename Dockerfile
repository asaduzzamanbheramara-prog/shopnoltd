# =========================
# 1️⃣ Build stage: Composer dependencies
# =========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy only composer files from backend to leverage caching
COPY backend/composer.json backend/composer.lock ./

# Ensure directories exist for Laravel
RUN mkdir -p database/seeders database/factories

# Install PHP dependencies
RUN composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader

# =========================
# 2️⃣ Final stage: PHP-FPM + Nginx
# =========================
FROM php:8.2-fpm-bullseye

WORKDIR /app

# Install system packages and PHP extensions
RUN apt-get update && apt-get install -y \
    nginx git unzip libpng-dev libjpeg-dev libfreetype6-dev \
    libonig-dev libxml2-dev zip curl libicu-dev libpq-dev \
 && docker-php-ext-configure gd --with-freetype --with-jpeg \
 && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Composer dependencies from the build stage
COPY --from=vendor /app/vendor ./vendor

# Copy the full backend source code
COPY backend/ ./

# Remove default Nginx config and add our own
RUN rm -rf /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# Copy PHP-FPM config
COPY docker/php-fpm.conf /usr/local/etc/php-fpm.d/www.conf

# Setup Laravel storage & bootstrap/cache permissions
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache

# Copy supervisord configuration
COPY docker/supervisord.conf /etc/supervisord.conf

# Setup Laravel environment if not exists
RUN if [ ! -f .env ]; then \
      cp .env.example .env && \
      sed -i 's/APP_ENV=.*/APP_ENV=local/' .env && \
      sed -i 's/APP_DEBUG=.*/APP_DEBUG=true/' .env && \
      sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env && \
      echo 'LOG_CHANNEL=single' >> .env; \
    fi

# Generate Laravel app key
RUN php artisan key:generate --force || true

# Configure Supervisor to tail Laravel & PHP-FPM logs
RUN echo '[program:laravel-log]' >> /etc/supervisord.conf && \
    echo 'command=/bin/bash -c "mkdir -p /app/storage/logs && touch /app/storage/logs/laravel.log && tail -F /app/storage/logs/laravel.log /var/log/php-fpm/error.log"' >> /etc/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisord.conf && \
    echo 'stdout_logfile=/dev/stdout' >> /etc/supervisord.conf && \
    echo 'stdout_logfile_maxbytes=0' >> /etc/supervisord.conf && \
    echo 'stderr_logfile=/dev/stderr' >> /etc/supervisord.conf && \
    echo 'stderr_logfile_maxbytes=0' >> /etc/supervisord.conf

# Expose port 80 for Nginx
EXPOSE 80

# Start Supervisor (which manages Nginx and PHP-FPM)
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisord.conf"]
