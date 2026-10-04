param([switch]$CacheContigu, [ValidateSet(8,16)][int]$CpuCores = 16)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Le port 8080 est occupé.'
}
$pwsh = (Get-Process -Id $PID).Path
$script = Join-Path $root 'Start-Strata-P100.ps1'
$command = '"'+$pwsh+'" -NoProfile -ExecutionPolicy Bypass -File "'+$script+'" -CpuCores '+$CpuCores
if ($CacheContigu) { $command += ' -CacheContigu' }
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$command;CurrentDirectory=$root;ProcessStartupInformation=$startup}
if ($result.ReturnValue -ne 0) { throw "Windows ne lance pas le serveur (code $($result.ReturnValue))." }
Write-Output "Lancement caché demandé (PID $($result.ProcessId)). Le chargement continue indépendamment du terminal de lancement."
