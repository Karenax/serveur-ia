param()
. (Join-Path $PSScriptRoot 'Environnement-Android.ps1')
foreach ($controle in @(
    @{Nom='Java'; Exe='java.exe'; Arguments=@('-version')},
    @{Nom='Gradle'; Exe='gradle.bat'; Arguments=@('--version')},
    @{Nom='SDK installes'; Exe='sdkmanager.bat'; Arguments=@("--sdk_root=$env:ANDROID_HOME", '--list_installed')},
    @{Nom='ADB'; Exe='adb.exe'; Arguments=@('version')},
    @{Nom='Profils telephone/tablette'; Exe='emulator.exe'; Arguments=@('-list-avds')}
)) {
    Write-Host "`n$($controle.Nom)"
    $argumentsControle = $controle.Arguments
    & $controle.Exe @argumentsControle
    if ($LASTEXITCODE -ne 0) { throw "Verification echouee : $($controle.Nom)" }
}
Write-Host "`nAcceleration de l'emulateur (un code non nul n'empeche pas la compilation)"
& (Join-Path $env:ANDROID_HOME 'emulator\emulator-check.exe') accel
if ($LASTEXITCODE -ne 0) {
    Write-Warning 'Acceleration materielle indisponible. Activer Plateforme de l''hyperviseur Windows comme administrateur, puis redemarrer Windows.'
}
