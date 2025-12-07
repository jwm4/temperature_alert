# FreezeAlert Maintenance Guide

If you modify `temperature_alert.py`, you need to restart the background service for changes to take effect.

## Option 1: Using Task Scheduler (Recommended)
1. Open **Task Scheduler**.
2. Find the task named `TemperatureAlertSystem`.
3. Right-click it and select **End** (if running).
4. Right-click it again and select **Run**.

## Option 2: Using PowerShell
Run these commands in PowerShell to restart the process:

```powershell
# Stop the existing process
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue

# Start the service again (in background)
Start-Process python -ArgumentList "temperature_alert.py" -WindowStyle Hidden
```
*Note: This stops ALL python processes. Use with caution if running other python scripts.*

## Option 3: Reboot
Since the task is set to run "At Log On", simply restarting your computer will also apply the changes.

## Verification
After restarting, you can verify the service is listening by running:
```bash
python trigger_now.py
```
If it prints "Trigger sent...", the service is running.
