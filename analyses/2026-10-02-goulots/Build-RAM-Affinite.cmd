@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
cl.exe /nologo /O2 /arch:AVX2 /openmp /EHsc /std:c++20 "D:\Serveur IA\analyses\2026-10-02-goulots\ram-affinite.cpp" /Fo"D:\Serveur IA\analyses\2026-10-02-goulots\ram-affinite.obj" /Fe"D:\Serveur IA\analyses\2026-10-02-goulots\ram-affinite.exe"
exit /b %errorlevel%
