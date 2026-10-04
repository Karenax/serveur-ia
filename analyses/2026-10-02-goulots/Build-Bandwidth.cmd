@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "CUDA_PATH=D:\Serveur IA\toolchain\cuda-12.4"
set "PATH=%CUDA_PATH%\bin;%PATH%"
cl.exe /nologo /O2 /arch:AVX2 /openmp /EHsc /std:c++20 /I"%CUDA_PATH%\include" "D:\Serveur IA\analyses\2026-10-02-goulots\bandwidth.cpp" /Fo"D:\Serveur IA\analyses\2026-10-02-goulots\bandwidth.obj" /Fe"D:\Serveur IA\analyses\2026-10-02-goulots\bandwidth.exe" /link /LIBPATH:"%CUDA_PATH%\lib\x64" cudart.lib
exit /b %errorlevel%
