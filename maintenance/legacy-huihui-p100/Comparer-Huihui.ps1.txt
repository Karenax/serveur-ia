$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py='C:\Users\karen\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
foreach($cfg in @(@{MTP=$true;DraftTokens=2;Split='layer';Flash='on'},@{MTP=$false;Split='row';Flash='on'},@{MTP=$true;DraftTokens=2;Split='row';Flash='on'},@{MTP=$true;DraftTokens=2;Split='layer';Flash='off'})){
 $serverPid=[int](Get-Content "$root\huihui.pid")
 $p=Get-Process -Id $serverPid -ErrorAction SilentlyContinue
 if($p){if($p.Path -ne "$root\cafe-build-p100\bin\llama-server.exe"){throw 'PID inattendu'};Stop-Process -Id $serverPid; $p.WaitForExit()}
 Start-Sleep -Seconds 2
 & "$root\Start-Huihui-P100.ps1" @cfg
 $mode=(Get-Content "$root\huihui-configuration.json" -Raw|ConvertFrom-Json).mode
 & $py -u "$root\Tester-Huihui.py" --mode $mode
 $archive=Get-ChildItem "$root\comparatifs" -Directory -Filter "huihui-$mode-*"|Sort-Object LastWriteTime -Descending|Select-Object -First 1
 Copy-Item "$root\huihui-$mode.stdout.log","$root\huihui-$mode.stderr.log" -Destination $archive.FullName
 $p=Get-Process -Id ([int](Get-Content "$root\huihui.pid")) -ErrorAction SilentlyContinue
 if($p){@{ram_observed_gib=$p.WorkingSet64/1GB;private_gib=$p.PrivateMemorySize64/1GB}|ConvertTo-Json|Set-Content (Join-Path $archive.FullName 'ram-observee.json'); & nvidia-smi --query-gpu=uuid,name,memory.used,utilization.gpu --format=csv|Set-Content (Join-Path $archive.FullName 'gpu-observe.csv')}
 Write-Output "Essai terminé : $mode"
}
