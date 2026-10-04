$pidFile = Join-Path $PSScriptRoot 'cafe-iq3.pid'
$exe = Join-Path $PSScriptRoot 'cafe-build-p100\bin\llama-server.exe'
if (Test-Path $pidFile) {
 $serverPid = [int](Get-Content $pidFile)
 $process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
 $hybridExe = Join-Path $PSScriptRoot 'cafe-build-p100-hybride\bin\llama-server.exe'
 if ($process -and $process.Path -in @($exe,$hybridExe)) {
  Stop-Process -Id $serverPid
  Wait-Process -Id $serverPid -Timeout 30 -ErrorAction SilentlyContinue
  'Serveur Café arrêté.'
 }
}

