$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$prefix = $projectRoot.TrimEnd('\') + '\'
function Assert-ProjectPath([string]$Path) {
    $resolved = [IO.Path]::GetFullPath($Path)
    if (-not $resolved.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw "Chemin hors projet : $resolved" }
    return $resolved
}
function Get-StreamHash($Stream) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($Stream)).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
$pairs = @(
    @('cudart.zip', 'llama-b11344'),
    @('llama-cpu.zip', 'llama-cpu-b11344'),
    @('llama-cuda.zip', 'llama-b11344'),
    @('unsloth-legacy.zip', 'unsloth-legacy'),
    @('unsloth-portable.zip', 'unsloth-portable')
)
$results = @()
foreach ($pair in $pairs) {
    $archivePath = Assert-ProjectPath (Join-Path $projectRoot $pair[0])
    if (-not (Test-Path -LiteralPath $archivePath)) { continue }
    $length = (Get-Item -LiteralPath $archivePath).Length
    $archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
    $zip = [IO.Compression.ZipFile]::OpenRead($archivePath)
    $entries = @(); $valid = $true
    try {
        foreach ($entry in $zip.Entries) {
            if (-not $entry.Name) { continue }
            $target = Assert-ProjectPath (Join-Path (Join-Path $projectRoot $pair[1]) $entry.FullName)
            $same = $false
            if ((Test-Path -LiteralPath $target -PathType Leaf) -and (Get-Item -LiteralPath $target).Length -eq $entry.Length) {
                $stream = $entry.Open()
                try { $expected = Get-StreamHash $stream } finally { $stream.Dispose() }
                $same = $expected -eq (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
            }
            $entries += [pscustomobject]@{ entry=$entry.FullName; identical=$same }
            if (-not $same) { $valid = $false }
        }
    } finally { $zip.Dispose() }
    $result = [pscustomobject]@{ path=$archivePath; bytes=$length; sha256=$archiveHash; extracted_directory=$pair[1]; entries=$entries; deleted=$false }
    if ($valid -and $entries.Count -gt 0) {
        Remove-Item -LiteralPath $archivePath
        $result.deleted = $true
    }
    $results += $result
    $results | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'archives.json') -Encoding utf8
    Write-Output "$($pair[0]) : identical=$valid; deleted=$($result.deleted); bytes=$length"
}
$caches = @()
foreach ($relative in @('__pycache__', '.ruff_cache', 'lanceur\__pycache__', 'client-qwen\__pycache__', 'client-voice\__pycache__')) {
    $target = Assert-ProjectPath (Join-Path $projectRoot $relative)
    if (-not (Test-Path -LiteralPath $target)) { continue }
    $items = @(Get-ChildItem -LiteralPath $target -Recurse -Force)
    if (($items | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) { throw "Lien dans le cache : $target" }
    $tracked = @(git -C $projectRoot ls-files -- $relative)
    if ($tracked.Count) { throw "Cache suivi par Git : $relative" }
    $bytes = ($items | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum
    Remove-Item -LiteralPath $target -Recurse -Force
    $caches += [pscustomobject]@{path=$target;bytes=$bytes;deleted=$true}
}
$caches | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'caches.json') -Encoding utf8
Write-Output "Caches supprimes : $($caches.Count)"
