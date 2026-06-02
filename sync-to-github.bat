@echo off
setlocal enabledelayedexpansion

set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"
set "GIT=C:\Program Files\Git\cmd\git.exe"
set "LOG=%REPO%\git-sync.log"

cd /d "%REPO%"

echo.
echo  ============================================
echo   FMCG ERP ^| Sync to GitHub
echo  ============================================
echo.

:: Stage all changes (respects .gitignore)
"%GIT%" add -A

:: Check if anything is staged
"%GIT%" diff --cached --quiet
if %errorlevel% equ 0 (
    echo  Nothing to sync - working tree is already clean.
    echo  [%date% %time%] Nothing to sync - clean. >> "%LOG%"
    goto :done
)

:: Count changed files
set FILES=0
for /f %%c in ('"%GIT%" diff --cached --name-only ^| find /c /v ""') do set FILES=%%c

:: Build timestamp
set "YY=%date:~-4%"
set "MM=%date:~4,2%"
set "DD=%date:~7,2%"
set "HH=%time:~0,2%"
set "MN=%time:~3,2%"
set "HH=!HH: =0!"
set "STAMP=!YY!-!MM!-!DD! !HH!:!MN!"

set "MSG=Auto-sync: !FILES! file(s) [!STAMP!]"

echo  Staging:  !FILES! file(s)
echo  Message:  !MSG!
echo.
echo  Committing...
"%GIT%" commit -m "!MSG!"
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Commit failed. See output above.
    echo  [!STAMP!] ERROR: commit failed >> "%LOG%"
    goto :error
)

echo.
echo  Pushing to GitHub ^(origin/main^)...
"%GIT%" push origin main
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Push failed. Check internet / GitHub credentials.
    echo  [!STAMP!] ERROR: push failed >> "%LOG%"
    goto :error
)

echo.
echo  ============================================
echo   SUCCESS - !FILES! file(s) pushed to GitHub!
echo  ============================================
echo  [!STAMP!] SUCCESS: pushed !FILES! file(s) >> "%LOG%"
goto :done

:error
echo.
echo  ============================================
echo   SYNC FAILED - see error above
echo  ============================================

:done
