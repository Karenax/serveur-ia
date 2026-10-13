$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$pidPath = Join-Path $root 'strata-iq4-server.pid'
if (Test-Path -LiteralPath $pidPath) {
    $serverPid = [int](Get-Content -LiteralPath $pidPath)
    $existing = Get-CimInstance Win32_Process -Filter "ProcessId=$serverPid" -ErrorAction SilentlyContinue
    if ($existing -and $existing.CommandLine -like '*serve.server*' -and
        ($existing.CommandLine -like '*configuration-iq4.json*' -or
         $existing.CommandLine -like '*strata-iq4-p100-hybride.json*')) {
        Write-Output 'Le serveur IQ4 est déjà démarré ou en cours de chargement : http://127.0.0.1:8080'
        return
    }
}
if (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Le port 8080 est occupé. Arrêter le serveur actuel avant de charger IQ4.'
}
$configPath = Join-Path $root 'strata-iq4-p100-hybride.json'
$server = Start-Process -FilePath (Join-Path $root 'Strata-src\.venv\Scripts\python.exe') -ArgumentList @(
    '-u','-m','serve.server','--engine','strata','--config',('"'+$configPath+'"'),'--port','8080') `
    -WorkingDirectory (Join-Path $root 'Strata-src') -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $root 'strata-iq4-server.stdout.log') `
    -RedirectStandardError (Join-Path $root 'strata-iq4-server.stderr.log') -PassThru
$server.Id | Set-Content -LiteralPath $pidPath
Write-Output "IQ4 démarré (PID $($server.Id)), chargement en cours : http://127.0.0.1:8080"
