$exe = Join-Path $PSScriptRoot 'llama-cpu-b11344\llama-server.exe'
$pidFile = Join-Path $PSScriptRoot 'qwen.pid'
if (Test-Path $pidFile) {
 $serverPid = [int](Get-Content $pidFile)
 $process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
 if ($process -and $process.Path -eq $exe) { Stop-Process -Id $serverPid; "Serveur arrêté." }
}

