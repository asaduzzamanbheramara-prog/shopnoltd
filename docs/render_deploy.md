Render Deployment Guide (quick)
1. Push to GitHub.
2. On Render create Web Service, set Build Command: composer install --no-dev && php artisan migrate --force
3. Set DATABASE_URL and other env vars.
