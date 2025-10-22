# Use PHP 8.2 with Apache
FROM php:8.2-apache

# Install required PHP extensions and system packages
RUN apt-get update && apt-get install -y \
    git curl zip unzip libpng-dev libonig-dev libxml2-dev libzip-dev \
    && docker-php-ext-install pdo_mysql mbstring exif pcntl bcmath gd zip

# Enable Apache mod_rewrite
RUN a2enmod rewrite

# Set working directory
WORKDIR /var/www/html

# Copy Composer from the official image
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copy all project files into the container
COPY . .

# Install PHP dependencies (generate vendor/ + autoload.php)
RUN composer install --no-dev --optimize-autoloader

# Create a default .env file if not present
RUN if [ ! -f .env ]; then \
    cp .env.example .env && \
    sed -i 's/APP_ENV=.*/APP_ENV=production/' .env && \
    sed -i 's/APP_DEBUG=.*/APP_DEBUG=false/' .env && \
    sed -i 's/APP_URL=.*/APP_URL=https:\/\/shopnoltd.onrender.com/' .env; \
    fi

# Generate Laravel application key
RUN php artisan key:generate --force

# Fix permissions for Laravel
RUN chown -R www-data:www-data /var/www/html/storage /var/www/html/bootstrap/cache \
    && chmod -R 775 /var/www/html/storage /var/www/html/bootstrap/cache

# Configure Apache to serve Laravel from /public
RUN echo '<VirtualHost *:80>\n\
    DocumentRoot /var/www/html/public\n\
    <Directory /var/www/html/public>\n\
        AllowOverride All\n\
        Require all granted\n\
    </Directory>\n\
    ErrorLog ${APACHE_LOG_DIR}/error.log\n\
    CustomLog ${APACHE_LOG_DIR}/access.log combined\n\
</VirtualHost>' > /etc/apache2/sites-available/000-default.conf

# Expose port 80
EXPOSE 80

# Start Apache
CMD ["apache2-foreground"]
