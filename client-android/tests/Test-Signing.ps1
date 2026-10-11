param([string]$Apk, [string]$Python)
$ErrorActionPreference = 'Stop'
$androidRoot = Split-Path $PSScriptRoot -Parent
$projectRoot = Split-Path $androidRoot -Parent
. (Join-Path $projectRoot 'client-qwen\android-outils\Environnement-Android.ps1')
. (Join-Path $androidRoot 'scripts\Resolve-Python.ps1')
. (Join-Path $androidRoot 'scripts\Sign-Android.ps1')
$pythonExecutable = Resolve-FredPython -Requested $Python -ProjectRoot $projectRoot
if (!$Apk) { $Apk = Join-Path $projectRoot 'toolchain\android-smoke\app\build\outputs\apk\debug\app-debug.apk' }
$temporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$probeDirectory = Join-Path $temporaryRoot ('FredAndroidSigningTest-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $probeDirectory | Out-Null
try {
    $signingDirectory = Join-Path $probeDirectory 'private-keys'
    $aligned = Join-Path $probeDirectory 'aligned.apk'
    $signed = Join-Path $probeDirectory 'signed.apk'
    $beforeEnvironment = [Environment]::GetEnvironmentVariable('FRED_ANDROID_SIGN_PASSWORD', 'Process')
    Invoke-FredAndroidSigning -ProjectRoot $projectRoot -PythonExecutable $pythonExecutable -UnsignedApk $Apk -AlignedApk $aligned -SignedApk $signed -SigningDirectory $signingDirectory
    $keyHash = (Get-FileHash -LiteralPath (Join-Path $signingDirectory 'fred-client.p12') -Algorithm SHA256).Hash
    $passwordHash = (Get-FileHash -LiteralPath (Join-Path $signingDirectory 'password.dpapi') -Algorithm SHA256).Hash
    Invoke-FredAndroidSigning -ProjectRoot $projectRoot -PythonExecutable $pythonExecutable -UnsignedApk $Apk -AlignedApk $aligned -SignedApk $signed -SigningDirectory $signingDirectory
    if ((Get-FileHash -LiteralPath (Join-Path $signingDirectory 'fred-client.p12') -Algorithm SHA256).Hash -ne $keyHash) { throw 'La cle de signature a ete remplacee.' }
    if ((Get-FileHash -LiteralPath (Join-Path $signingDirectory 'password.dpapi') -Algorithm SHA256).Hash -ne $passwordHash) { throw 'Le secret DPAPI a ete remplace.' }
    if ([Environment]::GetEnvironmentVariable('FRED_ANDROID_SIGN_PASSWORD', 'Process') -ne $beforeEnvironment) { throw 'Le secret est reste dans l environnement.' }
    Write-Host 'Signature locale, verification, ACL et reutilisation de la cle : OK.'
} finally {
    # Delete only the exact isolated test directory created above.
    $resolvedProbe = (Resolve-Path -LiteralPath $probeDirectory).Path
    $expectedProbe = [System.IO.Path]::GetFullPath($probeDirectory)
    if ($resolvedProbe -ne $expectedProbe -or !$resolvedProbe.StartsWith($temporaryRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Chemin de nettoyage du test invalide.'
    }
    Remove-Item -LiteralPath $resolvedProbe -Recurse -Force
}
