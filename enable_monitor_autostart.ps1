# Register the monitor to start automatically when the current user signs in.
# This uses Windows Task Scheduler and does not require the terminal to stay open.

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherPath = Join-Path $projectRoot 'start_monitor.ps1'
$taskName = 'System Resource Performance Monitor'

if (-not (Test-Path $launcherPath)) {
    throw "Launcher script not found: $launcherPath"
}

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$launcherPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host "Automatic startup enabled for: $taskName"
Write-Host 'The monitor will start the next time you sign in to Windows.'
