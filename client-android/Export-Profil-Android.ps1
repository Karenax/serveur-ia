param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [Parameter(Mandatory = $true)][string]$DossierSortie,
    [string]$Python
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot 'scripts\Resolve-Python.ps1')
$pythonExecutable = Resolve-FredPython -Requested $Python -ProjectRoot $projectRoot
& $pythonExecutable (Join-Path $PSScriptRoot 'scripts\Export-Profile.py') --exe $Exe --output-directory $DossierSortie
if ($LASTEXITCODE -ne 0) { throw 'Export du profil Android impossible.' }
