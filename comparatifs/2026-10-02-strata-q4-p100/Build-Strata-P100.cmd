@echo off
set "VSLANG=1033"
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "CUDA_PATH=D:\Serveur IA\toolchain\cuda-12.4"
set "PATH=%CUDA_PATH%\bin;C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
set "CMAKE_CUDA_RUNTIME_LIBRARY=Shared"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Serveur IA\Fix-Strata-Build-Dependencies.ps1"
if errorlevel 1 exit /b %errorlevel%
"D:\Serveur IA\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe" -S "D:\Serveur IA\Strata-src" -B "D:\Serveur IA\strata-build-p100" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_RUNTIME_LIBRARY=Shared -DSTRATA_ENABLE_CUDA=ON -DSTRATA_EXPERIMENTAL_SM60=ON -DCMAKE_CUDA_ARCHITECTURES=60-real -DCMAKE_CUDA_FLAGS=-allow-unsupported-compiler -DCUDAToolkit_ROOT="%CUDA_PATH%" -DSTRATA_PORTABLE=ON -DSTRATA_BUILD_TESTS=OFF -DSTRATA_GGML_DIR="D:\Serveur IA\toolchain\strata-llama\llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d" -DSTRATA_MMQ_KQUANTS=ON
if errorlevel 1 exit /b %errorlevel%
"D:\Serveur IA\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe" --build "D:\Serveur IA\strata-build-p100" --target strata strata-device native_expert_parity -j 12
exit /b %errorlevel%


