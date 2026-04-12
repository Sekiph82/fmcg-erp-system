@echo off
setlocal enabledelayedexpansion

:: Re-launch with cmd /k so window stays open
if "%~1"=="--started" goto :main
cmd /k "%~f0" --started
exit /b

:main
title FMCG ERP - Git Auto-Sync Setup
cd /d "%~dp0"

echo.
echo ============================================================
echo  FMCG ERP - GitHub Auto-Sync Setup
echo  Run this ONCE. After this, your folder will stay in sync
echo  with GitHub automatically every 5 minutes.
echo ============================================================
echo.

set REPO_URL=https://github.com/Sekiph82/fmcg-erp-system.git
set REPO_DIR=%~dp0

:: ============================================================
:: 1. CHECK GIT IS INSTALLED
:: ============================================================
echo [1/4] Checking Git...

git --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Git is not installed on this machine.
    echo.
    echo  Please download and install Git from:
    echo  https://git-scm.com/download/win
    echo.
    echo  After installing Git, run this script again.
    echo.
    goto :error
)

for /f "tokens=*" %%v in ('git --version') do set GIT_VER=%%v
echo  Git found: !GIT_VER!

:: ============================================================
:: 2. CONNECT THIS FOLDER TO GITHUB
:: ============================================================
echo.
echo [2/4] Connecting folder to GitHub...

:: Check if already a git repo
if exist ".git\" (
    echo  Git already initialized in this folder.
    :: Make sure remote is set correctly
    git remote set-url origin %REPO_URL% >nul 2>&1
    if errorlevel 1 (
        git remote add origin %REPO_URL% >nul 2>&1
    )
    echo  Remote set to: %REPO_URL%
) else (
    echo  Initializing Git in this folder...
    git init >nul 2>&1
    git remote add origin %REPO_URL% >nul 2>&1
    echo  Remote set to: %REPO_URL%
)

:: Fetch and sync with GitHub (hard reset to match remote exactly)
echo.
echo  Fetching latest code from GitHub...
git fetch origin main >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Could not reach GitHub. Check your internet connection.
    goto :error
)

git checkout -B main >nul 2>&1
git reset --hard origin/main >nul 2>&1
git branch --set-upstream-to=origin/main main >nul 2>&1

echo  Folder is now in sync with GitHub.

:: ============================================================
:: 3. CREATE AUTO-PULL SCRIPT
:: ============================================================
echo.
echo [3/4] Creating auto-pull script...

set PULL_SCRIPT=%REPO_DIR%git-auto-pull.bat

(
    echo @echo off
    echo cd /d "%REPO_DIR%"
    echo git pull origin main --ff-only ^>^>"%REPO_DIR%git-sync.log" 2^>^&1
) > "%PULL_SCRIPT%"

echo  Created: git-auto-pull.bat

:: ============================================================
:: 4. REGISTER WINDOWS TASK SCHEDULER
:: ============================================================
echo.
echo [4/4] Setting up Windows Task Scheduler (every 5 minutes)...

:: Delete existing task if it exists
schtasks /delete /tn "FMCG-ERP-GitSync" /f >nul 2>&1

:: Create new scheduled task
schtasks /create ^
    /tn "FMCG-ERP-GitSync" ^
    /tr "cmd /c \"%PULL_SCRIPT%\"" ^
    /sc MINUTE ^
    /mo 5 ^
    /f ^
    /rl HIGHEST >nul 2>&1

if errorlevel 1 (
    echo.
    echo  WARNING: Could not register Task Scheduler job.
    echo  You may need to run this script as Administrator.
    echo  Right-click setup-git-sync.bat and choose "Run as administrator".
    echo.
    echo  Auto-sync will NOT run automatically until this is fixed.
    echo  You can still sync manually by double-clicking: git-auto-pull.bat
    echo.
) else (
    echo  Task registered: "FMCG-ERP-GitSync" runs every 5 minutes.
)

:: ============================================================
:: DONE
:: ============================================================
echo.
echo ============================================================
echo  Setup complete!
echo.
echo  Your folder is now connected to:
echo  %REPO_URL%
echo.
echo  Auto-sync: every 5 minutes in the background
echo  Sync log:  %REPO_DIR%git-sync.log
echo.
echo  To sync manually at any time:
echo    Double-click git-auto-pull.bat
echo.
echo  To remove auto-sync:
echo    schtasks /delete /tn "FMCG-ERP-GitSync" /f
echo ============================================================
echo.
echo  Press any key to close...
pause >nul
exit /b 0

:error
echo.
echo  Setup failed. This window will stay open so you can read the error above.
echo  Press any key to close...
pause >nul
exit /b 1
