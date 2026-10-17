# Run after setup-neural.ps1. No downloads, installs, private text, or uploads.
param(
    [ValidateRange(1,3)][int]$Repeats=2,
    [ValidateSet('chrome','msedge')][string]$Browser='chrome',
    [ValidateLength(0,2000)][string]$Conditions='',
    [string]$Assets='',
    [switch]$Headless
)
$ErrorActionPreference='Stop'
$env:PYTHONUTF8='1'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    if (-not (Test-Path .\.venv\Scripts\python.exe)) { throw 'Run windows/setup-neural.ps1 first.' }
    Write-Host 'Keep the benchmark browser visible. Do not seek, resize, or switch tabs. Nothing uploads automatically.'
    $arguments=@('tools/benchmark_neural.py','--repeats',"$Repeats",'--browser',$Browser)
    if ($Conditions) { $arguments+=@('--conditions',$Conditions) }
    if ($Assets) { $arguments+=@('--assets',$Assets) }
    if ($Headless) { $arguments+='--headless' }
    & .\.venv\Scripts\python.exe @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Benchmark incomplete. See artifacts/jali-benchmark-report.json and the local run logs.' }
    Write-Host 'Inspect artifacts/jali-benchmark-report.json before sharing it.'
} finally { Pop-Location }
