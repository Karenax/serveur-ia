@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "CUDA_PATH=D:\Serveur IA\toolchain\cuda-12.4"
set "PATH=%CUDA_PATH%\bin;C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
"D:\Serveur IA\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe" -S "D:\Serveur IA\cafe-llama-src" -B "D:\Serveur IA\cafe-build-p100" -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=60-real -DCMAKE_CUDA_FLAGS=-allow-unsupported-compiler -DCUDAToolkit_ROOT="%CUDA_PATH%" -DGGML_NATIVE=OFF -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DGGML_CUDA_GRAPHS=OFF -DGGML_CUDA_MOE_DIRECT_GPU_ONLY=ON -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_TOOLS=ON
if errorlevel 1 exit /b %errorlevel%
"D:\Serveur IA\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe" --build "D:\Serveur IA\cafe-build-p100" --target llama-server -j 12
exit /b %errorlevel%
