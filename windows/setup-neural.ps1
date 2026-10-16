# Explicit developer setup, not an installer. Requires Python 3.11 x64, Node 22 and gh.
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    foreach ($name in @('py','node','npm.cmd','gh')) { Get-Command $name -ErrorAction Stop | Out-Null }
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 x64 is required.' }
    & .\.venv\Scripts\python.exe -c "import sys,platform; assert sys.version_info[:2]==(3,11) and platform.machine().lower() in ('amd64','x86_64'), 'Use Python 3.11 x64'"
    if ($LASTEXITCODE -ne 0) { throw 'Unsupported Python interpreter.' }
    & .\.venv\Scripts\python.exe -m pip install -r tools/requirements-neural-studio.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & npm.cmd ci --prefix tools --ignore-scripts
    if ($LASTEXITCODE -ne 0) { throw 'Node dependency setup failed.' }
    & .\.venv\Scripts\python.exe tools/prepare_kokoro_cpu.py
    if ($LASTEXITCODE -ne 0) { throw 'Checksum-pinned speech setup failed.' }
    & .\.venv\Scripts\python.exe tools/build_neural_studio.py
    if ($LASTEXITCODE -ne 0) { throw 'Character/analyzer setup failed. Check GitHub CLI public-source access.' }
    Write-Host 'Setup complete. Run .\windows\start-neural.ps1 in this repository.'
} finally { Pop-Location }
