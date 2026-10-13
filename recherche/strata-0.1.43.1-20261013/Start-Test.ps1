param(
    [ValidateSet('reference','defaults','fp16','trim','help','mtp-batch')]
    [string]$Profil = 'reference',
    [switch]$VerifierSeulement
)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskOld = Join-Path (Split-Path $taskRoot) 'strata-0.1.41-test-20261008'
$taskPython = Join-Path $taskOld '.venv/Scripts/python.exe'
$taskConfig = Join-Path $taskRoot "config-$Profil.json"
$taskCfg = Get-Content -LiteralPath $taskConfig -Raw | ConvertFrom-Json
if ($taskCfg.host -ne '127.0.0.1' -or $taskCfg.port -ne 8081) { throw 'Adresse du test incorrecte.' }
foreach ($taskPath in @($taskPython,$taskCfg.exe,$taskCfg.cwd,$taskCfg.tokenizer) + @($taskCfg.lib_dirs)) {
    if (-not (Test-Path -LiteralPath $taskPath)) { throw "Fichier requis absent : $taskPath" }
}
$taskBuild = Get-Content -LiteralPath (Join-Path $taskRoot 'engine-cuda12/BUILD.json') -Raw | ConvertFrom-Json
if ($taskBuild.version -ne '0.1.43.1' -or 60 -notin $taskBuild.archs) { throw 'Moteur incompatible avec les P100.' }
if ($VerifierSeulement) { Write-Output "Profil $Profil : fichiers et configuration vérifiés, sans inférence."; return }
if (Get-CimInstance Win32_Process -Filter "Name='strata.exe'") { throw 'Un moteur Strata fonctionne déjà. Aucun service arrêté.' }
if (Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue) { throw 'Port de test occupé.' }
foreach ($taskGpu in $taskCfg.env.CUDA_VISIBLE_DEVICES.Split(',')) {
    $taskFree = & nvidia-smi --id=$taskGpu --query-gpu=memory.free --format=csv,noheader,nounits
    if ($LASTEXITCODE -ne 0 -or [int]$taskFree -lt 14000) { throw 'VRAM insuffisante pour le test.' }
}
if ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB -lt 65) { throw 'Moins de 65 Gio de RAM disponibles.' }
$taskPriorReady = $env:STRATA_ENGINE_READY_S
try {
    $env:STRATA_ENGINE_READY_S = '1800'
    $taskServer = Start-Process -FilePath $taskPython -ArgumentList @(
    '-u','-m','serve.server','--engine','strata','--config',('"'+$taskConfig+'"'),
    '--host','127.0.0.1','--port','8081'
) -WorkingDirectory $taskCfg.cwd -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $taskRoot "logs/server-$Profil.stdout.log") `
    -RedirectStandardError (Join-Path $taskRoot "logs/server-$Profil.stderr.log")
} finally {
    if ($null -eq $taskPriorReady) { Remove-Item Env:STRATA_ENGINE_READY_S -ErrorAction SilentlyContinue }
    else { $env:STRATA_ENGINE_READY_S = $taskPriorReady }
}
@{pid=$taskServer.Id; config=$taskConfig; profile=$Profil; started=(Get-Date).ToString('o')} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'test-process.json') -Encoding utf8
Write-Output "Test $Profil démarré : PID $($taskServer.Id), port 8081."
