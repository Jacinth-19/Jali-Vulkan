# No downloads or installs. Bind only to this Windows machine by default.
param([ValidateRange(1024,65535)][int]$Port=8082)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    if (-not (Test-Path .\.venv\Scripts\python.exe)) { throw 'Run windows/setup-neural.ps1 first.' }
    Write-Host "After the server starts, open http://localhost:$Port in Edge or Chrome. Ctrl+C stops it."
    & .\.venv\Scripts\python.exe tools/neural_studio_server.py --bind 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Studio failed; check setup, asset hashes and port availability.' }
} finally { Pop-Location }
