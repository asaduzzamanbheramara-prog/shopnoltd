# ========================================
# 1️⃣ Build Stage
# ========================================
FROM composer:2 AS vendor

WORKDIR /app

COPY composer.json composer.lock ./
RUN composer install --no-dev --prefer-dist --optimize-autoloader

# ========================================
# 2️⃣ Final Stage (Nginx + PHP-FPM)
# ========================================
FROM php:8.2-fpm-bullseye AS app

# Install dependencies
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

# Copy Laravel app files
COPY . .

# Copy vendor from builder
COPY --from=vendor /app/vendor ./vendor

# Copy configs
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisord.conf

# Create Laravel storage & cache directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache

# Permissions
RUN chown -R www-data:www-data storage bootstrap/cache

# Prepare .env (if not exists)
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Optimize Laravel
RUN composer dump-autoload --optimize || true
RUN php artisan key:generate --force || true

# Nginx directories
RUN mkdir -p /var/log/nginx /run/nginx

# Expose ports
EXPOSE 80

# Start both Nginx & PHP-FPM using Supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
