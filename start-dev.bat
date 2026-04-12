@echo off
setlocal enabledelayedexpansion
title FMCG ERP - Dev Startup

:: ============================================================
:: FMCG ERP System - Windows Development Startup Script
:: Double-click to start all services and open the browser.
:: ============================================================

:: --- Navigate to project root (the folder this .bat lives in) ---
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
if errorlevel 1 (
    echo  Docker is not running. Starting Docker Desktop automatically...
    echo.

    :: --- Try to find and launch Docker Desktop ---
    set DOCKER_EXE=
    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        set DOCKER_EXE=C:\Program Files\Docker\Docker\Docker Desktop.exe
    ) else if exist "%LOCALAPPDATA%\Docker\Docker Desktop.exe" (
        set DOCKER_EXE=%LOCALAPPDATA%\Docker\Docker Desktop.exe
    ) else if exist "%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe" (
        set DOCKER_EXE=%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe
    )

    if "!DOCKER_EXE!"=="" (
        echo  ERROR: Docker Desktop not found on this machine.
        echo.
        echo  Please install Docker Desktop from:
        echo  https://www.docker.com/products/docker-desktop
        echo.
        pause
        exit /b 1
    )

    start "" "!DOCKER_EXE!"
    echo  Docker Desktop is starting. Waiting for engine to be ready...
    echo  (This may take up to 60 seconds on first launch)
    echo.

    :: --- Wait up to 90 seconds for Docker engine to respond ---
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

    if !DOCKER_READY!==0 (
        echo.
        echo  ERROR: Docker engine did not start within 90 seconds.
        echo  Please open Docker Desktop manually and wait for it to finish
        echo  loading, then run this script again.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo  Docker is ready.
) else (
    echo  Docker is already running.
)

:: ============================================================
:: 2. CHECK ENV FILE
:: ============================================================
echo [2/5] Checking environment file...

if not exist ".env.development" (
    echo.
    echo  WARNING: .env.development not found.
    echo.
    echo  Creating from .env.example...
    if exist ".env.example" (
        copy ".env.example" ".env.development" >nul
        echo  Created .env.development from .env.example.
        echo  Please review and update .env.development with your settings.
        echo.
    ) else (
        echo  ERROR: .env.example also missing. Cannot create .env.development.
        echo  Please create .env.development manually before starting.
        echo.
        pause
        exit /b 1
    )
) else (
    echo        .env.development found.
)

:: ============================================================
:: 3. CHECK PORTS
:: ============================================================
echo [3/5] Checking ports...

set PORT_OK=1

netstat -an 2>nul | find "0.0.0.0:5432" >nul 2>&1
if not errorlevel 1 (
    echo  WARNING: Port 5432 ^(PostgreSQL^) is already in use.
    echo           Docker Compose may conflict. Stop the existing service first.
    set PORT_OK=0
)

netstat -an 2>nul | find "0.0.0.0:8000" >nul 2>&1
if not errorlevel 1 (
    echo  WARNING: Port 8000 ^(Backend^) is already in use.
    echo           Docker Compose may conflict. Stop the existing service first.
    set PORT_OK=0
)

netstat -an 2>nul | find "0.0.0.0:3000" >nul 2>&1
if not errorlevel 1 (
    echo  WARNING: Port 3000 ^(Frontend^) is already in use.
    echo           Docker Compose may conflict. Stop the existing service first.
    set PORT_OK=0
)

if !PORT_OK!==0 (
    echo.
    set /p CONTINUE="  Continue anyway? [y/N]: "
    if /i not "!CONTINUE!"=="y" (
        echo  Aborted.
        pause
        exit /b 1
    )
) else (
    echo        All ports available.
)

:: ============================================================
:: 4. START SERVICES
:: ============================================================
echo [4/5] Starting services with Docker Compose...
echo.

docker compose --env-file .env.development up -d --build
if errorlevel 1 (
    echo.
    echo  ERROR: docker compose failed to start services.
    echo  Check the output above for details.
    echo.
    pause
    exit /b 1
)

echo.
echo  Services starting in background...

:: ============================================================
:: 5. HEALTH CHECKS - Wait for readiness
:: ============================================================
echo [5/5] Waiting for services to become ready...
echo.

:: --- Wait for PostgreSQL ---
echo  Waiting for PostgreSQL (port 5432)...
set DB_READY=0
for /l %%i in (1,1,30) do (
    if !DB_READY!==0 (
        netstat -an 2>nul | find "0.0.0.0:5432" >nul 2>&1
        if not errorlevel 1 (
            set DB_READY=1
        ) else (
            <nul set /p "=."
            timeout /t 2 /nobreak >nul
        )
    )
)
if !DB_READY!==0 (
    echo.
    echo  WARNING: PostgreSQL did not become available in time.
    echo           Services may still be initializing.
) else (
    echo.
    echo  PostgreSQL is up.
)

:: --- Wait for Backend ---
echo  Waiting for Backend API (port 8000)...
set BACKEND_READY=0
for /l %%i in (1,1,45) do (
    if !BACKEND_READY!==0 goto :backend_done
    curl -s -o nul -w "%%{http_code}" http://localhost:8000/health 2>nul | find "200" >nul 2>&1
    if not errorlevel 1 (
        set BACKEND_READY=1
    ) else (
        :: fallback: check if port is open
        netstat -an 2>nul | find "0.0.0.0:8000" >nul 2>&1
        if not errorlevel 1 (
            set BACKEND_READY=1
        ) else (
            <nul set /p "=."
            timeout /t 2 /nobreak >nul
        )
    )
)
:backend_done
if !BACKEND_READY!==0 (
    echo.
    echo  WARNING: Backend did not become available in time.
    echo           It may still be building or initializing.
) else (
    echo.
    echo  Backend is up.
)

:: --- Wait for Frontend ---
echo  Waiting for Frontend (port 3000)...
set FRONTEND_READY=0
for /l %%i in (1,1,60) do (
    if !FRONTEND_READY!==0 goto :frontend_done
    curl -s -o nul -w "%%{http_code}" http://localhost:3000 2>nul | find "200" >nul 2>&1
    if not errorlevel 1 (
        set FRONTEND_READY=1
    ) else (
        :: fallback: check if port is open
        netstat -an 2>nul | find "0.0.0.0:3000" >nul 2>&1
        if not errorlevel 1 (
            set FRONTEND_READY=1
        ) else (
            <nul set /p "=."
            timeout /t 2 /nobreak >nul
        )
    )
)
:frontend_done
if !FRONTEND_READY!==0 (
    echo.
    echo  WARNING: Frontend did not become available in 2 minutes.
    echo           It may still be building. Try opening the browser manually.
) else (
    echo.
    echo  Frontend is up.
)

:: ============================================================
:: OPEN BROWSER
:: ============================================================
echo.
echo ============================================================
echo  All services started.
echo.
echo  Frontend:  http://localhost:3000/login
echo  Backend:   http://localhost:8000/docs
echo  Database:  localhost:5432
echo ============================================================
echo.

echo  Opening browser to login page...
start "" "http://localhost:3000/login"

:: ============================================================
:: SHOW RUNNING CONTAINERS
:: ============================================================
echo.
echo  Running containers:
echo.
docker compose --env-file .env.development ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo.
echo ============================================================
echo  Tip: To view logs, run:
echo       docker compose --env-file .env.development logs -f
echo.
echo  Tip: To stop all services, run:
echo       docker compose --env-file .env.development down
echo ============================================================
echo.
pause
endlocal
