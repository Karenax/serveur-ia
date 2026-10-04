$pidFile = Join-Path $PSScriptRoot 'qwen-gpu.pid'
$exe = Join-Path $PSScriptRoot 'cafe-build-p100\bin\llama-server.exe'
if (Test-Path $pidFile) {
 $serverPid = [int](Get-Content $pidFile)
 $process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
 if ($process -and $process.Path -eq $exe) {
  Stop-Process -Id $serverPid
  Wait-Process -Id $serverPid -Timeout 30 -ErrorAction SilentlyContinue
  'Serveur GPU arrêté.'
 }
}
