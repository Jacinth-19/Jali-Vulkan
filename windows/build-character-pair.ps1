# Personal paired WebGL build. Run windows/setup-neural.ps1 explicitly first.
param([Parameter(Mandatory=$true)][switch]$PersonalUseOnly,[switch]$NoArchive)
$ErrorActionPreference='Stop'
$env:PYTHONUTF8='1'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    if (-not $PersonalUseOnly) { throw 'Personal acknowledgement required. Do not redistribute the bundle.' }
    $python='.venv/Scripts/python.exe'
    if (-not (Test-Path $python)) { throw 'Run windows/setup-neural.ps1 first.' }
    & $python -m pip install -r tools/requirements-male-build.txt pyinstaller==6.16.0
    if ($LASTEXITCODE -ne 0) { throw 'Explicit build dependency preparation failed.' }
    & $python tools/studio_voices.py --install am_michael
    if ($LASTEXITCODE -ne 0) { throw 'Explicit male voice preparation failed.' }
    & $python tools/build_neural_studio.py
    if ($LASTEXITCODE -ne 0) { throw 'Female studio preparation failed.' }
    & $python tools/prepare_makehuman_male.py
    if ($LASTEXITCODE -ne 0) { throw 'Official male variant preparation failed.' }
    & $python tools/build_neural_studio.py --character artifacts/male-character --output artifacts/male-studio
    if ($LASTEXITCODE -ne 0) { throw 'Male studio preparation failed.' }
    $Options=@()
    if ($NoArchive) { $Options+='--no-archive' }
    & $python tools/package_windows.py --personal-build --studio artifacts/male-studio --female-studio artifacts/neural-studio @Options
    if ($LASTEXITCODE -ne 0) { throw 'Personal paired WebGL package failed.' }
    Write-Host 'Male-default EXE with male/female selector prepared. WebGL only; no native profile fallback.'
    Write-Host 'Back up user data and export browser profiles before replacing a build. Public redistribution is not cleared.'
} finally { Pop-Location }
