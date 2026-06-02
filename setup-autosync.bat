@echo off
setlocal

set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"
set "SYNC_BAT=%REPO%\sync-to-github.bat"
set "TASK_NAME=FMCG-ERP-GitSync"

echo.
echo  ============================================
echo   FMCG ERP ^| Auto-Sync Setup
echo   Syncs local changes to GitHub every 5 min
echo  ============================================
echo.

:: Remove old task if it exists
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Register new task — runs silently every 5 minutes, no popup window
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "cmd /c \"%SYNC_BAT%\" >> \"%REPO%\git-sync.log\" 2>&1" ^
    /sc MINUTE ^
    /mo 5 ^
    /f ^
    /rl HIGHEST ^
    /it

if %errorlevel% equ 0 (
    echo  Task registered: "%TASK_NAME%" runs every 5 minutes.
    echo.
    echo  Your changes will be pushed to GitHub automatically.
    echo  Log file: %REPO%\git-sync.log
    echo.
    echo  To stop auto-sync:
    echo    schtasks /delete /tn "%TASK_NAME%" /f
    echo.
    echo  To sync manually:
    echo    Double-click sync-to-github.bat
) else (
    echo.
    echo  WARNING: Could not register Task Scheduler job.
    echo  Please right-click setup-autosync.bat and choose
    echo  "Run as administrator", then try again.
    echo.
    echo  You can still sync manually by double-clicking:
    echo    sync-to-github.bat
)

echo.
echo  Press any key to close...
pause >nul
