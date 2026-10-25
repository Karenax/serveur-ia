@echo off
setlocal
set "KIARA_ROOT=%~dp0.."
call "%KIARA_ROOT%\toolchain\msvc\setup_x64.bat"
if errorlevel 1 exit /b 1
set "VULKAN_SDK=%KIARA_ROOT%\toolchain\vulkan-sdk-1.4.363.0"
set "PATH=%KIARA_ROOT%\toolchain\ninja-1.12.1;%VULKAN_SDK%\Bin;%PATH%"
set "KIARA_CMAKE=%KIARA_ROOT%\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe"
"%KIARA_CMAKE%" -S "%KIARA_ROOT%\client-voice\max-asr" -B "%KIARA_ROOT%\toolchain\max-asr-build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DWHISPER_SOURCE_DIR="%KIARA_ROOT%\toolchain\whisper.cpp-1.9.5"
if errorlevel 1 exit /b 1
"%KIARA_CMAKE%" --build "%KIARA_ROOT%\toolchain\max-asr-build" --target kiara-asr --parallel 6
exit /b %errorlevel%
