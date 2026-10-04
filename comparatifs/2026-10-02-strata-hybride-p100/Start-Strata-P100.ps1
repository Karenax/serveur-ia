param([switch]$Hybride, [switch]$GPUSeulement)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Le port 8080 est occupé. Arrêter le serveur existant avant Strata.'
}
$python = Join-Path $root 'Strata-src\.venv\Scripts\python.exe'
$config = Join-Path $root $(if ($GPUSeulement) { 'strata-q4-p100.json' } else { 'strata-q4-p100-hybride.json' })
'Première requête CUDA synchronisée' | Set-Content -LiteralPath (Join-Path $root 'strata-data\cuda-debug.flag')
$process = Start-Process -FilePath $python -ArgumentList @('-u', '-m', 'serve.server', '--engine', 'strata', '--config', ('"'+$config+'"'), '--port', '8080') -WorkingDirectory (Join-Path $root 'Strata-src') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'strata-server.stdout.log') -RedirectStandardError (Join-Path $root 'strata-server.stderr.log') -PassThru
$process.Id | Set-Content -LiteralPath (Join-Path $root 'strata-server.pid')
$powershellExe = Join-Path $PSHOME 'pwsh.exe'
if (!(Test-Path -LiteralPath $powershellExe)) { $powershellExe = Join-Path $PSHOME 'powershell.exe' }
$warmupScript = Join-Path $root 'Warmup-Strata-P100.ps1'
$warmup = Start-Process -FilePath $powershellExe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$warmupScript+'"'),'-ServerPid',$process.Id) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'strata-warmup.stdout.log') -RedirectStandardError (Join-Path $root 'strata-warmup.stderr.log') -PassThru
$warmup.Id | Set-Content -LiteralPath (Join-Path $root 'strata-warmup.pid')
Write-Output "Strata démarré (PID $($process.Id)), chargement en cours. http://127.0.0.1:8080"
