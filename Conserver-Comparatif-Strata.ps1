$ErrorActionPreference = 'Stop'
$archive = Join-Path $PSScriptRoot 'comparatifs\2026-10-02-strata-q4-p100'
$results = Import-Csv -LiteralPath (Join-Path $archive 'resultats-strata-mtp.csv')
if ($results.Count -ne 2) { throw 'Les deux essais GPU complets sont requis avant archivage final.' }
foreach ($n in 1,2) {
    $log = Get-Content -LiteralPath (Join-Path $archive "engine-strata-mtp-test-$n.log") -Raw
    if ($log -notmatch 'decode expert compute: 0 CPU jobs,') { throw "Calcul expert GPU non confirmé pour le test $n." }
}
$files = @(
    'Start-Strata-P100.ps1','Stop-Strata-P100.ps1','Warmup-Strata-P100.ps1',
    'Test-Strata-P100.ps1','Test-Qwen-GPU.ps1','Build-Strata-P100.cmd','Check-Strata-P100.cmd',
    'Fix-Strata-Build-Dependencies.ps1','Check-Strata-Build-Dependencies.cmd',
    'Convert-MTP-Strata.py','Analyser-Comparatifs.py','Generer-CompteRendu-Strata.py','Conserver-Comparatif-Strata.ps1',
    'protocole-comparatif-q4.json','strata-q4-p100.json','strata-build-dependencies-fixed.log',
    'strata-check-build-dependencies.log','strata-engine-p100.log',
    'strata-server.stdout.log','strata-server.stderr.log',
    'strata-warmup.stdout.log','strata-warmup.stderr.log','strata-warmup-response.json',
    'COMPARATIF-Q4-STRATA.txt','LISEZ-MOI.txt'
)
foreach ($name in $files) {
    $source = Join-Path $PSScriptRoot $name
    if (Test-Path -LiteralPath $source) { Copy-Item -LiteralPath $source -Destination $archive -Force }
}
foreach ($name in 'comparatif-q4-p100.csv','ressources-q4-p100.json') {
    Copy-Item -LiteralPath (Join-Path (Join-Path $PSScriptRoot 'comparatifs') $name) -Destination $archive -Force
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Strata-src\tests\cuda\prefill_p100_test.cpp') -Destination $archive -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'strata-build-p100\strata.exe') -Destination (Join-Path $archive 'strata-p100-gpu-seul.exe') -Force
& git -C (Join-Path $PSScriptRoot 'Strata-src') diff --binary ("--output=" + (Join-Path $archive 'adaptations-strata.patch'))
if ($LASTEXITCODE) { throw 'Impossible de conserver les adaptations du code.' }
$engine = Get-CimInstance Win32_Process -Filter "Name='strata.exe'" | Where-Object {
    $_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -eq (Join-Path $PSScriptRoot 'strata-build-p100\strata.exe')
} | Select-Object -First 1
$modelDirectory = 'D:\modèle\qwen3.8FlashNext'
$modelFiles = Get-ChildItem -LiteralPath $modelDirectory -File | Where-Object {
    $_.Name -like 'Qwen3.8-Flash-Next-UD-Q4_K_XL-*.gguf' -or $_.Name -eq 'mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf'
} | ForEach-Object { [pscustomobject]@{path=$_.FullName;bytes=$_.Length;mtime_utc=$_.LastWriteTimeUtc.ToString('o')} }
$hashed = Get-ChildItem -LiteralPath $archive -File -Recurse | Where-Object { $_.Name -ne 'manifest-final.json' } | ForEach-Object {
    [pscustomobject]@{path=$_.FullName.Substring($archive.Length+1);bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}
}
$manifest = [pscustomobject]@{
    created=(Get-Date).ToString('o');engine='Strata';commit=(& git -C (Join-Path $PSScriptRoot 'Strata-src') rev-parse HEAD);
    engine_pid=$engine.ProcessId;engine_creation=$engine.CreationDate.ToString('o');
    engine_binary_sha256=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'strata-build-p100\strata.exe')).Hash;
    cpu_expert_jobs=0;ple_ram_gib=26.82;expert_ram_gib=55.71;staging_blobs=64;
    model_files=$modelFiles;model_file_identity_note='Fichiers GGUF originaux conservés ; tailles et dates contrôlées. Pas de relecture des 111 Go pour calculer une empreinte intégrale.';
    main_model_compatibility='Projections natives Q4/Q5/Q8 préservées ; petits tenseurs compatibles BF16 décrits dans conversions.json.';
    mtp_compatibility='Draft Q8_0 converti en Q2_0 pour Strata ; Café utilisait le draft Q8_0 original.';
    files=$hashed
}
$manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $archive 'manifest-final.json') -Encoding utf8
Write-Output "Archive finale : $archive ($($hashed.Count) fichiers avec empreintes SHA256)."
