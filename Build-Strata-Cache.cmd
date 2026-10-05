@echo off
call "D:\Serveur IA\toolchain\msvc\setup_x64.bat"
"D:\Serveur IA\Strata-src\.venv\Scripts\python.exe" "D:\Serveur IA\Construire-Cache-Strata.py"
exit /b %errorlevel%
