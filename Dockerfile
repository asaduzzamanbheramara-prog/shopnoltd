# ========================================
# 1️⃣ Build Stage (Composer Dependencies)
# ========================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend composer files (lock optional)
COPY backend/composer.json backend/composer.lock* ./

# Install PHP dependencies
RUN composer install --no-dev --prefer-dist --optimize-autoloader --no-scripts --no-progress -vvv

# ========================================
# 2️⃣ Final Stage (PHP-FPM + Nginx)
# ========================================
FROM php:8.2-fpm-bullseye AS app

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
 && docker-php-ext-configure gd --with-freetype --with-jpeg \
 && docker-php-ext-install gd mbstring pdo pdo_mysql tokenizer xml bcmath intl opcache \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /var/www/html

# Copy backend Laravel app
COPY backend/ .

# Copy vendor from build stage
COPY --from=vendor /app/vendor ./vendor

# Copy Docker configs
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisord.conf

# Create storage & cache directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache

# Set permissions
RUN chown -R www-data:www-data storage bootstrap/cache

# Prepare .env if missing
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Optimize Laravel
RUN composer dump-autoload --optimize || true
RUN php artisan key:generate --force || true

# Ensure Nginx directories exist
RUN mkdir -p /var/log/nginx /run/nginx

# Expose HTTP port
EXPOSE 80

# Start Supervisor (runs both Nginx & PHP-FPM)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
