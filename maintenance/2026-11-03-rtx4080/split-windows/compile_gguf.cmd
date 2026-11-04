@echo off
call "D:\Serveur IA\toolchain\msvc\setup_x64.bat"
cl /nologo /EHsc /std:c++17 /O2 /DFNX_27B=0 /D_CRT_SECURE_NO_WARNINGS /I"D:\Serveur IA\toolchain\strata-0156-source\src\split\src" "D:\Serveur IA\toolchain\strata-0156-source\src\split\src\gguf.cpp" "D:\Serveur IA\maintenance\2026-11-03-rtx4080\split-windows\gguf_smoke.cpp" /Fe:gguf-smoke.exe > gguf-build.log 2>&1
exit /b %ERRORLEVEL%
