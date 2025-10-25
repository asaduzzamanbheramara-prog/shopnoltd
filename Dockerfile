# ========================================
# 1️⃣ Build Stage: Composer dependencies
# ========================================
FROM composer:2 AS vendor
WORKDIR /app

# Copy full backend (Laravel app)
COPY backend/ ./

# Ensure directories exist to prevent classmap errors
RUN mkdir -p database/seeders database/factories

# Install PHP dependencies, update if lock is out-of-date
RUN composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader || \
    composer update --no-dev --prefer-dist --no-interaction --optimize-autoloader

# ========================================
# 2️⃣ Final Stage: PHP-FPM + Nginx
# ========================================
FROM php:8.2-fpm-bullseye

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nginx git unzip libpng-dev libjpeg-dev libfreetype6-dev \
    libonig-dev libxml2-dev zip curl libicu-dev libpq-dev \
    supervisor \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy built vendor files from build stage
COPY --from=vendor /app /app

# Remove default Nginx config
RUN rm -rf /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf

# Copy custom Nginx, PHP-FPM and Supervisor configs
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/php-fpm.conf /usr/local/etc/php-fpm.d/www.conf
COPY docker/supervisord.conf /etc/supervisord.conf

# Create storage/log directories and set permissions
RUN mkdir -p /app/storage/framework/{sessions,views,cache} /app/storage/logs /app/bootstrap/cache \
    && chown -R www-data:www-data /app/storage /app/bootstrap/cache

# Expose web port
EXPOSE 80

# Start Supervisor to run PHP-FPM + Nginx
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisord.conf"]
