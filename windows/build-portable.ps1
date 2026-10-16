# Personal local build ONLY; do not redistribute the output bundle.
param([Parameter(Mandatory=$true)][switch]$PersonalUseOnly, [switch]$IncludeNativeVulkan)
$ErrorActionPreference='Stop'
$env:PYTHONUTF8='1'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    if (-not $PersonalUseOnly) { throw 'Read docs/windows-portable.md before acknowledging personal use.' }
    if (-not (Test-Path .\.venv\Scripts\python.exe)) { throw 'Run windows/setup-neural.ps1 first.' }
    & .\.venv\Scripts\python.exe -m pip install pyinstaller==6.16.0
    if ($LASTEXITCODE -ne 0) { throw 'Pinned PyInstaller installation failed.' }
    & .\.venv\Scripts\python.exe tools/build_neural_studio.py
    if ($LASTEXITCODE -ne 0) { throw 'Explicit presentation preparation failed.' }
    $Options = @()
    if ($IncludeNativeVulkan) { $Options += '--include-native' }
    & .\.venv\Scripts\python.exe tools/package_windows.py --personal-build @Options
    if ($LASTEXITCODE -ne 0) { throw 'Personal portable build failed.' }
    Write-Host 'Built artifacts/windows-portable/JaliStudio-Windows-x64.zip for YOUR OWN use. Do not publish it.'
} finally { Pop-Location }
