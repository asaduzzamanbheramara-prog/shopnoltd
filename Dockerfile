# ===========================
# Stage 1: Composer dependencies (debug mode)
# ===========================
FROM composer:2 AS vendor

WORKDIR /app

# Copy backend files so composer can access everything
COPY backend/ /app/

# Run composer in verbose mode for debugging
# Shows full error message if something fails
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress -vvv || \
    (echo "❌ Composer install failed! Dumping composer.json for debugging:" && \
     cat composer.json && exit 1)
