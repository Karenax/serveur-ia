param([switch]$MTP, [ValidateRange(512,262144)][int]$Context = 4096, [int]$CacheMiB = 8192,
      [ValidateRange(1,16)][int]$Parallel = 1)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$exe = Join-Path $root 'cafe-build-p100\bin\llama-server.exe'
if (!(Test-Path $exe)) { throw 'Le moteur P100 doit être compilé avant le lancement.' }
if (Get-NetTCPConnection -State Listen -LocalPort 8080 -ErrorAction SilentlyContinue) { throw 'Le port 8080 est déjà utilisé.' }
$env:PATH = (Join-Path $root 'toolchain\cuda-12.4\bin') + ';' + $env:PATH
$env:CUDA_VISIBLE_DEVICES = 'GPU-a39f1b57-5a26-b53d-e943-44ef8042a438,GPU-486d5352-582e-2880-78bf-3dec4688e142'
$env:CUDA_DISABLE_PTX_JIT = '1'
$env:GGML_CUDA_MOE_DIRECT_CPU_FRAC = '0'
$env:GGML_CUDA_MOE_DIRECT_BUDGET_MB = "$CacheMiB"
$env:GGML_CUDA_MOE_DIRECT_RESERVE_MB = '2048'
$env:GGML_CUDA_MOE_DIRECT_STATS = '50'
$env:GGML_CUDA_MOE_DIRECT_PROFILE = '0'
Remove-Item Env:GGML_CUDA_ENABLE_UNIFIED_MEMORY -ErrorAction SilentlyContinue
$model = 'D:\modèle\qwen3.8FlashNext\Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf'
$mode = if ($MTP) { 'mtp' } else { 'sans-mtp' }
# Context is the total KV pool, divided between Parallel conversations.
$argsList = @('-m', ('"' + $model + '"'), '--host', '127.0.0.1', '--port', '8080', '--alias', 'qwen3.8-flash-next', '-c', "$Context", '-np', "$Parallel", '--cont-batching', '-t', '4', '-tb', '4', '-b', '256', '-ub', '128', '-ngl', '99', '--fit', 'off', '--host-moe', '--no-pipeline-parallel', '--moe-cache', 'off', '--split-mode', 'layer', '--tensor-split', '1,1', '--load-mode', 'none', '--lazy-mode', 'off', '-ot', 'per_layer_token_embd=CPU', '--flash-attn', 'off', '--jinja', '--metrics', '-lv', '4')
if ($MTP) {
 $draft = 'D:\modèle\qwen3.8FlashNext\mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf'
 $argsList += @('-md', ('"' + $draft + '"'), '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2', '--spec-draft-ngl', '99')
}
$process = Start-Process -FilePath $exe -ArgumentList $argsList -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root "gpu-$mode.stdout.log") -RedirectStandardError (Join-Path $root "gpu-$mode.stderr.log") -PassThru
$process.Id | Set-Content (Join-Path $root 'qwen-gpu.pid')
Write-Output "Démarrage GPU $mode : PID $($process.Id), $Parallel conversations, contexte total $Context, http://127.0.0.1:8080"

