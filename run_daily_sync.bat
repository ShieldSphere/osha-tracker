@echo off
REM ============================================================
REM TSG Safety Tracker Daily Sync - API-based
REM ============================================================
REM
REM This script syncs NEW OSHA records from the DOL API.
REM It only fetches inspections with open_date > your latest record.
REM
REM USAGE:
REM   run_daily_sync.bat           - Run with default 50 max requests
REM   run_daily_sync.bat 100       - Run with 100 max requests
REM   run_daily_sync.bat 50 silent - Run silently (for Task Scheduler)
REM
REM TASK SCHEDULER SETUP:
REM 1. Open Task Scheduler
REM 2. Create Basic Task -> Name: "TSG Safety Tracker Daily Sync"
REM 3. Trigger: Daily at 6:00 AM
REM 4. Action: Start a program
REM 5. Program: cmd.exe
REM 6. Arguments: /c "c:\Users\matt\TSG Safety\Applications\OSHA Tracker\run_daily_sync.bat" 50 silent
REM 7. Start in: c:\Users\matt\TSG Safety\Applications\OSHA Tracker
REM
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo TSG Safety Tracker Daily Sync (API) - %date% %time%
echo ============================================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Set max requests (default 50)
set MAX_REQUESTS=50
if not "%1"=="" if not "%1"=="silent" set MAX_REQUESTS=%1

echo Max API requests: %MAX_REQUESTS%
echo.

REM Run the API sync
echo Fetching new records from DOL OSHA API...
python -m src.services.api_sync_service %MAX_REQUESTS%

REM Log completion
echo. >> sync_log.txt
echo [%date% %time%] API Sync completed (max %MAX_REQUESTS% requests) >> sync_log.txt

echo.
echo ============================================================
echo Sync complete!
echo ============================================================

REM Only pause if running interactively (not silent mode)
if not "%1"=="silent" if not "%2"=="silent" pause
