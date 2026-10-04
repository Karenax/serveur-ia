@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "CUDA_PATH=D:\Serveur IA\toolchain\cuda-12.4"
set "PATH=%CUDA_PATH%\bin;%PATH%"
nvcc.exe -O3 -arch=sm_60 -allow-unsupported-compiler -cudart shared "D:\Serveur IA\analyses\2026-10-02-goulots\kernel-copy.cu" -o "D:\Serveur IA\analyses\2026-10-02-goulots\kernel-copy.exe"
exit /b %errorlevel%
