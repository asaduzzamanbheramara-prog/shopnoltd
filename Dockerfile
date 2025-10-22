# Stage: PHP-FPM
FROM php:8.2-fpm-alpine

# Install system dependencies
RUN apk add --no-cache bash git icu-dev oniguruma-dev zlib-dev libzip-dev postgresql-dev \
    && docker-php-ext-install pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache

# Set working directory
WORKDIR /var/www/html

# Copy composer from official image
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copy project files
COPY . .

# Install PHP dependencies
RUN composer install --no-dev --optimize-autoloader

# Create .env if missing
RUN if [ ! -f .env ]; then \
    cp .env.example .env && \
    sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
    sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
    sed -i 's|APP_URL=.*|APP_URL=https://shopnoltd.onrender.com|' .env; \
    fi

# Generate Laravel app key
RUN php artisan key:generate --force

# Fix permissions
RUN mkdir -p storage/framework/{sessions,views,cache} storage/logs bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache

# Expose port
EXPOSE 9000

# Start PHP-FPM
CMD ["php-fpm"]
