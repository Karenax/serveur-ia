@echo off
setlocal
call "D:\Serveur IA\toolchain\Build-Environment.cmd"
set "TEMP=D:\Temp\strata-recherche"
set "TMP=%TEMP%"
set "VSLANG=1033"
"D:\Serveur IA\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe" -S "D:\Serveur IA\recherche\strata-0.1.39-20261004-185410\source-adaptee" -B "D:\Serveur IA\recherche\strata-0.1.39-20261004-185410\build-adapte" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_RUNTIME_LIBRARY=Shared -DSTRATA_ENABLE_CUDA=ON -DSTRATA_EXPERIMENTAL_SM60=ON -DCMAKE_CUDA_ARCHITECTURES=60-real -DCMAKE_CUDA_FLAGS=-allow-unsupported-compiler -DCUDAToolkit_ROOT="D:\Serveur IA\toolchain\cuda-12.4" -DCMAKE_CUDA_COMPILER="D:\Serveur IA\toolchain\cuda-12.4\bin\nvcc.exe" -DSTRATA_PORTABLE=ON -DSTRATA_BUILD_TESTS=ON -DSTRATA_GGML_DIR="D:\Serveur IA\toolchain\strata-llama\llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d" -DSTRATA_MMQ_KQUANTS=ON
if errorlevel 1 exit /b %errorlevel%
"D:\Serveur IA\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe" --build "D:\Serveur IA\recherche\strata-0.1.39-20261004-185410\build-adapte" --target strata strata-device native_expert_parity prefill_p100_test -j 10
exit /b %errorlevel%

