param(
    [ValidateSet('Debug', 'Release')][string]$Configuration = 'Release',
    [string]$Python,
    [string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
. (Join-Path $projectRoot 'client-qwen\android-outils\Environnement-Android.ps1')
. (Join-Path $PSScriptRoot 'scripts\Resolve-Python.ps1')
$pythonExecutable = Resolve-FredPython -Requested $Python -ProjectRoot $projectRoot
$gradle = Join-Path $projectRoot 'toolchain\gradle-8.13\bin\gradle.bat'
$apksigner = Join-Path $env:ANDROID_HOME 'build-tools\36.0.0\apksigner.bat'
foreach ($tool in @($gradle, $apksigner)) {
    if (!(Test-Path -LiteralPath $tool -PathType Leaf)) { throw "Outil absent : $tool" }
}

& (Join-Path $PSScriptRoot 'scripts\Build-WireGuard-Android.ps1')
& (Join-Path $PSScriptRoot 'scripts\Build-Voice-Android.ps1')
& $pythonExecutable (Join-Path $PSScriptRoot 'scripts\Prepare-Assets.py')
if ($LASTEXITCODE -ne 0) { throw 'Preparation des fichiers mobiles impossible.' }
& $pythonExecutable (Join-Path $PSScriptRoot 'scripts\Prepare-Assets.py') --check
if ($LASTEXITCODE -ne 0) { throw 'Verification des fichiers mobiles impossible.' }
& $pythonExecutable (Join-Path $PSScriptRoot 'scripts\Prepare-Licenses.py')
if ($LASTEXITCODE -ne 0) { throw 'Preparation des licences Android impossible.' }
& $pythonExecutable (Join-Path $PSScriptRoot 'scripts\Prepare-Licenses.py') --check
if ($LASTEXITCODE -ne 0) { throw 'Verification des licences Android impossible.' }
& $pythonExecutable -m unittest discover -s (Join-Path $PSScriptRoot 'tests') -p 'test_*.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Tests de livraison Android en echec.' }

Push-Location $PSScriptRoot
try {
    & $gradle --no-daemon --console=plain ("assemble" + $Configuration)
    if ($LASTEXITCODE -ne 0) { throw 'Compilation Android en echec.' }
} finally {
    Pop-Location
}
if ($Configuration -eq 'Release') {
    . (Join-Path $PSScriptRoot 'scripts\Sign-Android.ps1')
    $unsigned = Join-Path $PSScriptRoot 'app\build\outputs\apk\release\app-release-unsigned.apk'
    $aligned = Join-Path $PSScriptRoot 'app\build\outputs\apk\release\app-release-aligned.apk'
    $compiled = Join-Path $PSScriptRoot 'app\build\outputs\apk\release\app-release-signed.apk'
    Invoke-FredAndroidSigning -ProjectRoot $projectRoot -PythonExecutable $pythonExecutable -UnsignedApk $unsigned -AlignedApk $aligned -SignedApk $compiled
} else {
    $compiled = Join-Path $PSScriptRoot 'app\build\outputs\apk\debug\app-debug.apk'
}
if (!(Test-Path -LiteralPath $compiled -PathType Leaf)) { throw 'APK compile introuvable.' }
& $apksigner verify --verbose $compiled
if ($LASTEXITCODE -ne 0) { throw 'Signature APK invalide.' }

# Les profils personnels sont importes ensuite : jamais dans le paquet Android.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($compiled)
try {
    foreach ($requiredLicense in @('assets/third-party/manifest.json', 'assets/third-party/application/LICENSE.txt', 'assets/third-party/go/LICENSE', 'assets/third-party/markdown-it/LICENSE.txt', 'assets/voice/model.json', 'assets/third-party/whisper/whisper.cpp-LICENSE.txt', 'assets/third-party/whisper/whisper-model-LICENSE.txt', 'lib/arm64-v8a/libfredvoice.so', 'lib/x86_64/libfredvoice.so')) {
        if (!$archive.GetEntry($requiredLicense)) { throw 'Le paquet Android ne contient pas ses licences.' }
    }
    foreach ($entry in $archive.Entries) {
        if ($entry.FullName -match '(?i)(\.fred-android|\.dpapi)$|(^|/)profil\.json$') {
            throw 'Le paquet contient un fichier personnel interdit.'
        }
    }
} finally { $archive.Dispose() }
$distribution = if ($OutputDirectory) { [System.IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $PSScriptRoot 'dist' }
New-Item -ItemType Directory -Force -Path $distribution | Out-Null
$name = if ($Configuration -eq 'Release') { 'Acces-serveur-Fred-Android.apk' } else { 'Acces-serveur-Fred-Android-debug.apk' }
$apk = Join-Path $distribution $name
Copy-Item -LiteralPath $compiled -Destination $apk -Force
$digest = (Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText($apk + '.sha256', $digest + '  ' + $name + [Environment]::NewLine, [System.Text.Encoding]::ASCII)
Write-Host "APK pret : $apk"
Write-Host "SHA-256 : $digest"
if ($Configuration -eq 'Release') {
    Write-Host 'Signature locale privee. Conserver toolchain\android-signing pour les mises a jour.'
} else {
    Write-Host 'Signature debug uniquement. Ce paquet est destine au developpement.'
}
