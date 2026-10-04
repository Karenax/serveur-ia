$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$pidFile=Join-Path $root 'huihui.pid'
if(Test-Path -LiteralPath $pidFile){
 $serverPid=[int](Get-Content -LiteralPath $pidFile)
 $p=Get-Process -Id $serverPid -ErrorAction SilentlyContinue
 if($p){
  if($p.Path -notin @("$root\cafe-build-p100\bin\llama-server.exe","$root\llama-b11344\llama-server.exe")){throw 'Le PID ne correspond pas au serveur Huihui.'}
  Stop-Process -Id $serverPid
  $p.WaitForExit()
 }
 Remove-Item -LiteralPath $pidFile
}
Write-Output 'Serveur Huihui arrêté.'
