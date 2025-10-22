# Stage 1: vendor
FROM composer:2 as vendor
WORKDIR /app
COPY composer.json composer.lock* /app/
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress || true

# Stage 2: PHP FPM
FROM php:8.2-fpm-alpine AS base
RUN apk add --no-cache git icu-dev oniguruma-dev zlib-dev libzip-dev bash
RUN docker-php-ext-install pdo pdo_mysql pdo_pgsql mbstring zip intl bcmath opcache || true
WORKDIR /var/www/html
COPY . /var/www/html
COPY --from=vendor /app/vendor /var/www/html/vendor
RUN mkdir -p storage/framework/sessions storage/framework/views storage/framework/cache storage/logs bootstrap/cache
RUN chown -R www-data:www-data /var/www/html/storage /var/www/html/bootstrap/cache || true
EXPOSE 9000
CMD ["php-fpm"]
