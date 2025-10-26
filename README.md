ShopNoLTD – Full Stack Deployment Guide

License: MIT
Stack: Laravel 10 (PHP 8.2) + MySQL + React 20 + Nginx

This repository contains a production-ready full-stack application, with a Laravel backend and React frontend, configured for Docker deployment.

📦 Folder Structure
shopnoltd/
├── backend/                 # Laravel backend
│   ├── app/
│   ├── bootstrap/
│   ├── config/
│   ├── database/
│   ├── public/
│   ├── resources/
│   ├── routes/
│   ├── tests/
│   ├── artisan
│   ├── composer.json
│   └── composer.lock*       # optional
├── frontend/                # React frontend
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── package-lock.json*
│   └── .env
├── docker/
│   ├── nginx/
│   │   ├── default.conf     # Laravel
│   │   └── frontend.conf    # React
│   └── supervisord.conf
├── db/
│   └── schema.sql
├── docker-compose.yml
├── Dockerfile               # Laravel backend + Nginx + PHP-FPM
├── Dockerfile.frontend      # React frontend build
├── README.md
└── LICENSE

⚙️ Setup & Deployment
1️⃣ Clone the repository
git clone https://github.com/asaduzzamanbheramara-prog/shopnoltd.git
cd shopnoltd

2️⃣ Configure Environment
Backend .env
cp backend/.env.example backend/.env


Edit the .env:

APP_ENV=production
APP_DEBUG=false
APP_URL=https://shopnoltd.onrender.com
DB_CONNECTION=mysql
DB_HOST=db
DB_PORT=3306
DB_DATABASE=shopnoltd_db
DB_USERNAME=shopnoltd_user
DB_PASSWORD=your_password

Frontend .env
cp frontend/.env.example frontend/.env


Set the backend API URL if needed:

REACT_APP_API_URL=https://shopnoltd.onrender.com/api

3️⃣ Database Setup
# MySQL container optional via docker-compose or local DB
mysql -u shopnoltd_user -p shopnoltd_db < db/schema.sql

4️⃣ Docker Deployment (Local)
Build containers
docker-compose build

Start services
docker-compose up -d

Access Services

Backend (Laravel): http://localhost:8080

Frontend (React): http://localhost:3000

5️⃣ Deployment to Render

Steps:

Create a new Web Service in Render.

Connect your GitHub repository shopnoltd.

For Backend:

Root directory: /

Docker: Dockerfile

Port: 80

For Frontend:

Root directory: /frontend

Docker: Dockerfile.frontend

Port: 80

Set environment variables in Render dashboard for .env configuration.

Deploy → Your service will be live at https://shopnoltd.onrender.com.

6️⃣ Commands

Backend (Laravel)

# Artisan commands
docker exec -it shopnoltd_backend php artisan migrate
docker exec -it shopnoltd_backend php artisan key:generate
docker exec -it shopnoltd_backend php artisan config:cache


Frontend (React)

docker exec -it shopnoltd_frontend npm run build

7️⃣ Notes

Docker ensures all dependencies are installed for PHP, Nginx, Laravel, and React.

The backend and frontend run in separate containers.

Storage and cache permissions are set for Laravel automatically.

React SPA is served via Nginx in production mode.

If composer.lock or package-lock.json is missing, Docker handles it gracefully.

8️⃣ License

MIT License – see LICENSE
