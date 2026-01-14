@echo off
REM TSG Safety Tracker Server Management Script (Windows Batch)
REM This script manages the TSG Safety Tracker server with auto-restart capability

echo ============================================================
echo TSG Safety Tracker Server Manager
echo ============================================================
echo.

:menu
echo Choose an option:
echo   1. Start server (stable mode, no auto-reload)
echo   2. Start server (development mode, with auto-reload)
echo   3. Stop all server processes
echo   4. Restart server
echo   5. Clear cache and start server
echo   6. View server status
echo   7. Exit
echo.
set /p choice="Enter choice (1-7): "

if "%choice%"=="1" goto start_stable
if "%choice%"=="2" goto start_dev
if "%choice%"=="3" goto stop
if "%choice%"=="4" goto restart
if "%choice%"=="5" goto clear_and_start
if "%choice%"=="6" goto status
if "%choice%"=="7" goto end
goto menu

:start_stable
echo.
echo Starting server in STABLE mode (no auto-reload)...
echo This mode is more stable and won't hang on file changes.
echo.
python run.py --no-reload
goto menu

:start_dev
echo.
echo Starting server in DEVELOPMENT mode (with auto-reload)...
echo Server will automatically restart when files change.
echo.
python run.py
goto menu

:stop
echo.
echo Stopping all Python server processes...
for /f "tokens=2" %%i in ('tasklist ^| findstr python.exe') do (
    echo Killing process %%i
    taskkill //F //PID %%i 2>nul
)
echo All server processes stopped.
echo.
pause
goto menu

:restart
echo.
echo Restarting server...
call :stop
timeout /t 2 /nobreak >nul
call :clear_and_start
goto menu

:clear_and_start
echo.
echo Clearing cache and starting server...
python run.py --clear-cache --no-reload
goto menu

:status
echo.
echo Checking server status...
tasklist | findstr python.exe
if errorlevel 1 (
    echo No Python processes running.
) else (
    echo Python processes found above.
)
echo.
echo Checking if port 8000 is in use...
netstat -ano | findstr :8000
if errorlevel 1 (
    echo Port 8000 is free.
) else (
    echo Port 8000 is in use.
)
echo.
pause
goto menu

:end
echo.
echo Exiting...
exit /b 0
