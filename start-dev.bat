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
    if exist ".env.example" (
        copy ".env.example" ".env.development" >nul
        echo  Created .env.development from .env.example.
    ) else (
        echo  ERROR: .env.development and .env.example are both missing.
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
if not errorlevel 1 ( echo  WARNING: Port 5432 is in use. & set PORT_OK=0 )

netstat -an 2>nul | find "0.0.0.0:8000" >nul 2>&1
if not errorlevel 1 ( echo  WARNING: Port 8000 is in use. & set PORT_OK=0 )

netstat -an 2>nul | find "0.0.0.0:3000" >nul 2>&1
if not errorlevel 1 ( echo  WARNING: Port 3000 is in use. & set PORT_OK=0 )

if !PORT_OK!==1 ( echo  All ports are available. )

:: ============================================================
:: 4. START SERVICES
:: ============================================================
echo.
echo [4/5] Starting services with Docker Compose...
echo.

docker compose --env-file .env.development up -d --build
if errorlevel 1 (
    echo.
    echo  ERROR: docker compose failed. See output above.
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
        netstat -an 2>nul | find "0.0.0.0:5432" >nul 2>&1
        if not errorlevel 1 ( set DB_READY=1 ) else ( <nul set /p "=." & timeout /t 2 /nobreak >nul )
    )
)
echo.
if !DB_READY!==1 ( echo  PostgreSQL is up. ) else ( echo  WARNING: PostgreSQL not ready yet, continuing... )

:: --- Backend ---
echo  Waiting for Backend API...
set BACKEND_READY=0
for /l %%i in (1,1,45) do (
    if !BACKEND_READY!==0 (
        curl -s -o nul -w "%%{http_code}" http://localhost:8000/health 2>nul | find "200" >nul 2>&1
        if not errorlevel 1 (
            set BACKEND_READY=1
        ) else (
            netstat -an 2>nul | find "0.0.0.0:8000" >nul 2>&1
            if not errorlevel 1 ( set BACKEND_READY=1 ) else ( <nul set /p "=." & timeout /t 2 /nobreak >nul )
        )
    )
)
echo.
if !BACKEND_READY!==1 ( echo  Backend is up. ) else ( echo  WARNING: Backend not ready yet, continuing... )

:: --- Frontend ---
echo  Waiting for Frontend...
set FRONTEND_READY=0
for /l %%i in (1,1,60) do (
    if !FRONTEND_READY!==0 (
        curl -s -o nul -w "%%{http_code}" http://localhost:3000 2>nul | find "200" >nul 2>&1
        if not errorlevel 1 (
            set FRONTEND_READY=1
        ) else (
            netstat -an 2>nul | find "0.0.0.0:3000" >nul 2>&1
            if not errorlevel 1 ( set FRONTEND_READY=1 ) else ( <nul set /p "=." & timeout /t 2 /nobreak >nul )
        )
    )
)
echo.
if !FRONTEND_READY!==1 ( echo  Frontend is up. ) else ( echo  WARNING: Frontend not ready yet, opening browser anyway... )

:: ============================================================
:: DONE - OPEN BROWSER
:: ============================================================
echo.
echo ============================================================
echo  All services started!
echo.
echo  Frontend : http://localhost:3000/login
echo  Backend  : http://localhost:8000/docs
echo  Database : localhost:5432
echo ============================================================
echo.

start "" "http://localhost:3000/login"

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
