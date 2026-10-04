@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Interface-Qwen.ps1"
if errorlevel 1 pause
