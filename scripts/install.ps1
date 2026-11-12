. "$PSScriptRoot/common.ps1"
Push-Location $ProjectRoot
try {
    & $ProjectPython -m pip install --target .runtime/python -r backend/requirements-lock.txt
    if ($LASTEXITCODE) { throw 'Python dependency installation failed.' }
    Push-Location frontend
    try {
        npm ci
        if ($LASTEXITCODE) { throw 'Frontend dependency installation failed.' }
        npm run build
        if ($LASTEXITCODE) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
} finally { Pop-Location }
