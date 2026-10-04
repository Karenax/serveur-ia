$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$exe = Join-Path $root 'llama-cpu-b11344\llama-server.exe'
$model = 'D:\modèle\qwen3.8FlashNext\Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf'
if (Test-Path (Join-Path $root 'qwen.pid')) {
 $savedPid = [int](Get-Content (Join-Path $root 'qwen.pid'))
 $existing = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
 if ($existing -and $existing.Path -eq $exe) { Write-Output "Serveur déjà lancé : PID $savedPid"; exit }
}
$env:CUDA_VISIBLE_DEVICES = 'GPU-a39f1b57-5a26-b53d-e943-44ef8042a438,GPU-486d5352-582e-2880-78bf-3dec4688e142'
$arguments = @('-m', ('"' + $model + '"'), '--host', '127.0.0.1', '--port', '8080', '--alias', 'qwen3.8-flash-next', '-c', '4096', '-np', '1', '-t', '16', '-tb', '16', '-b', '256', '-ub', '128', '--split-mode', 'layer',  '-ngl', '0', '--fit', 'off', '--flash-attn', 'off', '--jinja')
$process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'qwen.stdout.log') -RedirectStandardError (Join-Path $root 'qwen.stderr.log') -PassThru
$process.Id | Set-Content (Join-Path $root 'qwen.pid')
Write-Output "Démarrage PID $($process.Id), http://127.0.0.1:8080"




