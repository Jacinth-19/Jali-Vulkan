@echo off
if not exist "%~dp0..\.venv\Scripts\python.exe" (
  echo Run windows\setup-neural.ps1 from the trusted checkout first.
  pause
  exit /b 1
)
"%~dp0..\.venv\Scripts\python.exe" "%~dp0..\tools\studio_launcher.py"
