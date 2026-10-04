@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "CUDA_PATH=D:\Serveur IA\toolchain\cuda-12.4"
set "PATH=D:\Serveur IA\toolchain\cmake-3.31.8-windows-x86_64\bin;%CUDA_PATH%\bin;C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
cmake -S "D:\Serveur IA\Strata-src" -B "D:\Serveur IA\strata-build-contribution" -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_CUDA=ON -DSTRATA_EXPERIMENTAL_SM60=ON -DCMAKE_CUDA_ARCHITECTURES=60-real -DCMAKE_CUDA_RUNTIME_LIBRARY=Shared -DCUDAToolkit_ROOT="%CUDA_PATH%" -DCMAKE_CUDA_COMPILER="%CUDA_PATH%\bin\nvcc.exe" -DSTRATA_PORTABLE=ON -DSTRATA_BUILD_TESTS=ON -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_GGML_DIR="D:\Serveur IA\toolchain\strata-llama\llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d" -DSTRATA_MMQ_KQUANTS=ON
if errorlevel 1 exit /b %errorlevel%
cmake --build "D:\Serveur IA\strata-build-contribution" --target strata prefill_p100_test native_dense_ple_key_test native_expert_parity gguf_split_test file_expert_source_test -j 10
exit /b %errorlevel%
