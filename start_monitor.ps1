# Start the monitor with the project folder as its working directory.
# This matters because the program uses relative paths such as data/metrics.db.

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$monitorPath = Join-Path $projectRoot 'build\bin\Release\system_monitor.exe'

if (-not (Test-Path $monitorPath)) {
    throw "Monitor executable not found: $monitorPath"
}

$running = Get-Process system_monitor -ErrorAction SilentlyContinue
if ($running) {
    Write-Host 'The monitor is already running.'
    exit 0
}

Start-Process `
    -FilePath $monitorPath `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden

Write-Host 'Monitor started in the background.'
Write-Host 'Database: data\metrics.db'
Write-Host 'Log: system_monitor.log'
