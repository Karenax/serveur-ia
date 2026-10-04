@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "CUDA_PATH=D:\Serveur IA\toolchain\cuda-12.4"
set "PATH=%CUDA_PATH%\bin;C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
"D:\Serveur IA\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe" -S "D:\Serveur IA\Strata-src" -B "D:\Serveur IA\strata-build-p100" -DSTRATA_BUILD_TESTS=ON
if errorlevel 1 exit /b %errorlevel%
"D:\Serveur IA\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe" --build "D:\Serveur IA\strata-build-p100" --target prefill_p100_test prefill_mmq_kquant_test -j 8
exit /b %errorlevel%
