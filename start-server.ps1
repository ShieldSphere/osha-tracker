# TSG Safety Tracker Server Management Script (PowerShell)
# This script manages the TSG Safety Tracker server with auto-restart on crash

param(
    [switch]$NoReload,
    [switch]$AutoRestart,
    [switch]$Stop,
    [switch]$Status,
    [switch]$ClearCache
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

function Write-Header {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "TSG Safety Tracker Server Manager" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Stop-Server {
    Write-Host "Stopping all Python server processes..." -ForegroundColor Yellow
    Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "  Killing process $($_.Id) - $($_.Name)" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force
    }
    Write-Host "All server processes stopped." -ForegroundColor Green
}

function Get-ServerStatus {
    Write-Host "Server Status:" -ForegroundColor Cyan
    Write-Host ""

    $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
    if ($pythonProcesses) {
        Write-Host "Python processes running:" -ForegroundColor Green
        $pythonProcesses | Format-Table Id, ProcessName, CPU, WorkingSet -AutoSize
    } else {
        Write-Host "No Python processes running." -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "Port 8000 status:" -ForegroundColor Cyan
    $port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($port8000) {
        Write-Host "Port 8000 is in use by process:" -ForegroundColor Green
        $port8000 | Format-Table LocalAddress, LocalPort, State, OwningProcess -AutoSize
    } else {
        Write-Host "Port 8000 is available." -ForegroundColor Yellow
    }
}

function Clear-PythonCache {
    Write-Host "Clearing Python cache..." -ForegroundColor Yellow
    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | ForEach-Object {
        Write-Host "  Removing: $($_.FullName)" -ForegroundColor Gray
        Remove-Item -Path $_.FullName -Recurse -Force
    }
    Write-Host "Cache cleared." -ForegroundColor Green
}

function Start-ServerWithAutoRestart {
    param([bool]$noReload)

    $restartCount = 0
    $maxRestarts = 10

    while ($restartCount -lt $maxRestarts) {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host "Starting TSG Safety Tracker Server (Attempt $($restartCount + 1))" -ForegroundColor Cyan
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host ""

        $args = @()
        if ($noReload) {
            $args += "--no-reload"
        }

        try {
            $process = Start-Process -FilePath "python" -ArgumentList (@("run.py") + $args) -NoNewWindow -PassThru -Wait

            if ($process.ExitCode -eq 0) {
                Write-Host "Server stopped gracefully." -ForegroundColor Green
                break
            } else {
                Write-Host "Server exited with code $($process.ExitCode)" -ForegroundColor Red
            }
        } catch {
            Write-Host "Server crashed: $_" -ForegroundColor Red
        }

        $restartCount++
        if ($restartCount -lt $maxRestarts) {
            Write-Host ""
            Write-Host "Auto-restarting in 5 seconds..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }

    if ($restartCount -eq $maxRestarts) {
        Write-Host ""
        Write-Host "Maximum restart attempts reached. Please check the logs." -ForegroundColor Red
    }
}

# Main script logic
Write-Header

if ($Stop) {
    Stop-Server
    exit 0
}

if ($Status) {
    Get-ServerStatus
    exit 0
}

if ($ClearCache) {
    Clear-PythonCache
}

if ($AutoRestart) {
    Write-Host "Starting server with AUTO-RESTART enabled..." -ForegroundColor Green
    Write-Host "Server will automatically restart if it crashes." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop the server completely." -ForegroundColor Yellow
    Write-Host ""
    Start-ServerWithAutoRestart -noReload $NoReload
} else {
    # Single start without auto-restart
    $args = @()
    if ($NoReload) {
        $args += "--no-reload"
        Write-Host "Starting server in STABLE mode (no auto-reload)..." -ForegroundColor Green
    } else {
        Write-Host "Starting server in DEVELOPMENT mode (with auto-reload)..." -ForegroundColor Green
    }
    Write-Host ""

    & python run.py @args
}
