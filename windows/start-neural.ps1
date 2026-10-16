# No downloads or installs. Bind only to this Windows machine by default.
param([ValidateRange(1024,65535)][int]$Port=8082, [switch]$NativeVulkan, [switch]$SoftwareVulkanForTesting)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$PreviousIcd = $env:VK_ICD_FILENAMES
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    if (-not (Test-Path .\.venv\Scripts\python.exe)) { throw 'Run windows/setup-neural.ps1 first.' }
    $Options = @()
    if ($SoftwareVulkanForTesting -and -not $NativeVulkan) { throw 'SoftwareVulkanForTesting requires NativeVulkan.' }
    if ($NativeVulkan) {
        if (-not (Test-Path build-live/jali_rich.exe) -or -not (Test-Path artifacts/native-head/mpfb-native.glb)) { throw 'Run windows/setup-native.ps1 first.' }
        $Options += @('--native-asset','artifacts/native-head/mpfb-native.glb')
        if ($SoftwareVulkanForTesting) {
            if (-not (Test-Path .cache/runtime/windows-swiftshader.json)) { throw 'Run windows/setup-native.ps1 -SoftwareForTesting first. No hardware fallback was attempted.' }
            $env:VK_ICD_FILENAMES = (Resolve-Path .cache/runtime/windows-swiftshader.json).Path
            Write-Host 'Explicit Chrome SwiftShader SOFTWARE Vulkan: not hardware-GPU acceptance.'
        }
    }
    Write-Host "After the server starts, open http://localhost:$Port in Edge or Chrome. Ctrl+C stops it."
    & .\.venv\Scripts\python.exe tools/neural_studio_server.py --bind 127.0.0.1 --port $Port @Options
    if ($LASTEXITCODE -ne 0) { throw 'Studio failed; check setup, asset hashes and port availability.' }
} finally { $env:VK_ICD_FILENAMES = $PreviousIcd; Pop-Location }
