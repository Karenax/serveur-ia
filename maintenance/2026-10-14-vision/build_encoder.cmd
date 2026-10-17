@echo off
setlocal
for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
call "%PROJECT_ROOT%\toolchain\Build-Environment.cmd"
set "VSLANG=1033"
"%PROJECT_ROOT%\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe" -S "%PROJECT_ROOT%\dependances\strata-0.1.43.1\source\tools\vision" -B "%PROJECT_ROOT%\toolchain\vision-trial-20261014\build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTRATA_VISION_CUDA=ON -DSTRATA_PORTABLE=ON -DCMAKE_CUDA_ARCHITECTURES=61-real -DCMAKE_CUDA_RUNTIME_LIBRARY=Shared -DCMAKE_CUDA_FLAGS=-allow-unsupported-compiler -DCUDAToolkit_ROOT="%PROJECT_ROOT%\toolchain\cuda-12.4" -DCMAKE_CUDA_COMPILER="%PROJECT_ROOT%\toolchain\cuda-12.4\bin\nvcc.exe" -DLLAMA_DIR="%PROJECT_ROOT%\toolchain\strata-llama\llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d"
if errorlevel 1 exit /b %errorlevel%
"%PROJECT_ROOT%\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe" --build "%PROJECT_ROOT%\toolchain\vision-trial-20261014\build" --target strata-vision -j 6
exit /b %errorlevel%
