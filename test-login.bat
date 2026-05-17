@echo off
setlocal enabledelayedexpansion

title FMCG ERP - Login Smoke Test
cd /d "%~dp0"

echo.
echo ============================================================
echo  FMCG ERP - Login Smoke Test
echo ============================================================
echo.

:: ── Read credentials from .env.development ───────────────────────────────────
set "ADMIN_USER="
set "ADMIN_PASS="

if not exist ".env.development" (
    echo  ERROR: .env.development not found.
    echo  Run start-dev.bat first or copy .env.development.example to .env.development.
    goto :fail
)

for /f "usebackq tokens=1,* delims==" %%A in (".env.development") do (
    set "KEY=%%A"
    set "VAL=%%B"
    if "!KEY!"=="INITIAL_ADMIN_USERNAME" set "ADMIN_USER=!VAL!"
    if "!KEY!"=="INITIAL_ADMIN_PASSWORD" set "ADMIN_PASS=!VAL!"
)

if "!ADMIN_USER!"=="" (
    echo  ERROR: INITIAL_ADMIN_USERNAME not found in .env.development.
    goto :fail
)
if "!ADMIN_PASS!"=="" (
    echo  ERROR: INITIAL_ADMIN_PASSWORD not found in .env.development.
    goto :fail
)

echo  Credentials loaded from .env.development
echo  Username : !ADMIN_USER!
echo  Password : (hidden)
echo.

:: ── Step 1: Backend health check ─────────────────────────────────────────────
echo [1/3] Backend health check...
echo.

curl -s -o NUL -w "  HTTP status: %%{http_code}\n" http://localhost:8000/health
if errorlevel 1 (
    echo.
    echo  BACKEND DOWN: curl could not reach http://localhost:8000/health
    echo  Make sure the containers are running: docker compose --env-file .env.development ps
    goto :fail
)

curl -s http://localhost:8000/health > "%TEMP%\erp_health.json" 2>nul
set /p HEALTH_BODY=<"%TEMP%\erp_health.json"
echo  Response: !HEALTH_BODY!
echo.

echo [2/3] Testing login...
echo.

:: ── Step 2: POST login, save cookie ──────────────────────────────────────────
set "COOKIE_FILE=%TEMP%\erp_test_cookie.txt"
if exist "!COOKIE_FILE!" del "!COOKIE_FILE!"

curl -s -i ^
  -c "!COOKIE_FILE!" ^
  -X POST "http://localhost:8000/api/v1/auth/login" ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  -d "username=!ADMIN_USER!&password=!ADMIN_PASS!" ^
  -o "%TEMP%\erp_login_response.txt" ^
  -w "%%{http_code}" > "%TEMP%\erp_login_status.txt" 2>nul

set /p LOGIN_STATUS=<"%TEMP%\erp_login_status.txt"
echo  Login HTTP status: !LOGIN_STATUS!

if "!LOGIN_STATUS!"=="200" goto :login_ok
if "!LOGIN_STATUS!"=="201" goto :login_ok

echo.
echo  LOGIN FAILED: credentials rejected (HTTP !LOGIN_STATUS!).
echo.
echo  Possible causes:
echo    - Admin password in database differs from INITIAL_ADMIN_PASSWORD in .env.development
echo    - Account is locked (too many failed attempts)
echo    - Backend is not fully started
echo.
echo  Fix: run the password reset script:
echo    docker compose --env-file .env.development exec backend python scripts/reset_dev_admin_password.py
echo.
goto :fail

:login_ok
echo  Login succeeded.
echo.

:: ── Step 3: GET /auth/me with cookie ─────────────────────────────────────────
echo [3/3] Testing /auth/me...
echo.

curl -s -o "%TEMP%\erp_me_response.txt" ^
  -b "!COOKIE_FILE!" ^
  -w "%%{http_code}" ^
  "http://localhost:8000/api/v1/auth/me" > "%TEMP%\erp_me_status.txt" 2>nul

set /p ME_STATUS=<"%TEMP%\erp_me_status.txt"
echo  /auth/me HTTP status: !ME_STATUS!

if "!ME_STATUS!"=="200" goto :me_ok

echo.
echo  LOGIN COOKIE FAILED: login succeeded but /auth/me returned HTTP !ME_STATUS!.
echo  This usually means cookie or CORS configuration is wrong, or DB tables are missing.
echo.
echo  Check backend logs:
echo    docker compose --env-file .env.development logs backend --tail 50
echo.
goto :fail

:me_ok
set /p ME_BODY=<"%TEMP%\erp_me_response.txt"
echo  Response: !ME_BODY:~0,200!...
echo.
echo ============================================================
echo  LOGIN OK: !ADMIN_USER! credentials work and /auth/me works.
echo ============================================================
echo.
goto :done

:fail
echo ============================================================
echo  TEST FAILED. See messages above.
echo ============================================================
echo.

:done
:: Clean up temp files
if exist "%TEMP%\erp_health.json"       del "%TEMP%\erp_health.json"
if exist "%TEMP%\erp_login_response.txt" del "%TEMP%\erp_login_response.txt"
if exist "%TEMP%\erp_login_status.txt"  del "%TEMP%\erp_login_status.txt"
if exist "%TEMP%\erp_me_response.txt"   del "%TEMP%\erp_me_response.txt"
if exist "%TEMP%\erp_me_status.txt"     del "%TEMP%\erp_me_status.txt"
if exist "!COOKIE_FILE!"                del "!COOKIE_FILE!"

echo  Press any key to close...
pause >nul
endlocal
