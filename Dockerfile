# ===========================
# 1️⃣ Vendor / Composer Stage
# ===========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend code
COPY backend/ ./

# Ensure required directories exist
RUN mkdir -p database/seeders database/factories

# Install Composer dependencies robustly
RUN set -eux; \
    echo "Installing composer dependencies..."; \
    if ! composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader; then \
        echo ""; \
        echo "======================================================"; \
        echo "ERROR: composer.lock is out of date with composer.json!"; \
        echo "Missing packages might include:"; \
        echo "  - psr/http-client"; \
        echo "  - psr/http-message"; \
        echo "  - psr/log"; \
        echo "Solution: Run 'composer update' locally and commit composer.lock"; \
        echo "======================================================"; \
        exit 1; \
    fi

# ===========================
# 2️⃣ Main PHP-FPM Stage
# ===========================
FROM php:8.2-fpm-bullseye

WORKDIR /app

# Install system dependencies & PHP extensions
RUN apt-get update && apt-get install -y \
        nginx \
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
        supervisor \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy Composer dependencies from vendor stage
COPY --from=vendor /app /app

# Copy Nginx & Supervisor configs (paths updated)
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose port 80
EXPOSE 80

# Ensure permissions (optional, adjust user/group as needed)
RUN chown -R www-data:www-data /app \
    && chmod -R 755 /app

# Start Supervisor (which will start PHP-FPM & Nginx)
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
