param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
. (Join-Path $projectRoot 'client-qwen\android-outils\Environnement-Android.ps1')
. (Join-Path $projectRoot 'client-android\scripts\Resolve-Python.ps1')
. (Join-Path $projectRoot 'client-android\scripts\Sign-Android.ps1')
$fixturePython = Resolve-FredPython -ProjectRoot $projectRoot
$fixtureRoot = Join-Path $projectRoot 'toolchain\android-tests\update-future-project'
$fixtureDist = Join-Path $projectRoot 'toolchain\android-tests\update-future-dist'
$fixtureInstrumentation = Join-Path $projectRoot 'toolchain\android-tests\update-release-instrumentation'
New-Item -ItemType Directory -Force -Path $fixtureRoot,$fixtureDist,$fixtureInstrumentation | Out-Null
@'
from pathlib import Path
import shutil, sys, re
root=Path(sys.argv[1]); source=root/'client-android'; target=root/'toolchain/android-tests/update-future-project'
for name in ('settings.gradle','build.gradle','gradle.properties'):
    shutil.copy2(source/name,target/name)
shutil.copytree(source/'app/src/main',target/'app/src/main',dirs_exist_ok=True)
shutil.copytree(source/'app/src/release',target/'app/src/release',dirs_exist_ok=True)
gradle=(source/'app/build.gradle').read_text(encoding='utf-8')
code=int(re.search(r'versionCode\s+(\d+)',gradle).group(1))
version=re.search(r"versionName\s+'([^']+)'",gradle).group(1)
parts=[int(value) for value in version.split('.')];parts[-1]+=1
future='.'.join(map(str,parts))
gradle=re.sub(r'versionCode\s+\d+',f'versionCode {code+1}',gradle,count=1)
gradle=re.sub(r"versionName\s+'[^']+'",f"versionName '{future}'",gradle,count=1)
(target/'app/build.gradle').write_text(gradle,encoding='utf-8')
'@ | & $fixturePython - $projectRoot
if ($LASTEXITCODE -ne 0) { throw 'Preparation fixture impossible.' }
& (Join-Path $projectRoot 'toolchain\gradle-8.13\bin\gradle.bat') -p $fixtureRoot --no-daemon --console=plain assembleRelease
if ($LASTEXITCODE -ne 0) { throw 'Compilation fixture impossible.' }
Invoke-FredAndroidSigning -ProjectRoot $projectRoot -PythonExecutable $fixturePython `
    -UnsignedApk (Join-Path $fixtureRoot 'app\build\outputs\apk\release\app-release-unsigned.apk') `
    -AlignedApk (Join-Path $fixtureDist 'aligned.apk') -SignedApk (Join-Path $fixtureDist 'Acces-serveur-Fred-Android.apk')
$fixtureApk = Join-Path $fixtureDist 'Acces-serveur-Fred-Android.apk'
$fixtureGradle = Get-Content -LiteralPath (Join-Path $fixtureRoot 'app\build.gradle') -Raw
$fixtureVersion = [regex]::Match($fixtureGradle, "versionName\s+'([^']+)'").Groups[1].Value
$fixtureCode = [int][regex]::Match($fixtureGradle, 'versionCode\s+(\d+)').Groups[1].Value
$manifest = @{package='net.karenax.fred';version=$fixtureVersion;version_code=$fixtureCode;bytes=(Get-Item -LiteralPath $fixtureApk).Length;sha256=(Get-FileHash -LiteralPath $fixtureApk).Hash.ToLowerInvariant()}
[System.IO.File]::WriteAllText((Join-Path $fixtureDist 'release.json'),($manifest|ConvertTo-Json),[System.Text.UTF8Encoding]::new($false))
# Reuse the test DEX with a manifest targeting the signed Release application.
$testManifest = '<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="net.karenax.fred.updatetest"><uses-sdk android:minSdkVersion="26" android:targetSdkVersion="36"/><application android:label="Fred update fixture"/><instrumentation android:name="net.karenax.fred.UpdateFlowInstrumentation" android:targetPackage="net.karenax.fred"/></manifest>'
[System.IO.File]::WriteAllText((Join-Path $fixtureInstrumentation 'AndroidManifest.xml'),$testManifest,[System.Text.UTF8Encoding]::new($false))
& (Join-Path $env:ANDROID_HOME 'build-tools\36.0.0\aapt2.exe') link -I (Join-Path $env:ANDROID_HOME 'platforms\android-36\android.jar') --manifest (Join-Path $fixtureInstrumentation 'AndroidManifest.xml') -o (Join-Path $fixtureInstrumentation 'unsigned.apk')
if ($LASTEXITCODE -ne 0) { throw 'Manifeste instrumentation impossible.' }
@'
from pathlib import Path
import zipfile, sys
root=Path(sys.argv[1])
with zipfile.ZipFile(root/'client-android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk') as source, zipfile.ZipFile(root/'toolchain/android-tests/update-release-instrumentation/unsigned.apk','a') as target:
    for name in source.namelist():
        if name.startswith('classes') and name.endswith('.dex'): target.writestr(name,source.read(name))
'@ | & $fixturePython - $projectRoot
if ($LASTEXITCODE -ne 0) { throw 'DEX instrumentation impossible.' }
Invoke-FredAndroidSigning -ProjectRoot $projectRoot -PythonExecutable $fixturePython `
    -UnsignedApk (Join-Path $fixtureInstrumentation 'unsigned.apk') `
    -AlignedApk (Join-Path $fixtureInstrumentation 'aligned.apk') -SignedApk (Join-Path $fixtureInstrumentation 'signed.apk')
Write-Host 'Fixture future signee et instrumentation Release pretes. Aucun paquet de production remplace.'
