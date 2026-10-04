@echo off
call "D:\Serveur IA\toolchain\msvc\setup_x64.bat"
cd /d "D:\Serveur IA\cafe-build-p100"
link.exe /nologo @"D:\Serveur IA\cafe-build-p100-hybride\link.rsp" /out:"D:\Serveur IA\cafe-build-p100-hybride\bin\ggml-cuda.dll" /implib:"D:\Serveur IA\cafe-build-p100-hybride\ggml-cuda.lib" /pdb:"D:\Serveur IA\cafe-build-p100-hybride\ggml-cuda.pdb" /dll /version:0.25 /machine:x64 /INCREMENTAL:NO -LIBPATH:"D:\Serveur IA\toolchain\cuda-12.4\lib\x64"
exit /b %errorlevel%
