# =========================
# 1. Base PHP image
# =========================
FROM php:8.2-fpm

# Install system dependencies (added gettext-base for envsubst)
RUN apt-get update && apt-get install -y \
    git curl unzip zip nginx supervisor gettext-base \
    libpng-dev libjpeg-dev libfreetype6-dev libonig-dev libzip-dev && \
    docker-php-ext-configure gd --with-freetype --with-jpeg && \
    docker-php-ext-install pdo pdo_mysql mbstring gd zip exif pcntl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Composer from the official Composer image
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# =========================
# 2. Set working directory
# =========================
WORKDIR /app

# Copy project files
COPY backend/ /app/

# =========================
# 3. Install dependencies
# =========================
RUN composer install --no-dev --no-interaction --prefer-dist --optimize-autoloader

# =========================
# 4. Environment setup
# =========================
RUN if [ ! -f .env ]; then \
        cp .env.example .env && \
        sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
        sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env; \
    fi && \
    php artisan key:generate --force || true && \
    chown -R www-data:www-data /app/storage /app/bootstrap/cache && \
    chmod -R 755 /app/storage /app/bootstrap/cache

# =========================
# 5. Copy configuration files
# =========================
COPY backend/docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY backend/docker/default.conf.template /etc/nginx/conf.d/default.conf.template

# Render dynamic port (Render requires 10000)
ENV PORT=10000
EXPOSE 10000


# Generate Nginx conf (uses envsubst)
RUN envsubst '$PORT' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# =========================
# 6. Start Supervisor
# =========================
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
