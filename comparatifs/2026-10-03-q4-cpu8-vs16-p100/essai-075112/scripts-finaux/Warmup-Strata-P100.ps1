param([Parameter(Mandatory=$true)][int]$ServerPid, [ValidateSet(8,16)][int]$CpuCores = 16)
$ErrorActionPreference = 'Stop'
$marker = Join-Path $PSScriptRoot 'strata-data\cuda-debug.flag'
$watch = [Diagnostics.Stopwatch]::StartNew()
try {
    while ($watch.Elapsed.TotalMinutes -lt 90) {
        if (!(Get-Process -Id $ServerPid -ErrorAction SilentlyContinue)) { return }
        $health = $null
        try { $health = Invoke-RestMethod 'http://127.0.0.1:8080/health' -TimeoutSec 5 } catch {}
        if ($health.service -eq 'strata' -and $health.loaded) { break }
        Start-Sleep -Seconds 3
    }
    if (!$health.loaded) { throw 'Strata ne devient pas prêt après 90 minutes.' }
    $payload = @{model='qwen3.8-flash-next';messages=@(@{role='user';content='Explique en français pourquoi le ciel est bleu, puis pourquoi il devient rouge au coucher du soleil. Donne une explication précise et accessible.'});max_tokens=1;temperature=0;seed=42;cache_prompt=$false;chat_template_kwargs=@{enable_thinking=$false}} | ConvertTo-Json -Depth 7
    $answer = Invoke-RestMethod 'http://127.0.0.1:8080/v1/chat/completions' -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload)) -TimeoutSec 300
    if ($answer.usage.completion_tokens -ne 1) { throw 'La requête initiale ne produit pas le token attendu.' }
    $answer | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'strata-warmup-response.json') -Encoding utf8
    if (Test-Path -LiteralPath $marker) { Remove-Item -LiteralPath $marker }
    Write-Output "$(Get-Date -Format o) Initialisation CUDA validée ; synchronisation diagnostique désactivée."
    if ($CpuCores -eq 8) {
        $ownedIds = @($ServerPid)
        for ($level = 0; $level -lt 3; $level++) {
            $children = @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -in $ownedIds -and $_.ProcessId -notin $ownedIds })
            if (!$children.Count) { break }
            $ownedIds += @($children | ForEach-Object ProcessId)
        }
        $engine = @(Get-CimInstance Win32_Process -Filter "Name='strata.exe'" | Where-Object { $_.ProcessId -in $ownedIds -and $_.CommandLine -match '--pool-workers 7(?: |$)' })
        if ($engine.Count -ne 1) { throw 'Impossible de retrouver le moteur à 7 travailleurs CPU.' }
        & (Join-Path $PSScriptRoot 'Strata-src\.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'Limiter-Strata-8coeurs.py') --pid $engine[0].ProcessId --out (Join-Path $PSScriptRoot 'strata-affinite-8coeurs.json') --apply
        if ($LASTEXITCODE -ne 0) { throw 'La vérification des affinités sur 8 cœurs a échoué.' }
        Write-Output "$(Get-Date -Format o) Affinités CPU vérifiées sur huit cœurs physiques répartis."
    }
} catch {
    # Keep synchronization enabled if the initial request fails.
    Write-Error $_
    exit 1
}
