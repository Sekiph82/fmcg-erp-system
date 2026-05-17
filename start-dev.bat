@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: Keep the window open no matter what happens.
:: Re-launch self with cmd /k if not already done.
:: ============================================================
if "%~1"=="--started" goto :main
cmd /k "%~f0" --started
exit /b

:main
title FMCG ERP - Dev Startup
cd /d "%~dp0"

echo.
echo ============================================================
echo  FMCG ERP - Development Environment
echo ============================================================
echo.

:: ============================================================
:: 0. PULL LATEST CODE FROM GITHUB (if git repo is set up)
:: ============================================================
if exist ".git\" (
    git --version >nul 2>&1
    if not errorlevel 1 (
        echo  Pulling latest code from GitHub...
        git pull origin main --ff-only >nul 2>&1
        if errorlevel 1 (
            echo  WARNING: Could not pull from GitHub. Continuing with local code.
        ) else (
            echo  Code is up to date.
        )
        echo.
    )
)

:: ============================================================
:: 1. START DOCKER IF NOT RUNNING
:: ============================================================
echo [1/5] Checking Docker...

docker info >nul 2>&1
if not errorlevel 1 (
    echo  Docker is already running.
    goto :docker_ready
)

echo  Docker is not running. Starting Docker Desktop...
echo.

:: --- Launch Docker Desktop (confirmed path first) ---
set DOCKER_EXE=
if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
    set "DOCKER_EXE=C:\Program Files\Docker\Docker\Docker Desktop.exe"
) else if exist "%LOCALAPPDATA%\Docker\Docker Desktop.exe" (
    set "DOCKER_EXE=%LOCALAPPDATA%\Docker\Docker Desktop.exe"
) else if exist "%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe" (
    set "DOCKER_EXE=%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe"
)

if "!DOCKER_EXE!"=="" (
    echo  ERROR: Docker Desktop not found on this machine.
    echo.
    echo  Please install Docker Desktop from:
    echo  https://www.docker.com/products/docker-desktop
    echo.
    goto :error
)

start "" "!DOCKER_EXE!"
echo  Docker Desktop launched. Waiting for engine (up to 90 seconds)...
echo.

set DOCKER_READY=0
for /l %%i in (1,1,45) do (
    if !DOCKER_READY!==0 (
        docker info >nul 2>&1
        if not errorlevel 1 (
            set DOCKER_READY=1
        ) else (
            <nul set /p "=."
            timeout /t 2 /nobreak >nul
        )
    )
)
echo.

if !DOCKER_READY!==0 (
    echo  ERROR: Docker engine did not start within 90 seconds.
    echo  Please wait for Docker Desktop to fully load, then try again.
    goto :error
)
echo  Docker is ready.

:docker_ready

:: ============================================================
:: 2. CHECK ENV FILE
:: ============================================================
echo.
echo [2/5] Checking environment file...

if not exist ".env.development" (
    if exist ".env.development.example" (
        copy ".env.development.example" ".env.development" >nul
        echo  Created .env.development from .env.development.example.
        echo.
        echo  IMPORTANT:
        echo  Open .env.development and check INITIAL_ADMIN_USERNAME and INITIAL_ADMIN_PASSWORD.
        echo  These values are only used when the admin user is created for the first time.
    ) else (
        echo  ERROR: .env.development and .env.development.example are both missing.
        echo.
        echo  Please create .env.development manually or restore .env.development.example.
        goto :error
    )
) else (
    echo  .env.development found.
)
:: ============================================================
:: 3. CHECK PORTS
:: ============================================================
echo.
echo [3/5] Checking ports...

set PORT_OK=1
netstat -an 2>nul | find "0.0.0.0:5432" >nul 2>&1
if not errorlevel 1 ( echo  NOTICE: Port 5432 is already in use. This is normal if dev containers are running. & set PORT_OK=0 )

netstat -an 2>nul | find "0.0.0.0:8000" >nul 2>&1
if not errorlevel 1 ( echo  NOTICE: Port 8000 is already in use. This is normal if dev containers are running. & set PORT_OK=0 )

netstat -an 2>nul | find "0.0.0.0:3000" >nul 2>&1
if not errorlevel 1 ( echo  NOTICE: Port 3000 is already in use. This is normal if dev containers are running. & set PORT_OK=0 )

if !PORT_OK!==1 ( echo  All ports are available. )

:: ============================================================
:: 4. START SERVICES
:: ============================================================
echo.
echo [4/5] Starting services with Docker Compose...
echo.

:: Start DB first (it may already be running from a previous session)
docker compose --env-file .env.development up -d db
timeout /t 3 /nobreak >nul

:: Build and force-recreate the backend so it always starts fresh with latest code
docker compose --env-file .env.development build backend
if errorlevel 1 (
    echo.
    echo  ERROR: docker compose build failed. See output above.
    goto :error
)

docker compose --env-file .env.development up -d --force-recreate backend
if errorlevel 1 (
    echo.
    echo  ERROR: docker compose failed to start backend. See output above.
    goto :error
)

:: Start frontend (no force-recreate needed — it hot-reloads)
docker compose --env-file .env.development up -d frontend
if errorlevel 1 (
    echo.
    echo  ERROR: docker compose failed to start frontend. See output above.
    goto :error
)

echo.
echo  Containers started.

:: ============================================================
:: 5. WAIT FOR READINESS
:: ============================================================
echo.
echo [5/5] Waiting for services to become ready...
echo.

:: --- PostgreSQL ---
echo  Waiting for PostgreSQL...
set DB_READY=0
for /l %%i in (1,1,30) do (
    if !DB_READY!==0 (
        for /f %%C in ('docker compose --env-file .env.development ps -q db 2^>nul') do (
            for /f %%H in ('docker inspect -f "{{.State.Health.Status}}" %%C 2^>nul') do (
                if "%%H"=="healthy" set DB_READY=1
            )
        )
        if !DB_READY!==0 ( <nul set /p "=." & timeout /t 2 /nobreak >nul )
    )
)
echo.
if !DB_READY!==1 (
    echo  PostgreSQL is up.
) else (
    echo  ERROR: PostgreSQL did not become ready.
    docker compose --env-file .env.development logs --tail=80 db
    goto :error
)

:: --- Backend ---
echo  Waiting for Backend API (health check)...
set BACKEND_READY=0
for /l %%i in (1,1,60) do (
    if !BACKEND_READY!==0 (
        curl.exe -fsS http://localhost:8000/health >nul 2>&1
        if not errorlevel 1 (
            set BACKEND_READY=1
        ) else (
            <nul set /p "=." & timeout /t 2 /nobreak >nul
        )
    )
)
echo.
if !BACKEND_READY!==0 (
    echo  ERROR: Backend health check timed out.
    docker compose --env-file .env.development logs --tail=120 backend
    goto :error
) else (
    echo  Backend is up.
    :: Brief pause to allow uvicorn server process to fully initialize
    timeout /t 3 /nobreak >nul
)

:: --- Frontend ---
echo  Waiting for Frontend...
set FRONTEND_READY=0
for /l %%i in (1,1,60) do (
    if !FRONTEND_READY!==0 (
        curl.exe -fsS http://localhost:3000/login >nul 2>&1
        if not errorlevel 1 (
            set FRONTEND_READY=1
        ) else (
            <nul set /p "=." & timeout /t 2 /nobreak >nul
        )
    )
)
echo.
if !FRONTEND_READY!==1 (
    echo  Frontend is up.
) else (
    echo  ERROR: Frontend did not become ready.
    docker compose --env-file .env.development logs --tail=120 frontend
    goto :error
)

:: ============================================================
:: DONE - OPEN BROWSER
:: ============================================================

:: Read dev credentials from .env.development for display
set "DEV_ADMIN_USER=admin"
set "DEV_ADMIN_PASS=(see INITIAL_ADMIN_PASSWORD in .env.development)"
set "DEV_ENV=development"
for /f "usebackq tokens=1,* delims==" %%A in (".env.development") do (
    if "%%A"=="INITIAL_ADMIN_USERNAME" set "DEV_ADMIN_USER=%%B"
    if "%%A"=="INITIAL_ADMIN_PASSWORD" set "DEV_ADMIN_PASS=%%B"
    if "%%A"=="ENVIRONMENT" set "DEV_ENV=%%B"
)

echo.
echo ============================================================
echo  All services started!
echo.
echo  Frontend : http://localhost:3000/login
echo  Backend  : http://localhost:8000/docs
echo  Database : localhost:5432
echo ============================================================

if /i "!DEV_ENV!"=="development" (
    echo.
    echo  Development login:
    echo    URL      : http://localhost:3000/login
    echo    Username : !DEV_ADMIN_USER!
    echo    Password : !DEV_ADMIN_PASS!
    echo.
    echo  If login fails because the database has a different admin password, run:
    echo    docker compose --env-file .env.development exec backend python scripts/reset_dev_admin_password.py
    echo.
    echo  Smoke test:  test-login.bat
)
echo.

:: Open in Chrome — check all common install locations
set CHROME_EXE=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME_EXE=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_EXE=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if "!CHROME_EXE!"=="" (
    echo  WARNING: Google Chrome not found. Opening in default browser instead.
    start "" "http://localhost:3000/login"
) else (
    echo  Opening Google Chrome...
    start "" "!CHROME_EXE!" "http://localhost:3000/login"
)

echo.
echo  Running containers:
echo.
docker compose --env-file .env.development ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo.
echo ============================================================
echo  To view logs : docker compose --env-file .env.development logs -f
echo  To stop      : docker compose --env-file .env.development down
echo ============================================================
echo.
echo  Press any key to close this window...
pause >nul
exit /b 0

:error
echo.
echo  Startup failed. This window will stay open so you can read the error.
echo  Press any key to close...
pause >nul
exit /b 1
