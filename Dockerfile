# ================================
# Stage 0: Composer (dependencies)
# ================================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend code
COPY backend/ ./

# Ensure directories exist
RUN mkdir -p database/seeders database/factories

# Install dependencies with robust error handling
RUN set -eux; \
    echo "Installing composer dependencies..."; \
    if ! composer install --no-dev --prefer-dist --no-interaction --optimize-autoloader; then \
        echo ""; \
        echo "======================================================"; \
        echo "ERROR: composer.lock is out of date with composer.json!"; \
        echo "Missing packages:"; \
        echo "  - psr/http-client"; \
        echo "  - psr/http-message"; \
        echo "  - psr/log"; \
        echo "Solution: Run 'composer update' locally and commit composer.lock"; \
        echo "======================================================"; \
        exit 1; \
    fi

# ================================
# Stage 1: PHP-FPM + production setup
# ================================
FROM php:8.2-fpm-bullseye

WORKDIR /app

# Install PHP extensions + system packages
RUN apt-get update && apt-get install -y \
    nginx git unzip zip curl libpng-dev libjpeg-dev libfreetype6-dev \
    libonig-dev libxml2-dev libicu-dev libpq-dev supervisor \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd mbstring pdo pdo_pgsql xml bcmath intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy backend + vendor dependencies
COPY --from=vendor /app /app

# Optional: nginx/supervisor configs
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose PHP-FPM port
EXPOSE 9000

# Start supervisor
CMD ["/usr/bin/supervisord", "-n"]
