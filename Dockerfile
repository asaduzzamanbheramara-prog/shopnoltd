# ================================
# Stage 1: PHP + Composer + Laravel
# ================================
FROM php:8.2-fpm-bullseye AS app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git unzip curl libpng-dev libonig-dev libxml2-dev libzip-dev \
    libpq-dev libicu-dev zlib1g-dev libjpeg-dev libfreetype6-dev \
    nginx supervisor gettext \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install PHP extensions
RUN docker-php-ext-install pdo pdo_mysql mbstring exif pcntl bcmath gd zip intl

# Copy backend files
COPY backend/ /app/

# Copy supervisord config
COPY backend/docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy Nginx template
COPY backend/docker/default.conf.template /etc/nginx/conf.d/default.conf.template

# Set Render dynamic port
ENV PORT=10000
EXPOSE 10000

# Substitute PORT in Nginx template
RUN envsubst '$PORT' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Laravel environment & permissions
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env; \
    fi \
    && php artisan key:generate --force \
    && chown -R www-data:www-data /app/storage /app/bootstrap/cache \
    && chmod -R 755 /app/storage /app/bootstrap/cache

# Install Composer dependencies
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer \
    && composer install --no-dev --optimize-autoloader --no-interaction --prefer-dist

# Start supervisor (which manages php-fpm + nginx)
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
