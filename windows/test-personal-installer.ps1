# Hosted-only clean user-data, install/update/uninstall regression; no uploaded installer.
$ErrorActionPreference='Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
$previous=$env:LOCALAPPDATA
try {
    $root=[IO.Path]::GetFullPath('artifacts/installer-proof');New-Item -ItemType Directory -Force $root | Out-Null
    $env:LOCALAPPDATA=Join-Path $root 'clean-profile';New-Item -ItemType Directory -Force $env:LOCALAPPDATA | Out-Null
    $install=Join-Path $root 'installed app';$setup=[IO.Path]::GetFullPath('artifacts/windows-personal-installer/JaliStudio-Personal-Setup.exe')
    $exe=Join-Path $install 'application/JaliStudio.exe'
    $args=@('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/PERSONALUSE=yes',"/DIR=`"$install`"")
    $process=Start-Process -FilePath $setup -ArgumentList $args -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "Install failed: $($process.ExitCode)" }
    $data=Join-Path $env:LOCALAPPDATA 'JaliVulkan';New-Item -ItemType Directory -Force $data | Out-Null
    'keep my private conversation data' | Set-Content (Join-Path $data 'preserve-test.txt')
    & $exe --verify-installation --diagnostics-file (Join-Path $root 'integrity.json')
    if ($LASTEXITCODE -ne 0) { throw 'Installed asset verification failed.' }
    & $exe --doctor --diagnostics-file (Join-Path $root 'doctor.json')
    if ($LASTEXITCODE -ne 0) { throw 'Clean-profile dependency doctor failed.' }
    'retired application file' | Set-Content (Join-Path $install 'application/retired-build-file.txt')
    $process=Start-Process -FilePath $setup -ArgumentList $args -PassThru -Wait
    if ($process.ExitCode -ne 0 -or -not (Test-Path (Join-Path $data 'preserve-test.txt'))) { throw 'Update/reinstall failed or erased user data.' }
    & $exe --verify-installation --diagnostics-file (Join-Path $root 'updated-integrity.json')
    if ($LASTEXITCODE -ne 0) { throw 'Updated payload failed verification (including retired-file cleanup).' }
    if (-not (Test-Path (Join-Path $root 'doctor.json'))) { throw 'Dependency doctor did not write its report.' }
    $process=Start-Process -FilePath (Join-Path $install 'unins000.exe') -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru -Wait
    if ($process.ExitCode -ne 0 -or (Test-Path $exe) -or -not (Test-Path (Join-Path $data 'preserve-test.txt'))) { throw 'Uninstall failed or erased user data.' }
    @{passed=$true;install=$true;reinstall_update_preserves_data=$true;updated_payload_verified=$true;retired_payload_file_removed=$true;uninstall_preserves_data=$true;clean_user_data=$true;signing='unsigned personal build';redistribution_approved=$false} | ConvertTo-Json | Set-Content (Join-Path $root 'result.json')
} finally { $env:LOCALAPPDATA=$previous;Pop-Location }
