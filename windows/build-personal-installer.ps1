# Optional unsigned per-user installer. Never publish its output.
param([Parameter(Mandatory=$true)][switch]$PersonalUseOnly,[string]$Compiler='',[string]$BundleDir='artifacts/windows-portable/JaliStudio',[string]$OutputDir='artifacts/windows-personal-installer')
$ErrorActionPreference='Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    if (-not $PersonalUseOnly) { throw 'Personal-use acknowledgement is required.' }
    if (-not $Compiler) { $Compiler=Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6/ISCC.exe' }
    if (-not (Test-Path $Compiler)) { throw 'Install free Inno Setup 6 (6.3 or newer), or pass -Compiler. Signing is optional.' }
    $BundleDir=[IO.Path]::GetFullPath($BundleDir);$OutputDir=[IO.Path]::GetFullPath($OutputDir)
    if (-not (Test-Path (Join-Path $BundleDir 'JaliStudio.exe'))) { throw 'First build your personal bundle with windows/build-portable.ps1 -PersonalUseOnly.' }
    & $Compiler "/DBundleDir=$BundleDir" "/DOutputDir=$OutputDir" windows/personal-installer.iss
    if ($LASTEXITCODE -ne 0) { throw 'Personal installer compilation failed.' }
    Write-Host "Unsigned personal installer: $OutputDir/JaliStudio-Personal-Setup.exe. Do not redistribute."
} finally { Pop-Location }
