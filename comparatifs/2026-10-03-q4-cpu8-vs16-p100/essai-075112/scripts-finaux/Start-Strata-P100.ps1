param([switch]$Hybride, [switch]$GPUSeulement, [switch]$CacheContigu, [ValidateSet(8,16)][int]$CpuCores = 16)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Le port 8080 est occupé. Arrêter le serveur existant avant Strata.'
}
$python = Join-Path $root 'Strata-src\.venv\Scripts\python.exe'
if ($GPUSeulement -and $CpuCores -eq 8) { throw 'Le test à 8 cœurs nécessite le mode hybride CPU et GPU.' }
$config = Join-Path $root $(if ($GPUSeulement) { 'strata-q4-p100.json' } elseif ($CpuCores -eq 8) { 'strata-q4-p100-8coeurs.json' } else { 'strata-q4-p100-hybride.json' })
if ($CacheContigu) {
    if ($GPUSeulement) { throw 'Le cache contigu est préparé pour la configuration hybride.' }
    $cache = 'C:\Strata-cache\q4-experts-contigus'
    $bin = Join-Path $cache 'experts.bin'
    if (!(Test-Path -LiteralPath $bin) -or (Get-Item -LiteralPath $bin).Length -ne 77017907200) {
        throw 'Créer le cache complet avec .\Preparer-Cache-Q4.ps1 avant le lancement.'
    }
    $source = Get-Content -LiteralPath (Join-Path $cache 'experts.bin.src.json') -Raw | ConvertFrom-Json
    $proof = Get-Content -LiteralPath (Join-Path $cache 'verification-cache.json') -Raw | ConvertFrom-Json
    $layoutHash = (Get-FileHash -LiteralPath (Join-Path $root 'strata-data\q4-local\native_experts.txt') -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($source.bytes -ne 77017907200 -or $proof.bytes -ne 77017907200 -or $proof.verified_samples -ne 9 -or $source.native_experts_sha256 -ne $layoutHash) {
        throw 'La validation du cache natif ne correspond pas au modèle Q4 actuel.'
    }
    $epochTicks = ([datetime]'1970-01-01T00:00:00Z').ToUniversalTime().Ticks
    foreach ($shard in $source.shards) {
        $file = Get-Item -LiteralPath (Join-Path (Join-Path $root 'strata-data\model-q4') $shard.name)
        $mtimeNs = ($file.LastWriteTimeUtc.Ticks - $epochTicks) * 100
        if ($file.Length -ne $shard.size -or $mtimeNs -ne $proof.source_mtime_ns.PSObject.Properties[$shard.name].Value) {
            throw 'Les GGUF sources ont changé depuis la création du cache. Préparer un nouveau dossier de cache.'
        }
    }
    $config = Join-Path $root $(if ($CpuCores -eq 8) { 'strata-q4-p100-cache-8coeurs.json' } else { 'strata-q4-p100-cache.json' })
}
'Première requête CUDA synchronisée' | Set-Content -LiteralPath (Join-Path $root 'strata-data\cuda-debug.flag')
$process = Start-Process -FilePath $python -ArgumentList @('-u', '-m', 'serve.server', '--engine', 'strata', '--config', ('"'+$config+'"'), '--port', '8080') -WorkingDirectory (Join-Path $root 'Strata-src') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'strata-server.stdout.log') -RedirectStandardError (Join-Path $root 'strata-server.stderr.log') -PassThru
$process.Id | Set-Content -LiteralPath (Join-Path $root 'strata-server.pid')
$powershellExe = Join-Path $PSHOME 'pwsh.exe'
if (!(Test-Path -LiteralPath $powershellExe)) { $powershellExe = Join-Path $PSHOME 'powershell.exe' }
$warmupScript = Join-Path $root 'Warmup-Strata-P100.ps1'
$warmup = Start-Process -FilePath $powershellExe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$warmupScript+'"'),'-ServerPid',$process.Id,'-CpuCores',$CpuCores) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'strata-warmup.stdout.log') -RedirectStandardError (Join-Path $root 'strata-warmup.stderr.log') -PassThru
$warmup.Id | Set-Content -LiteralPath (Join-Path $root 'strata-warmup.pid')
Write-Output "Strata démarré (PID $($process.Id)), chargement en cours. http://127.0.0.1:8080"
