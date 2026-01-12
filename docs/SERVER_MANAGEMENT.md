# OSHA Tracker - Server Management Guide

This guide provides solutions to common server stability issues and best practices for running the OSHA Tracker application.

## Quick Start

### Method 1: Batch Script (Easiest)
```bash
# Double-click or run from command prompt:
start-server.bat
```

This interactive menu lets you:
1. Start in stable mode (recommended)
2. Start in development mode
3. Stop all servers
4. Restart server
5. Clear cache and start
6. View server status

### Method 2: PowerShell (Recommended for Production)
```powershell
# Stable mode with auto-restart (best for production):
.\start-server.ps1 -NoReload -AutoRestart

# Development mode with auto-restart:
.\start-server.ps1 -AutoRestart

# Stop all servers:
.\start-server.ps1 -Stop

# Check server status:
.\start-server.ps1 -Status

# Clear cache and start:
.\start-server.ps1 -ClearCache -NoReload
```

### Method 3: Direct Python (For Debugging)
```bash
# Stable mode (no auto-reload):
python run.py --no-reload

# Development mode (with auto-reload):
python run.py

# Clear cache before starting:
python run.py --clear-cache --no-reload
```

## Common Issues & Solutions

### Issue 1: Server Crashes or Hangs

**Symptoms:**
- Server stops responding
- Application freezes
- Port 8000 becomes unavailable

**Solutions:**

1. **Use Stable Mode (No Auto-Reload)**
   ```bash
   python run.py --no-reload
   ```
   Auto-reload can cause issues when Python files change. Stable mode is more reliable.

2. **Clear Python Cache**
   ```bash
   python run.py --clear-cache --no-reload
   ```
   Stale bytecode can cause crashes. Always clear cache when troubleshooting.

3. **Use Auto-Restart**
   ```powershell
   .\start-server.ps1 -NoReload -AutoRestart
   ```
   Server will automatically restart if it crashes (up to 10 times).

### Issue 2: Port 8000 Already In Use

**Check what's using the port:**
```bash
# Windows Command Prompt:
netstat -ano | findstr :8000

# PowerShell:
Get-NetTCPConnection -LocalPort 8000
```

**Kill the process:**
```bash
# Find the PID from netstat output, then:
taskkill /F /PID <PID>

# Or use the batch script:
start-server.bat  # Choose option 3 (Stop)
```

### Issue 3: Server Won't Start

**Check for Python processes:**
```bash
tasklist | findstr python.exe
```

**Kill all Python processes:**
```bash
# Using batch script:
start-server.bat  # Choose option 3 (Stop)

# Or PowerShell:
.\start-server.ps1 -Stop

# Or manually:
taskkill /F /IM python.exe
```

**Clear cache and restart:**
```bash
python run.py --clear-cache --no-reload
```

### Issue 4: Server Stops After File Changes

**Problem:** Auto-reload causes instability

**Solution:** Use `--no-reload` flag
```bash
python run.py --no-reload
```

When developing, manually restart the server after making changes instead of relying on auto-reload.

## Production Deployment Best Practices

### Option 1: Run as Windows Service (Recommended)

1. Install NSSM (Non-Sucking Service Manager):
   ```bash
   # Download from: https://nssm.cc/download
   ```

2. Create the service:
   ```bash
   nssm install OSHATracker "C:\Path\To\Python\python.exe" "C:\Users\matt\TSG Safety\Applications\OSHA Tracker\run.py --no-reload"
   ```

3. Configure the service:
   ```bash
   nssm set OSHATracker AppDirectory "C:\Users\matt\TSG Safety\Applications\OSHA Tracker"
   nssm set OSHATracker AppStdout "C:\Users\matt\TSG Safety\Applications\OSHA Tracker\logs\server.log"
   nssm set OSHATracker AppStderr "C:\Users\matt\TSG Safety\Applications\OSHA Tracker\logs\error.log"
   nssm set OSHATracker AppRotateFiles 1
   nssm set OSHATracker AppRotateBytes 10485760
   ```

4. Start the service:
   ```bash
   nssm start OSHATracker
   ```

### Option 2: Use PowerShell Auto-Restart

Keep the server running with automatic restart on crash:
```powershell
.\start-server.ps1 -NoReload -AutoRestart
```

This will restart the server up to 10 times if it crashes.

### Option 3: Use Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: "At startup" or "At log on"
4. Action: Start a program
5. Program: `powershell.exe`
6. Arguments: `-File "C:\Users\matt\TSG Safety\Applications\OSHA Tracker\start-server.ps1" -NoReload -AutoRestart`
7. Start in: `C:\Users\matt\TSG Safety\Applications\OSHA Tracker`

## Monitoring & Debugging

### Check Server Status
```powershell
.\start-server.ps1 -Status
```

Shows:
- Running Python processes
- Port 8000 status
- Process IDs and resource usage

### View Logs
```bash
# Server logs are printed to console
# Redirect to file:
python run.py --no-reload > server.log 2>&1
```

### Health Check Endpoint
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{"status": "healthy", "service": "osha-tracker"}
```

## Performance Optimization

### Disable Auto-Reload
Always use `--no-reload` in production:
```bash
python run.py --no-reload
```

### Clear Cache Regularly
Before starting after code changes:
```bash
python run.py --clear-cache --no-reload
```

### Monitor Memory Usage
```powershell
Get-Process python | Format-Table Id, ProcessName, WorkingSet, CPU
```

If memory usage grows over time, consider:
1. Using auto-restart to periodically restart the server
2. Investigating memory leaks in the code
3. Adjusting database connection pool settings

## Troubleshooting Checklist

When server has issues:

1. ✅ Stop all running Python processes
   ```bash
   taskkill /F /IM python.exe
   ```

2. ✅ Clear Python cache
   ```bash
   python run.py --clear-cache
   ```

3. ✅ Check port 8000 is free
   ```bash
   netstat -ano | findstr :8000
   ```

4. ✅ Start in stable mode
   ```bash
   python run.py --no-reload
   ```

5. ✅ Test health endpoint
   ```bash
   curl http://localhost:8000/api/health
   ```

## Getting Help

If issues persist:

1. Check the console logs for error messages
2. Look for database connection errors
3. Verify all environment variables are set in `.env`
4. Ensure PostgreSQL/Supabase is accessible
5. Check for port conflicts with other applications

## Key Takeaways

- **Use `--no-reload` for stability** - Auto-reload causes most crash issues
- **Clear cache when troubleshooting** - Stale bytecode is a common culprit
- **Use auto-restart for production** - Server will recover from crashes automatically
- **Monitor with health checks** - Regularly test the `/api/health` endpoint
