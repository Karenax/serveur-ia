param(
    [ValidateSet('telephone', 'tablette')]
    [string]$Appareil = 'telephone',
    [switch]$SansAcceleration
)
. (Join-Path $PSScriptRoot 'Environnement-Android.ps1')
$profil = if ($Appareil -eq 'telephone') { 'Fred_Telephone_API36' } else { 'Fred_Tablette_API36' }
$argumentsEmulateur = @('-avd', $profil)
if ($SansAcceleration) { $argumentsEmulateur += @('-accel', 'off') }
& (Join-Path $env:ANDROID_HOME 'emulator\emulator.exe') @argumentsEmulateur
if ($LASTEXITCODE -ne 0) { throw "L'emulateur Android n'a pas demarre." }
