@echo off
call "D:\Serveur IA\toolchain\msvc\setup_x64.bat"
"D:\Serveur IA\toolchain\cuda-12.4\bin\nvcc.exe" -allow-unsupported-compiler -arch=sm_60 -c "D:\Serveur IA\maintenance\2026-11-03-rtx4080\split-windows\upstream_mma_probe.cu" -o "D:\Serveur IA\maintenance\2026-11-03-rtx4080\split-windows\mma-sm60.obj" > "D:\Serveur IA\maintenance\2026-11-03-rtx4080\split-windows\mma-sm60.log" 2>&1
set PASCAL_RESULT=%ERRORLEVEL%
"D:\Serveur IA\toolchain\cuda-12.4\bin\nvcc.exe" -allow-unsupported-compiler -arch=sm_89 -c "D:\Serveur IA\maintenance\2026-11-03-rtx4080\split-windows\upstream_mma_probe.cu" -o "D:\Serveur IA\maintenance\2026-11-03-rtx4080\split-windows\mma-sm89.obj" > "D:\Serveur IA\maintenance\2026-11-03-rtx4080\split-windows\mma-sm89.log" 2>&1
echo Pascal=%PASCAL_RESULT% Ada=%ERRORLEVEL%
