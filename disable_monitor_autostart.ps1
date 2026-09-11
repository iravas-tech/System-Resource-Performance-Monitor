# Remove automatic startup and stop the currently running monitor.

$taskName = 'System Resource Performance Monitor'
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

Get-Process system_monitor -ErrorAction SilentlyContinue | Stop-Process

Write-Host 'Automatic startup disabled.'
Write-Host 'The monitor process was stopped if it was running.'
