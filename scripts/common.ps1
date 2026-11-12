$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
function Get-ProjectPython {
    if ($env:MARKET_PYTHON) { return $env:MARKET_PYTHON }
    $savedPath = Join-Path $ProjectRoot '.runtime/python-executable.txt'
    if (Test-Path $savedPath) {
        $saved = (Get-Content -LiteralPath $savedPath -Raw).Trim()
        if (Test-Path -LiteralPath $saved) { return $saved }
    }
    $bundled = Get-ChildItem -Path 'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.*\dependencies\python\python.exe' -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
    if ($bundled) { return $bundled.FullName }
    $installed = Get-Command python -ErrorAction SilentlyContinue
    if ($installed -and $installed.Source -notlike '*WindowsApps*') { return $installed.Source }
    throw 'Set MARKET_PYTHON to a Python 3.12+ executable, or run inside Codex with its bundled runtime.'
}
$ProjectPython = Get-ProjectPython
$env:PYTHONPATH = "$ProjectRoot\.runtime\python;$ProjectRoot"
