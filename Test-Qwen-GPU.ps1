param([ValidateSet('sans-mtp','mtp')][string]$Mode = 'sans-mtp', [int]$MaxTokens = 256)
$ErrorActionPreference = 'Stop'
$protocol = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'protocole-comparatif-q4.json') -Raw | ConvertFrom-Json
$root = $PSScriptRoot
$serverPid = [int](Get-Content (Join-Path $root 'qwen-gpu.pid'))
$monitorPath = Join-Path $root "mesures-$Mode.csv"
$job = Start-Job -ArgumentList $serverPid,$monitorPath -ScriptBlock {
 param($serverId,$outputPath)
 'time,gpu_index,gpu_util_pct,vram_mib,power_w,server_cpu_seconds,server_ram_bytes,io_read_bytes_per_sec' | Set-Content $outputPath
 while ($true) {
  $proc = Get-Process -Id $serverId -ErrorAction SilentlyContinue
  if (!$proc) { break }
  $perf = Get-CimInstance Win32_PerfFormattedData_PerfProc_Process -Filter "IDProcess=$serverId" -ErrorAction SilentlyContinue
  $stamp = (Get-Date).ToString('o')
  $cpu = $proc.TotalProcessorTime.TotalSeconds.ToString([Globalization.CultureInfo]::InvariantCulture)
  $rows = & nvidia-smi --query-gpu=index,utilization.gpu,memory.used,power.draw --format=csv,noheader,nounits
  foreach ($row in $rows) { "$stamp,$($row -replace ', ',','),$cpu,$($proc.WorkingSet64),$($perf.IOReadBytesPersec)" | Add-Content $outputPath }
  Start-Sleep -Seconds 2
 }
}
try {
 $prompts = @($protocol.prompts)
 $results = @()
 for ($i = 0; $i -lt $prompts.Count; $i++) {
  $payload = @{model='qwen3.8-flash-next'; messages=@(@{role='user';content=$prompts[$i]}); max_tokens=$MaxTokens; temperature=$protocol.temperature; seed=$protocol.seed; cache_prompt=$protocol.cache_prompt; chat_template_kwargs=@{enable_thinking=$protocol.enable_thinking}} | ConvertTo-Json -Depth 8
  $payload | Set-Content (Join-Path $root "requete-$Mode-test-$($i+1).json") -Encoding utf8
  $watch = [Diagnostics.Stopwatch]::StartNew()
  $answer = Invoke-RestMethod 'http://127.0.0.1:8080/v1/chat/completions' -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload)) -TimeoutSec 480
  $watch.Stop()
  $answer | ConvertTo-Json -Depth 16 | Set-Content (Join-Path $root "gpu-$Mode-test-$($i+1).json") -Encoding utf8
  $acceptance = if ($answer.timings.draft_n -gt 0) { $answer.timings.draft_n_accepted / $answer.timings.draft_n } else { $null }
  $result = [pscustomobject]@{mode=$Mode;test=$i+1;elapsed_seconds=$watch.Elapsed.TotalSeconds;prompt_tokens=$answer.usage.prompt_tokens;output_tokens=$answer.usage.completion_tokens;prompt_tps=$answer.timings.prompt_per_second;generation_tps=$answer.timings.predicted_per_second;draft_tokens=$answer.timings.draft_n;draft_accepted=$answer.timings.draft_n_accepted;draft_acceptance=$acceptance;finish_reason=$answer.choices[0].finish_reason}
  $results += $result
  $result | ConvertTo-Json -Compress
 }
 $results | Export-Csv (Join-Path $root "resultats-$Mode.csv") -NoTypeInformation -Encoding utf8
 Invoke-RestMethod 'http://127.0.0.1:8080/metrics' | Set-Content (Join-Path $root "metrics-$Mode.txt") -Encoding utf8
} finally {
 Stop-Job $job
 Remove-Job $job
}
