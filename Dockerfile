# ========================================
# 1️⃣ Build Stage: Composer dependencies
# ========================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy composer files
COPY backend/composer.json backend/composer.lock ./

# ⚙️ Ensure compatibility: Update lock file if PHP version mismatch
RUN composer update --no-dev --prefer-dist --optimize-autoloader || composer install --no-dev --prefer-dist --optimize-autoloader

# ========================================
# 2️⃣ Final Stage: PHP-FPM + Nginx
# ========================================
FROM php:8.4-fpm-bullseye AS app
# ↑ use 8.4 to match your local PHP

# Install system dependencies & PHP extensions
RUN apt-get update && apt-get install -y \
        nginx \
        supervisor \
        git \
        unzip \
        libpng-dev \
        libjpeg-dev \
        libfreetype6-dev \
        libonig-dev \
        libxml2-dev \
        zip \
        curl \
        libicu-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /var/www/html

# Copy Laravel backend code
COPY backend/ ./

# Copy vendor dependencies
COPY --from=vendor /app/vendor ./vendor

# Copy Nginx & Supervisor configs
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisord.conf

# Create storage & cache directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache

# Set permissions
RUN chown -R www-data:www-data storage bootstrap/cache

# Ensure .env exists
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Optimize Laravel
RUN php artisan key:generate --force || true && \
    php artisan config:cache || true && \
    php artisan route:cache || true && \
    php artisan view:cache || true

# Create directories for Nginx
RUN mkdir -p /var/log/nginx /run/nginx

# Expose HTTP port
EXPOSE 80

# Start Supervisor (manages Nginx + PHP-FPM)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
