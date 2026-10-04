$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Le port 8080 est occupé. Arrêter le serveur actuel avant de charger IQ3_S.'
}
$config = Join-Path $root 'strata-iq3-p100-hybride.json'
if (!(Test-Path -LiteralPath (Join-Path $root 'strata-data\iq3-s-local\native_experts.txt'))) {
    throw 'Préparer le pack IQ3_S avec Strata-src\tools\iq_pack.py avant le lancement.'
}
'Première requête CUDA synchronisée' | Set-Content -LiteralPath (Join-Path $root 'strata-data\cuda-debug-iq3.flag')
$server = Start-Process -FilePath (Join-Path $root 'Strata-src\.venv\Scripts\python.exe') -ArgumentList @(
    '-u','-m','serve.server','--engine','strata','--config',('"'+$config+'"'),'--port','8080') `
    -WorkingDirectory (Join-Path $root 'Strata-src') -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $root 'strata-iq3-server.stdout.log') `
    -RedirectStandardError (Join-Path $root 'strata-iq3-server.stderr.log') -PassThru
$server.Id | Set-Content -LiteralPath (Join-Path $root 'strata-iq3-server.pid')
$test = Start-Process -FilePath (Join-Path $root 'Strata-src\.venv\Scripts\python.exe') -ArgumentList @(
    '-u',('"'+(Join-Path $root 'Tester-Strata-IQ3.py')+'"')) -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $root 'strata-iq3-test.stdout.log') `
    -RedirectStandardError (Join-Path $root 'strata-iq3-test.stderr.log') -PassThru
$test.Id | Set-Content -LiteralPath (Join-Path $root 'strata-iq3-test.pid')
Write-Output "IQ3_S démarré (PID $($server.Id)), chargement et validation en cours : http://127.0.0.1:8080"
