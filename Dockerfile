# Stage 1: vendor
FROM composer:2 AS vendor
WORKDIR /app
COPY composer.json composer.lock* /app/
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress --ignore-platform-reqs

# Stage 2: PHP-FPM
FROM php:8.2-fpm-alpine

# Install system dependencies + PostgreSQL + GD for images
RUN apk add --no-cache \
    bash \
    git \
    icu-dev \
    oniguruma-dev \
    zlib-dev \
    libzip-dev \
    postgresql-dev \
    libpng-dev \
    freetype-dev \
    libjpeg-turbo-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install \
        pdo \
        pdo_mysql \
        pdo_pgsql \
        mbstring \
        zip \
        intl \
        bcmath \
        opcache \
        gd

# Set working directory
WORKDIR /var/www/html

# Copy composer binary
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copy vendor from first stage
COPY --from=vendor /app/vendor /var/www/html/vendor

# Copy project files
COPY . /var/www/html

# Create storage & bootstrap cache directories
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache

# Clear Composer cache and reinstall dependencies (robust)
RUN composer clear-cache \
    && composer install --no-dev --optimize-autoloader --ignore-platform-reqs

# Create .env if missing
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
        sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Generate Laravel application key
RUN php artisan key:generate --force

# Fix permissions one last time
RUN chown -R www-data:www-data storage bootstrap/cache

# Expose PHP-FPM port
EXPOSE 9000

# Start PHP-FPM
CMD ["php-fpm"]
