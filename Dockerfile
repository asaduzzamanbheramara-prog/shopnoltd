# ===========================
# 1️⃣ Vendor / Composer Stage
# ===========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend code
COPY backend/ ./

# Ensure necessary folders exist
RUN mkdir -p database/seeders database/factories

# Install dependencies
RUN composer install --no-dev --no-interaction --prefer-dist --optimize-autoloader


# ===========================
# 2️⃣ Main PHP-FPM + Nginx Stage
# ===========================
FROM php:8.2-fpm-bullseye

WORKDIR /app

# Install required packages and PHP extensions
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    git \
    unzip \
    zip \
    curl \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libonig-dev \
    libxml2-dev \
    libicu-dev \
    libpq-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_mysql pdo_pgsql bcmath xml intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Composer dependencies (vendor stage)
COPY --from=vendor /app /app

# Copy Nginx and Supervisor configs (corrected paths)
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set permissions
RUN chown -R www-data:www-data /app \
    && chmod -R 755 /app

# Expose HTTP port
EXPOSE 80

# Start all services
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
