#Requires -Version 7.0
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repo = (Get-Item -LiteralPath (Join-Path $PSScriptRoot '..')).FullName

function Read-VersionConstant([string]$RelativePath, [string]$Constant) {
    $content = Get-Content -LiteralPath (Join-Path $repo $RelativePath) -Raw
    $pattern = '(?m)^' + [regex]::Escape($Constant) + ' = ''([0-9]+\.[0-9]+\.[0-9]+)''\s*$'
    $match = [regex]::Match($content, $pattern)
    if (!$match.Success) { throw "Version introuvable dans $RelativePath ($Constant)." }
    return $match.Groups[1].Value
}

$registryKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Kiara'
$registration = $null
if (Test-Path -LiteralPath $registryKey) {
    $registration = Get-ItemProperty -LiteralPath $registryKey
}
$location = if ($registration.InstallLocation) { $registration.InstallLocation.Trim().Trim('"') }
$exe = if ($location -and [IO.Path]::IsPathFullyQualified($location)) {
    Join-Path $location 'Kiara.exe'
}
$installed = if ($exe -and (Test-Path -LiteralPath $exe -PathType Leaf)) {
    Get-Item -LiteralPath $exe
}

[ordered]@{
    releve_le = [DateTimeOffset]::Now.ToString('o')
    depot = $repo
    source = [ordered]@{
        canal_windows = Read-VersionConstant 'lanceur/releases.py' 'DESKTOP_INSTALLER_VERSION'
        version_partagee = Read-VersionConstant 'shared/kiara_shared/version.py' 'VERSION'
    }
    installation_windows_compte_courant = [ordered]@{
        registre_present = ($null -ne $registration)
        version_registre = $registration.DisplayVersion
        emplacement_registre = $location
        executable = $installed.FullName
        version_executable = $installed.VersionInfo.ProductVersion
    }
    cartes_detectees_par_windows = @(Get-CimInstance Win32_VideoController |
        Sort-Object Name | Select-Object Name, DriverVersion)
} | ConvertTo-Json -Depth 4
