param()
$ErrorActionPreference = 'Stop'
$voiceProject = Split-Path $PSScriptRoot -Parent
$voiceRoot = Split-Path $voiceProject -Parent
. (Join-Path $voiceRoot 'client-qwen\android-outils\Environnement-Android.ps1')
$voiceCmake = Join-Path $voiceRoot 'toolchain\cmake-3.31.8-windows-x86_64\bin\cmake.exe'
$voiceNinja = Join-Path $voiceRoot 'toolchain\ninja-1.12.1\ninja.exe'
$voiceNdk = Join-Path $env:ANDROID_HOME 'ndk\27.3.13750724'
foreach ($voiceAbi in @('arm64-v8a', 'x86_64')) {
    $voiceBuild = Join-Path $voiceRoot ('toolchain\voice-build-android-' + $voiceAbi)
    & $voiceCmake -S (Join-Path $voiceRoot 'client-voice') -B $voiceBuild -G Ninja "-DCMAKE_MAKE_PROGRAM=$voiceNinja" "-DCMAKE_TOOLCHAIN_FILE=$voiceNdk\build\cmake\android.toolchain.cmake" "-DANDROID_ABI=$voiceAbi" '-DANDROID_PLATFORM=android-26' '-DANDROID_STL=c++_static' '-DCMAKE_BUILD_TYPE=Release' "-DWHISPER_SOURCE_DIR=$voiceRoot\toolchain\whisper.cpp-1.9.5"
    if ($LASTEXITCODE -ne 0) { throw ('Configuration voix impossible : ' + $voiceAbi) }
    & $voiceCmake --build $voiceBuild --parallel 4
    if ($LASTEXITCODE -ne 0) { throw ('Compilation voix impossible : ' + $voiceAbi) }
    $voiceTarget = Join-Path $voiceProject ('app\src\main\jniLibs\' + $voiceAbi)
    New-Item -ItemType Directory -Force -Path $voiceTarget | Out-Null
    Copy-Item -LiteralPath (Join-Path $voiceBuild 'libfredvoice.so') -Destination (Join-Path $voiceTarget 'libfredvoice.so') -Force
    Get-ChildItem -LiteralPath $voiceBuild -Recurse -File -Filter '*.so' | ForEach-Object {
        if ($_.Name -match '^lib(ggml|whisper|parakeet).*\.so$') { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $voiceTarget $_.Name) -Force }
    }
    $voiceStrip = Join-Path $voiceNdk 'toolchains\llvm\prebuilt\windows-x86_64\bin\llvm-strip.exe'
    Get-ChildItem -LiteralPath $voiceTarget -File -Filter '*.so' | Where-Object { $_.Name -ne 'libfredwireguard.so' } | ForEach-Object {
        & $voiceStrip --strip-debug $_.FullName
        if ($LASTEXITCODE -ne 0) { throw 'Nettoyage des symboles vocaux impossible.' }
    }
}
$voiceAssets = Join-Path $voiceProject 'app\src\main\assets\voice'
New-Item -ItemType Directory -Force -Path $voiceAssets | Out-Null
Copy-Item -LiteralPath (Join-Path $voiceRoot 'client-voice\model.json') -Destination (Join-Path $voiceAssets 'model.json') -Force
