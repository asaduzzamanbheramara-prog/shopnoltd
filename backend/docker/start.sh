#!/bin/bash
set -e

# Replace PORT variable in Nginx template
envsubst '$PORT' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Ensure Laravel log file exists
mkdir -p /app/storage/logs
touch /app/storage/logs/laravel.log

# Start Supervisor (manages Nginx + PHP-FPM + Laravel log tail)
exec /usr/bin/supervisord -c /etc/docker/supervisord.conf
