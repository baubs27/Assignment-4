. "$PSScriptRoot/common.ps1"
Push-Location $ProjectRoot
try {
    $env:MARKET_LIVE = '0'
    $testTemp = Join-Path $ProjectRoot ('.runtime/test-' + [guid]::NewGuid().ToString('N'))
    & $ProjectPython -m pytest tests -q --tb=short --basetemp $testTemp
    exit $LASTEXITCODE
} finally { Pop-Location }
