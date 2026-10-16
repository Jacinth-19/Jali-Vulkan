# Optional source build after setup-neural.ps1. Needs CMake + Visual Studio C++ x64 tools.
# Never installs a system GPU driver or silently substitutes software for hardware.
param([switch]$SoftwareForTesting)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    if (-not (Test-Path .\.venv\Scripts\python.exe)) { throw 'Run windows/setup-neural.ps1 first.' }
    foreach ($name in @('cmake','node')) { Get-Command $name -ErrorAction Stop | Out-Null }
    if (-not (Test-Path artifacts/neural-head-demo/model/mpfb-head.glb)) { throw 'Prepare the licensed head with windows/setup-neural.ps1 first.' }
    & .\.venv\Scripts\python.exe tools/build_native_head.py
    if ($LASTEXITCODE -ne 0) { throw 'Native character conversion failed.' }
    & node tools/validate_native_head.cjs artifacts/native-head/mpfb-native.glb artifacts/native-head/validation.json
    if ($LASTEXITCODE -ne 0) { throw 'Native GLB validation failed.' }
    $Options = @()
    if ($SoftwareForTesting) { $Options += '--ci-software' }
    & .\.venv\Scripts\python.exe tools/setup_windows_native.py @Options
    if ($LASTEXITCODE -ne 0) { throw 'Source build failed. Install CMake and the Visual Studio C++ x64 build tools/Windows SDK; inspect the compiler output.' }
    Write-Host 'Native build ready. Run .\windows\start-neural.ps1 -NativeVulkan'
    if ($SoftwareForTesting) { Write-Host 'Software test ONLY: add -SoftwareVulkanForTesting to the start command. Not a laptop GPU benchmark.' }
} finally { Pop-Location }
