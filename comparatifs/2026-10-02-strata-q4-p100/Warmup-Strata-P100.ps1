param([Parameter(Mandatory=$true)][int]$ServerPid)
$ErrorActionPreference = 'Stop'
$marker = Join-Path $PSScriptRoot 'strata-data\cuda-debug.flag'
$watch = [Diagnostics.Stopwatch]::StartNew()
try {
    while ($watch.Elapsed.TotalMinutes -lt 45) {
        if (!(Get-Process -Id $ServerPid -ErrorAction SilentlyContinue)) { return }
        $health = $null
        try { $health = Invoke-RestMethod 'http://127.0.0.1:8080/health' -TimeoutSec 5 } catch {}
        if ($health.service -eq 'strata' -and $health.loaded) { break }
        Start-Sleep -Seconds 3
    }
    if (!$health.loaded) { throw 'Strata ne devient pas prêt après 45 minutes.' }
    $payload = @{model='qwen3.8-flash-next';messages=@(@{role='user';content='Explique en français pourquoi le ciel est bleu, puis pourquoi il devient rouge au coucher du soleil. Donne une explication précise et accessible.'});max_tokens=1;temperature=0;seed=42;cache_prompt=$false;chat_template_kwargs=@{enable_thinking=$false}} | ConvertTo-Json -Depth 7
    $answer = Invoke-RestMethod 'http://127.0.0.1:8080/v1/chat/completions' -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload)) -TimeoutSec 300
    if ($answer.usage.completion_tokens -ne 1) { throw 'La requête initiale ne produit pas le token attendu.' }
    $answer | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'strata-warmup-response.json') -Encoding utf8
    if (Test-Path -LiteralPath $marker) { Remove-Item -LiteralPath $marker }
    Write-Output "$(Get-Date -Format o) Initialisation CUDA validée ; synchronisation diagnostique désactivée."
} catch {
    # Keep synchronization enabled if the initial request fails.
    Write-Error $_
    exit 1
}
