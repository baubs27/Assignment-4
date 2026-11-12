param([switch]$Offline, [int]$Port = 8000)
. "$PSScriptRoot/common.ps1"
Push-Location $ProjectRoot
try {
    if (!(Test-Path frontend/dist/index.html)) { throw 'Run ./scripts/install.ps1 first to install and build the frontend.' }
    $env:MARKET_LIVE = if ($Offline) { '0' } else { '1' }
    Write-Host "Market Desk: http://127.0.0.1:$Port (Ctrl+C to stop)"
    & $ProjectPython -m uvicorn backend.main:app --host 127.0.0.1 --port $Port
    exit $LASTEXITCODE
} finally { Pop-Location }
