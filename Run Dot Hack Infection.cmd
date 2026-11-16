@echo off
if not exist "%~dp0DotHackInfection.exe" (
  echo Build the launcher first: python scripts\project.py build-launcher
  pause
  exit /b 1
)
start "" "%~dp0DotHackInfection.exe"
