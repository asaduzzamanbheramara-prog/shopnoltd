# ===========================================
# Stage 1: Composer Dependencies Build Stage
# ===========================================
FROM composer:2 AS vendor

# Set working directory inside container
WORKDIR /app

# Copy composer files first for build cache efficiency
COPY backend/composer.json backend/composer.lock* ./

# Copy all backend source
COPY backend/ ./

# Install PHP dependencies (no dev, no scripts, verbose)
RUN set -e; \
    composer install --no-dev --prefer-dist --no-interaction --no-progress --no-scripts -vvv || { \
        echo "❌ Composer install failed! Listing PHP syntax issues:"; \
        find . -type f -name "*.php" -exec php -l {} \; | grep -v 'No syntax errors detected'; \
        exit 1; \
    }

# ===========================================
# Stage 2: PHP + Nginx + Supervisor Runtime
# ===========================================
FROM php:8.2-fpm-alpine

# Install required system packages and PHP extensions
RUN apk add --no-cache \
    nginx supervisor bash icu-dev oniguruma-dev zlib-dev libzip-dev postgresql-dev git \
    && docker-php-ext-install \
        pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache \
    && rm -rf /var/cache/apk/*

# Working directory for Laravel
WORKDIR /var/www/html

# Copy composer binary from composer image
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copy vendor folder from build stage
COPY --from=vendor /app/vendor /var/www/html/vendor

# Copy backend application files
COPY backend/ /var/www/html

# Copy Nginx and Supervisor configs
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisord.conf

# Ensure Laravel writable directories exist
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache

# Set correct ownership and permissions
RUN chown -R www-data:www-data storage bootstrap/cache

# Copy default .env if not present
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Optimize Composer autoloader
RUN composer dump-autoload --optimize || true

# Generate Laravel application key
RUN php artisan key:generate --force || true

# Fix missing Nginx runtime directories
RUN mkdir -p /var/log/nginx /run/nginx

# Expose default HTTP port for Render
EXPOSE 80

# Start both PHP-FPM and Nginx using Supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
