param()
$ErrorActionPreference = 'Stop'
$racineProjet = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$outils = Join-Path $racineProjet 'toolchain'
$env:ANDROID_HOME = Join-Path $outils 'android-sdk'
$env:ANDROID_USER_HOME = Join-Path $outils 'android-user'
$env:ANDROID_AVD_HOME = Join-Path $outils 'android-avd'
$env:GRADLE_USER_HOME = Join-Path $outils 'android-gradle-cache'
# Android Studio utilise son JBR 25 ; Gradle 8.13 utilise le JDK 21 distinct.
$jdk = Get-ChildItem (Join-Path $outils 'android-jdk') -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName 'bin\java.exe') } | Select-Object -First 1
if (!$jdk) { throw 'JDK Android absent dans toolchain.' }
$env:JAVA_HOME = $jdk.FullName
$env:Path = (@(
    (Join-Path $env:JAVA_HOME 'bin'),
    (Join-Path $env:ANDROID_HOME 'platform-tools'),
    (Join-Path $env:ANDROID_HOME 'cmdline-tools\latest\bin'),
    (Join-Path $env:ANDROID_HOME 'emulator'),
    (Join-Path $outils 'gradle-8.13\bin'),
    $env:Path
) -join ';')
foreach ($dossier in @($env:ANDROID_USER_HOME, $env:ANDROID_AVD_HOME, $env:GRADLE_USER_HOME)) {
    New-Item -ItemType Directory -Force -Path $dossier | Out-Null
}
$env:STUDIO_PROPERTIES = Join-Path $outils 'android-studio.properties'
