# ========================================
# 1️⃣ Build Stage: Composer dependencies
# ========================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy composer files first (for caching)
COPY backend/composer.json backend/composer.lock* ./

# Ensure composer.lock exists
RUN if [ ! -f composer.lock ]; then composer update --no-dev --prefer-dist --optimize-autoloader; fi

# Install dependencies
RUN composer install --no-dev --prefer-dist --optimize-autoloader || composer update --no-dev --prefer-dist --optimize-autoloader


# ========================================
# 2️⃣ Final Stage: PHP-FPM + Nginx
# ========================================
FROM php:8.4-fpm-bullseye AS app

# Install system packages and PHP extensions
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
        libpq-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j"$(nproc)" gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /var/www/html

# Copy application source
COPY backend/ ./

# Copy vendor dependencies from build stage
COPY --from=vendor /app/vendor ./vendor

# 🧩 Fix: Remove default Nginx config and use Laravel’s one
RUN rm -f /etc/nginx/conf.d/default.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# Copy Supervisor configuration
COPY docker/supervisord.conf /etc/supervisord.conf

# Prepare writable dirs
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache

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

EXPOSE 80

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
