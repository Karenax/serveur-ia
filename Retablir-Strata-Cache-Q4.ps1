$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$archive = (Get-Content -LiteralPath (Join-Path $root 'comparatif-cpu8-courant.txt') -Raw).Trim()
$statePath = Join-Path $archive 'etat-retablissement-ssd.json'
$python = Join-Path $root 'Strata-src\.venv\Scripts\python.exe'
function Save-Phase([string]$phase) {
    @{status=$phase;time=(Get-Date -Format o);launcher_pid=$PID} | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
}
try {
    Save-Phase 'waiting-for-cache'
    $deadline = (Get-Date).AddHours(2)
    while ((Get-Date) -lt $deadline) {
        $state = Get-Content -LiteralPath (Join-Path $archive 'etat-cache-ssd.json') -Raw | ConvertFrom-Json
        if ($state.status -eq 'failed') { throw $state.error }
        if ($state.status -eq 'complete') { break }
        Start-Sleep -Seconds 3
    }
    if ($state.status -ne 'complete') { throw 'La préparation SSD dépasse le délai prévu.' }
    Save-Phase 'starting-server'
    & (Join-Path $root 'Start-Strata-P100.ps1') -CacheContigu -CpuCores 8
    $serverPid = [int](Get-Content -LiteralPath (Join-Path $root 'strata-server.pid'))
    $deadline = (Get-Date).AddMinutes(90)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        if (!(Get-Process -Id $serverPid -ErrorAction SilentlyContinue)) { throw 'Le serveur restauré est arrêté.' }
        $health = $null
        try { $health = Invoke-RestMethod 'http://127.0.0.1:8080/health' -TimeoutSec 3 } catch {}
        $affinity = $null
        $affinityPath = Join-Path $root 'strata-affinite-8coeurs.json'
        if (Test-Path -LiteralPath $affinityPath) {
            try { $affinity = Get-Content -LiteralPath $affinityPath -Raw | ConvertFrom-Json } catch {}
        }
        $engines = @(Get-CimInstance Win32_Process -Filter "Name='strata.exe'" | Where-Object {
            $_.ExecutablePath -eq (Join-Path $root 'strata-build-p100\strata.exe') -and
            $_.CommandLine -like '*q4-experts-contigus*' -and $_.CommandLine -match '--pool-workers 7(?: |$)'
        })
        if ($health.loaded -and !(Test-Path -LiteralPath (Join-Path $root 'strata-data\cuda-debug.flag')) -and
            $engines.Count -eq 1 -and $affinity.pid -eq $engines[0].ProcessId -and $affinity.process_mask_after -eq 16711935) {
            $ready = $true; break
        }
        Start-Sleep -Seconds 5
    }
    if (!$ready) { throw 'Le serveur ne devient pas prêt avec huit cœurs répartis.' }
    $enginePid = [int]$engines[0].ProcessId
    Save-Phase 'confirmation-benchmark'
    & $python (Join-Path $root 'Limiter-Strata-8coeurs.py') --pid $enginePid --out (Join-Path $archive 'affinite-avant-spread-confirmation.json')
    if ($LASTEXITCODE -ne 0) { throw 'Affinités de confirmation invalides.' }
    & $python (Join-Path $root 'Comparer-Q4-IQ4.py') --config (Join-Path $root 'strata-q4-p100-cache-8coeurs.json') --out (Join-Path $archive 'q4-8-repartis-confirmation') --label 'Q4-8-spread-confirmation-SSD' --pid $enginePid --repeats 2
    if ($LASTEXITCODE -ne 0) { throw 'Comparatif de confirmation incomplet.' }
    & $python (Join-Path $root 'Limiter-Strata-8coeurs.py') --pid $enginePid --out (Join-Path $archive 'affinite-apres-spread-confirmation.json')
    if ($LASTEXITCODE -ne 0) { throw 'Les affinités ont changé.' }
    & $python (Join-Path $root 'Rapport-Strata-8coeurs.py') > (Join-Path $archive 'rapport-final.stdout.log')
    if ($LASTEXITCODE -ne 0) { throw 'Validation finale des comparatifs échouée.' }
    Copy-Item -LiteralPath (Join-Path $root 'strata-engine-p100-cache.log') -Destination (Join-Path $archive 'engine-cache-ssd-fin-comparatif.log')
    Save-Phase 'complete'
} catch {
    @{status='failed';time=(Get-Date -Format o);error=$_.Exception.Message;launcher_pid=$PID} | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
    exit 1
}
