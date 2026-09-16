param([switch]$Setup, [switch]$LexicalOnly, [switch]$Rebuild, [int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$signalPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.venv313\Scripts\python.exe')) {
    $signalPython = Join-Path $PSScriptRoot '.venv313\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $signalPython)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.13 is required. Install Python and retry.' }
    $Setup = $true
}
if ($Setup) {
    & $signalPython -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare pip.' }
    $signalRequirements = if ($LexicalOnly) { 'requirements.txt' } else { 'requirements-ml.txt' }
    & $signalPython -m pip install -r $signalRequirements
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    if (-not $LexicalOnly) {
        & $signalPython -m scripts.setup_models
        if ($LASTEXITCODE -ne 0) { throw 'Model setup failed. Retry setup or use lexical discovery from Data.' }
    }
}
& $signalPython -c 'import fastapi, uvicorn, multipart, langdetect, sklearn, numpy'
if ($LASTEXITCODE -ne 0) { throw 'Dependencies are missing. Run .\start.ps1 -Setup.' }
if ($Rebuild -or -not (Test-Path -LiteralPath 'frontend\dist\index.html')) {
    Push-Location frontend
    try {
        npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
}
Write-Host "Feedback review is starting at http://127.0.0.1:$Port — press Ctrl+C to stop."
& $signalPython -m uvicorn api.main:app --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
