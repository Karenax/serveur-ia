$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$pidPath = Join-Path $root 'strata-iq4-server.pid'
if (!(Test-Path -LiteralPath $pidPath)) { return }
$serverPid = [int](Get-Content -LiteralPath $pidPath)
$process = Get-CimInstance Win32_Process -Filter "ProcessId=$serverPid" -ErrorAction SilentlyContinue
if (!$process) { return }
if ($process.CommandLine -notlike '*serve.server*' -or
    ($process.CommandLine -notlike '*configuration-iq4.json*' -and
     $process.CommandLine -notlike '*strata-iq4-p100-hybride.json*')) {
    throw 'Le PID ne correspond pas au serveur IQ4 attendu.'
}
$health = $null
try { $health = Invoke-RestMethod 'http://127.0.0.1:8080/health' -TimeoutSec 3 } catch {}
if ($health -and $health.model -eq 'qwen3.8-flash-next-iq4-xs') {
    $unloaded = Invoke-RestMethod 'http://127.0.0.1:8080/unload' -Method Post -ContentType 'application/json' -Body '{}' -TimeoutSec 60
    if ($unloaded.status -eq 'busy') { throw 'Une réponse IQ4 est encore en cours. Attendre sa fin avant de stopper.' }
}
$owned = @($process)
for ($level = 0; $level -lt 3; $level++) {
    $parents = @($owned | ForEach-Object ProcessId)
    $children = @(Get-CimInstance Win32_Process | Where-Object {
        $_.ParentProcessId -in $parents -and $_.ProcessId -notin $parents
    })
    if (!$children.Count) { break }
    $owned += $children
}
for ($i = $owned.Count - 1; $i -ge 0; $i--) {
    Stop-Process -Id $owned[$i].ProcessId -ErrorAction SilentlyContinue
}
Write-Output 'Serveur IQ4 arrêté.'
