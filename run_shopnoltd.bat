@echo off
REM ===============================
REM ShopNoLtd Local Development Script
REM ===============================

REM Set paths (update if your PHP path or project path is different)
SET PHP_PATH=C:\xampp\php\php.exe
SET PROJECT_PATH=D:\Project\shopnoltd
SET BACKEND_PATH=%PROJECT_PATH%\backend
SET FRONTEND_PATH=%PROJECT_PATH%\frontend
SET FRONTEND_PORT=3000
SET BACKEND_PORT=8000

REM 1️⃣ Navigate to backend
cd /d %BACKEND_PATH%

REM 2️⃣ Generate APP_KEY if empty
for /f "tokens=2 delims==" %%A in ('findstr APP_KEY .env') do (
    set APP_KEY_VALUE=%%A
)
if "%APP_KEY_VALUE%"=="" (
    echo Generating APP_KEY...
    for /f %%K in ('"%PHP_PATH%" artisan key:generate --show') do set NEW_KEY=%%K
    powershell -Command "(gc .env) -replace 'APP_KEY=', 'APP_KEY=%NEW_KEY%' | Out-File -encoding ASCII .env"
    echo APP_KEY set to %NEW_KEY%
) else (
    echo APP_KEY already exists.
)

REM 3️⃣ Run Laravel migrations
echo Running Laravel migrations...
"%PHP_PATH%" artisan migrate

REM 4️⃣ Start Laravel backend in new window
start cmd /k "%PHP_PATH% artisan serve --host=127.0.0.1 --port=%BACKEND_PORT%"

REM 5️⃣ Start frontend in new window
cd /d %FRONTEND_PATH%
echo Installing frontend dependencies...
npm install
start cmd /k "npm start"

REM 6️⃣ Open browsers
timeout /t 5 >nul
start http://127.0.0.1:%BACKEND_PORT%
start http://localhost:%FRONTEND_PORT%

echo ===============================
echo ShopNoLtd is running locally!
echo Backend: http://127.0.0.1:%BACKEND_PORT%
echo Frontend: http://localhost:%FRONTEND_PORT%
echo ===============================
pause
