param([switch]$MTP, [ValidateRange(512,262144)][int]$Context = 4096, [int]$CacheMiB = 0,
      [ValidateRange(1,16)][int]$Parallel = 1,
      [ValidateRange(0,1)][double]$CpuFraction = 0,
      [ValidateRange(512,4096)][int]$ReserveMiB = 2048,
      [ValidateRange(1,16)][int]$CpuThreads = 15)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$exe = Join-Path $root 'cafe-build-p100\bin\llama-server.exe'
if ($CpuFraction -gt 0) { $exe = Join-Path $root 'cafe-build-p100-hybride\bin\llama-server.exe' }
if (!(Test-Path $exe)) { throw 'Le moteur P100 doit être compilé avant le lancement.' }
if ($CpuFraction -gt 0 -and !(Test-Path -LiteralPath (Join-Path $root 'cafe-build-p100-hybride\build-hybride.json'))) {
 throw 'La compilation hybride doit être terminée avant ce lancement.'
}
if ($CpuFraction -gt 0) {
 $proof = Get-Content -LiteralPath (Join-Path $root 'cafe-build-p100-hybride\build-hybride.json') -Raw | ConvertFrom-Json
 $cudaHash = (Get-FileHash -LiteralPath (Join-Path (Split-Path $exe) 'ggml-cuda.dll') -Algorithm SHA256).Hash.ToLowerInvariant()
 if ($proof.gpu_only -ne $false -or $cudaHash -ne $proof.cuda_sha256) { throw 'Le module CUDA ne correspond pas à la compilation hybride.' }
}
if (Get-NetTCPConnection -State Listen -LocalPort 8080 -ErrorAction SilentlyContinue) { throw 'Le port 8080 est déjà utilisé.' }
$env:PATH = (Join-Path $root 'toolchain\cuda-12.4\bin') + ';' + $env:PATH
$env:CUDA_VISIBLE_DEVICES = 'GPU-a39f1b57-5a26-b53d-e943-44ef8042a438,GPU-486d5352-582e-2880-78bf-3dec4688e142'
$env:CUDA_DISABLE_PTX_JIT = '1'
$env:GGML_CUDA_MOE_DIRECT_CPU_FRAC = $CpuFraction.ToString([Globalization.CultureInfo]::InvariantCulture)
$env:GGML_CUDA_MOE_DIRECT_CPU_THREADS = "$CpuThreads"
$env:GGML_CUDA_MOE_DIRECT_BUDGET_MB = "$CacheMiB"
$env:GGML_CUDA_MOE_DIRECT_RESERVE_MB = "$ReserveMiB"
$env:GGML_CUDA_MOE_DIRECT_STATS = '50'
$env:GGML_CUDA_MOE_DIRECT_PROFILE = '0'
Remove-Item Env:GGML_CUDA_ENABLE_UNIFIED_MEMORY -ErrorAction SilentlyContinue
$model = 'C:\Temp\Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf'
$mode = if ($MTP) { 'mtp' } else { 'sans-mtp' }
if ($CpuFraction -gt 0) { $mode = 'hybride-' + $mode }
# Context is the total KV pool, divided between Parallel conversations.
$argsList = @('-m', ('"' + $model + '"'), '--host', '127.0.0.1', '--port', '8080', '--alias', 'qwen3.8-flash-next-iq3-s', '-c', "$Context", '-np', "$Parallel", '--cont-batching', '-t', '4', '-tb', '4', '-b', '256', '-ub', '128', '-ngl', '99', '--fit', 'off', '--host-moe', '--no-pipeline-parallel', '--moe-cache', 'off', '--split-mode', 'layer', '--tensor-split', '1,1', '--load-mode', 'none', '--lazy-mode', 'off', '-ot', 'per_layer_token_embd=CPU', '--flash-attn', 'off', '--jinja', '--metrics', '-lv', '4')
if ($MTP) {
 $draft = 'D:\modèle\qwen3.8FlashNext\mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf'
 $argsList += @('-md', ('"' + $draft + '"'), '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2', '--spec-draft-ngl', '99')
}
$process = Start-Process -FilePath $exe -ArgumentList $argsList -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root "cafe-iq3-$mode.stdout.log") -RedirectStandardError (Join-Path $root "cafe-iq3-$mode.stderr.log") -PassThru
$process.Id | Set-Content (Join-Path $root 'cafe-iq3.pid')
@{mode=$mode;exe=$exe;model=$model;context=$Context;parallel=$Parallel;cache_mib=$CacheMiB;vram_reserve_mib=$ReserveMiB;cpu_fraction=$CpuFraction;cpu_expert_threads=$CpuThreads;gpu_only_build=($CpuFraction -eq 0);arguments=$argsList} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $root 'cafe-iq3-configuration.json') -Encoding utf8
Write-Output "Démarrage Café $mode : PID $($process.Id), $Parallel conversations, contexte total $Context, http://127.0.0.1:8080"


