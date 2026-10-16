# No installs, elevation or execution-policy changes.
$ErrorActionPreference='Stop'
$Python=Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Run windows/setup-neural.ps1 first.' }
& $Python (Join-Path $PSScriptRoot '..\tools\studio_launcher.py')
exit $LASTEXITCODE
