$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$processes = @(Get-CimInstance Win32_Process)
$servers = @($processes | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*serve.server*' -and $_.CommandLine -like '*strata-iq3-p100-hybride.json*' })
$ids = @($servers | ForEach-Object ProcessId)
foreach ($level in 1..3) {
    $ids += @($processes | Where-Object { $_.ParentProcessId -in $ids -and $_.ProcessId -notin $ids } | ForEach-Object ProcessId)
}
$testers = @($processes | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*Tester-Strata-IQ3.py*' })
foreach ($p in $testers) { Stop-Process -Id $p.ProcessId -ErrorAction SilentlyContinue }
foreach ($id in ($ids | Select-Object -Unique)) { Stop-Process -Id $id -ErrorAction SilentlyContinue }
Write-Output 'Serveur IQ3_S arrêté.'
