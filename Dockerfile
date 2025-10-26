FROM php:8.2-fpm-bullseye

WORKDIR /app

COPY --from=vendor /app /app

RUN apt-get update && apt-get install -y nginx supervisor git unzip libzip-dev zip \
    && docker-php-ext-install pdo pdo_mysql \
    && rm -rf /var/lib/apt/lists/*

# PHP-FPM socket
RUN sed -i 's|^listen = .*|listen = /run/php/php8.2-fpm.sock|' /usr/local/etc/php-fpm.d/www.conf

# Copy Nginx template & Supervisor config
COPY backend/docker/default.conf /etc/nginx/conf.d/default.conf.template
COPY backend/docker/supervisord.conf /etc/docker/supervisord.conf

# Generate actual Nginx config with dynamic PORT
RUN envsubst '$PORT' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Laravel .env & storage permissions
RUN if [ ! -f .env ]; then cp .env.example .env && \
      sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
      sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env; fi \
    && php artisan key:generate --force \
    && chown -R www-data:www-data /app/storage /app/bootstrap/cache \
    && chmod -R 755 /app/storage /app/bootstrap/cache

# Render dynamic port
ENV PORT=8080
EXPOSE 8080

# Start Supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/docker/supervisord.conf"]
