param(
    [ValidateSet('reference', 'trim', 'pipeline', 'benchmark', 'fp16', 'cpu-prefill', 'cpu-court', 'cpu-court-pin', 'cpu-court-pin-4096')]
    [string]$Profil = 'reference',
    [switch]$VerifierSeulement
)
$ErrorActionPreference = 'Stop'
$testRoot = $PSScriptRoot
$configPath = Join-Path $testRoot "config-$Profil.json"
$pythonPath = Join-Path $testRoot '.venv/Scripts/python.exe'
$sourcePath = Join-Path $testRoot 'source-officielle'
$cfg = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
if ($cfg.host -ne '127.0.0.1' -or $cfg.port -ne 8081) {
    throw 'Le profil de test doit rester sur 127.0.0.1:8081.'
}
& $pythonPath (Join-Path $testRoot 'Verifier-Test.py')
if ($LASTEXITCODE -ne 0) { throw 'La validation de la version de test a echoue.' }
if ($VerifierSeulement) { return }

# This script never stops another server. Do not load on the production cards while they are occupied.
$production = Get-CimInstance Win32_Process -Filter "Name='strata.exe'" |
    Where-Object { $_.ExecutablePath -eq 'D:\Serveur IA\strata-build-p100\strata.exe' }
if ($production) {
    throw 'Le serveur de production fonctionne encore sur les P100. Test non demarre ; production intacte.'
}
if (Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Le port 8081 est deja occupe. Aucun processus ne sera arrete.'
}
$gpuIds = $cfg.env.CUDA_VISIBLE_DEVICES.Split(',')
foreach ($gpuId in $gpuIds) {
    $free = & nvidia-smi --id=$gpuId --query-gpu=memory.free --format=csv,noheader,nounits
    if ($LASTEXITCODE -ne 0 -or [int]$free -lt 14000) {
        throw "P100 $gpuId : moins de 14000 Mio libres. Test non demarre."
    }
}
$availableGiB = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
if ($availableGiB -lt 65) { throw 'Moins de 65 Gio de RAM libres. Test non demarre.' }
$server = Start-Process -FilePath $pythonPath -ArgumentList @(
    '-u', '-m', 'serve.server', '--engine', 'strata', '--config', ('"' + $configPath + '"'),
    '--host', '127.0.0.1', '--port', '8081'
) -WorkingDirectory $sourcePath -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $testRoot "logs/server-$Profil.stdout.log") `
    -RedirectStandardError (Join-Path $testRoot "logs/server-$Profil.stderr.log")
@{ pid = $server.Id; config = $configPath; profile = $Profil; started = (Get-Date).ToString('o') } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $testRoot 'test-process.json') -Encoding utf8
Write-Output "Test $Profil lance sur http://127.0.0.1:8081 (PID $($server.Id)). Chargement en cours."
