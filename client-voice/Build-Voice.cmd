@echo off
setlocal
set "FRED_ROOT=%~dp0.."
call "%FRED_ROOT%\toolchain\msvc\setup_x64.bat"
if errorlevel 1 exit /b 1
set "FRED_CMAKE=%FRED_ROOT%\toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe"
set "PATH=%FRED_ROOT%\toolchain\ninja-1.12.1;%PATH%"
"%FRED_CMAKE%" -S "%~dp0." -B "%FRED_ROOT%\toolchain\voice-build-windows" -G Ninja -DCMAKE_BUILD_TYPE=Release -DWHISPER_SOURCE_DIR="%FRED_ROOT%\toolchain\whisper.cpp-1.9.5"
if errorlevel 1 exit /b 1
"%FRED_CMAKE%" --build "%FRED_ROOT%\toolchain\voice-build-windows" --parallel 4
exit /b %errorlevel%
