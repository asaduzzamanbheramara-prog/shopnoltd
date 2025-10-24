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
        nginx supervisor git unzip libpng-dev libjpeg-dev libfreetype6-dev \
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

# Remove default Nginx HTML and config, use custom
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisord.conf

# ===========================
# PHP-FPM Global Config
# ===========================
# Create /usr/local/etc/php-fpm.conf with global error log
RUN echo "error_log = /var/log/php-fpm/error.log" > /usr/local/etc/php-fpm.conf

# Pool file: www.conf
COPY docker/php-fpm.conf /usr/local/etc/php-fpm.d/www.conf

# Symlink Nginx site
RUN ln -sf /etc/nginx/conf.d/default.conf /etc/nginx/sites-enabled/default

# Create writable directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache /var/log/php-fpm \
    && chown -R www-data:www-data storage bootstrap/cache /var/log/php-fpm

# ===========================
# Debug-friendly Laravel .env
# ===========================
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=local/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=true/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env && \
        echo 'LOG_CHANNEL=single' >> .env; \
    fi

# ===========================
# Laravel setup + clear caches
# ===========================
RUN php artisan key:generate --force || true \
    && php artisan config:clear || true \
    && php artisan route:clear || true \
    && php artisan view:clear || true \
    && php artisan cache:clear || true

# ===========================
# 🐞 Debug PHP Config
# ===========================
RUN { \
  echo "display_errors=On"; \
  echo "display_startup_errors=On"; \
  echo "error_reporting=E_ALL"; \
  echo "log_errors=On"; \
  echo "error_log=/var/log/php-fpm/error.log"; \
} > /usr/local/etc/php/conf.d/debug.ini

# Expose web port
EXPOSE 80

# Start supervisor (Nginx + PHP-FPM)
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisord.conf"]
