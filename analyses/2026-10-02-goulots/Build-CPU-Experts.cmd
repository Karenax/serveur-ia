@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "GGML=D:\Serveur IA\toolchain\strata-llama\llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d\ggml"
cl.exe /nologo /MT /O2 /arch:AVX2 /openmp /EHsc /std:c++20 /I"D:\Serveur IA\Strata-src\include" /I"%GGML%\include" "D:\Serveur IA\analyses\2026-10-02-goulots\cpu-experts.cpp" /Fo"D:\Serveur IA\analyses\2026-10-02-goulots\cpu-experts.obj" /Fe"D:\Serveur IA\analyses\2026-10-02-goulots\cpu-experts.exe" /link "D:\Serveur IA\strata-build-p100\strata_kernels_cpu.lib" "D:\Serveur IA\strata-build-p100\ggml\src\ggml-cpu.lib" "D:\Serveur IA\strata-build-p100\ggml\src\ggml-base.lib" advapi32.lib
exit /b %errorlevel%
