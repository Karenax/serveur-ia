@echo off
setlocal
set "KIARA_ROOT=%~dp0.."
call "%KIARA_ROOT%\toolchain\msvc\setup_x64.bat"
if errorlevel 1 exit /b 1
set "VULKAN_SDK=%KIARA_ROOT%\toolchain\vulkan-sdk-1.4.363.0"
set "PATH=%KIARA_ROOT%\toolchain\ninja-1.12.1;%VULKAN_SDK%\Bin;%PATH%"
set "KIARA_CMAKE=%KIARA_ROOT%\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe"
"%KIARA_CMAKE%" -S "%KIARA_ROOT%\toolchain\qwentts-max-src" -B "%KIARA_ROOT%\toolchain\qwentts-max-build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DQWEN_SHARED=ON -DGGML_VULKAN=ON -DGGML_NATIVE=OFF -DGGML_AVX512=OFF -DGGML_CUDA=OFF -DGGML_BACKEND_DL=OFF -DGGML_BUILD_TESTS=OFF -DGGML_BUILD_EXAMPLES=OFF
if errorlevel 1 exit /b 1
"%KIARA_CMAKE%" --build "%KIARA_ROOT%\toolchain\qwentts-max-build" --target qwen --parallel 6
exit /b %errorlevel%
