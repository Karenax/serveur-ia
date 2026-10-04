param([ValidateSet('strata-mtp')][string]$Mode = 'strata-mtp', [int]$MaxTokens = 256)
$ErrorActionPreference = 'Stop'
$protocolPath = Join-Path $PSScriptRoot 'protocole-comparatif-q4.json'
$protocol = Get-Content -LiteralPath $protocolPath -Raw | ConvertFrom-Json
$archiveRoot = Join-Path $PSScriptRoot 'comparatifs\2026-10-02-strata-q4-p100'
$root = Join-Path $archiveRoot ('essais\'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $root -Force | Out-Null
Write-Output "Résultats conservés dans $root"
Copy-Item -LiteralPath $protocolPath -Destination (Join-Path $root 'protocole.json')
$engineLogPath = Join-Path $PSScriptRoot 'strata-engine-p100.log'
$serverPid = (Get-CimInstance Win32_Process -Filter "Name='strata.exe'" | Where-Object { $_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -eq (Join-Path $PSScriptRoot 'strata-build-p100\strata.exe') } | Select-Object -First 1).ProcessId
if (!$serverPid) { throw 'Moteur Strata absent' }
$engineFile = Join-Path $PSScriptRoot 'strata-build-p100\strata.exe'
[pscustomobject]@{date=(Get-Date).ToString('o');engine_pid=$serverPid;engine_start=(Get-Process -Id $serverPid).StartTime.ToString('o');engine_binary_sha256=(Get-FileHash -LiteralPath $engineFile).Hash;mode=$Mode;max_tokens=$MaxTokens;temperature=0;seed=42;thinking=$false;diagnostic_sync=(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'strata-data\cuda-debug.flag'));configuration=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'strata-q4-p100.json') -Raw | ConvertFrom-Json)} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $root 'configuration-tests.json') -Encoding utf8
$monitorPath = Join-Path $root "mesures-$Mode.csv"
$job = Start-Job -ArgumentList $serverPid,$monitorPath -ScriptBlock {
 param($serverId,$outputPath)
 'time,gpu_index,gpu_util_pct,vram_mib,power_w,server_cpu_seconds,server_ram_bytes,io_read_bytes_per_sec,disk_d_read_bytes_per_sec' | Set-Content $outputPath
 while ($true) {
  $proc = Get-Process -Id $serverId -ErrorAction SilentlyContinue
  if (!$proc) { break }
  $perf = Get-CimInstance Win32_PerfFormattedData_PerfProc_Process -Filter "IDProcess=$serverId" -ErrorAction SilentlyContinue
  $stamp = (Get-Date).ToString('o')
  $diskRead = (Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk -Filter "Name='1 D:'" -ErrorAction SilentlyContinue).DiskReadBytesPersec
  $cpu = $proc.TotalProcessorTime.TotalSeconds.ToString([Globalization.CultureInfo]::InvariantCulture)
  $rows = & nvidia-smi --query-gpu=index,utilization.gpu,memory.used,power.draw --format=csv,noheader,nounits
  foreach ($row in $rows) { "$stamp,$($row -replace ', ',','),$cpu,$($proc.WorkingSet64),$($perf.IOReadBytesPersec),$diskRead" | Add-Content $outputPath }
  Start-Sleep -Seconds 2
 }
}
try {
 $prompts = @($protocol.prompts)
 $results = @()
 for ($i = 0; $i -lt $prompts.Count; $i++) {
  $payload = @{model='qwen3.8-flash-next'; messages=@(@{role='user';content=$prompts[$i]}); max_tokens=$MaxTokens; temperature=$protocol.temperature; seed=$protocol.seed; cache_prompt=$protocol.cache_prompt; chat_template_kwargs=@{enable_thinking=$protocol.enable_thinking}} | ConvertTo-Json -Depth 8
  $payload | Set-Content (Join-Path $root "requete-$Mode-test-$($i+1).json") -Encoding utf8
  $logBefore = @(Get-Content -LiteralPath $engineLogPath).Count
  $watch = [Diagnostics.Stopwatch]::StartNew()
  try {
   $answer = Invoke-RestMethod 'http://127.0.0.1:8080/v1/chat/completions' -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload)) -TimeoutSec 900
  } catch {
   [pscustomobject]@{date=(Get-Date).ToString('o');mode=$Mode;test=$i+1;elapsed_seconds=$watch.Elapsed.TotalSeconds;error=$_.Exception.Message;server_response=$_.ErrorDetails.Message} | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $root "erreur-$Mode-test-$($i+1).json") -Encoding utf8
   throw
  } finally {
   $requestLog = @(Get-Content -LiteralPath $engineLogPath | Select-Object -Skip $logBefore)
   $requestLog | Set-Content -LiteralPath (Join-Path $root "engine-$Mode-test-$($i+1).log") -Encoding utf8
  }
  $watch.Stop()
  $answer | ConvertTo-Json -Depth 16 | Set-Content (Join-Path $root "gpu-$Mode-test-$($i+1).json") -Encoding utf8
  if (($requestLog -join "`n") -notmatch 'decode expert compute: 0 CPU jobs,') { throw 'Calcul GPU seul non confirmé dans le journal de cette requête.' }
  $acceptance = if ($answer.timings.draft_n -gt 0) { $answer.timings.draft_n_accepted / $answer.timings.draft_n } else { $null }
  $result = [pscustomobject]@{mode=$Mode;test=$i+1;elapsed_seconds=$watch.Elapsed.TotalSeconds;prompt_tokens=$answer.usage.prompt_tokens;output_tokens=$answer.usage.completion_tokens;prompt_tps=$answer.timings.prompt_per_second;generation_tps=($answer.timings.predicted_n*1000.0/$answer.timings.predicted_ms);reused_tokens=$answer.timings.cache_n;draft_tokens=$answer.timings.draft_n;draft_accepted=$answer.timings.draft_n_accepted;draft_acceptance=$acceptance;finish_reason=$answer.choices[0].finish_reason}
  $results += $result
  $results | Export-Csv (Join-Path $root "resultats-$Mode.csv") -NoTypeInformation -Encoding utf8
  $result | ConvertTo-Json -Compress
 }
 $results | Export-Csv (Join-Path $root "resultats-$Mode.csv") -NoTypeInformation -Encoding utf8
 Invoke-RestMethod 'http://127.0.0.1:8080/metrics' | ConvertTo-Json -Depth 20 | Set-Content (Join-Path $root "metrics-$Mode.json") -Encoding utf8
} finally {
 Stop-Job $job
 Remove-Job $job
}
# Stable copies for the comparison index; each original run keeps its own folder.
Get-ChildItem -LiteralPath $root -File | Copy-Item -Destination $archiveRoot -Force
