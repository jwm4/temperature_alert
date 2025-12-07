$ErrorActionPreference = "Stop"
try {
    $PythonPath = (Get-Command python).Source
} catch {
    Write-Error "Python not found in PATH. Please ensure Python is installed and added to PATH."
    exit 1
}

$ScriptPath = Join-Path $PSScriptRoot "temperature_alert.py"

$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument $ScriptPath
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Hidden -ExecutionTimeLimit (New-TimeSpan -Days 0)
$TaskName = "TemperatureAlertSystem"

Register-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -TaskName $TaskName -Description "Continuous background service for temperature alerts." -Force

Write-Host "Task '$TaskName' updated successfully. It will run automatically when you log in."
Write-Host "You can also start it manually now via Task Scheduler or by running the python script."
Write-Host "To test it now, open Task Scheduler, find '$TaskName', right-click and select 'Run'."
