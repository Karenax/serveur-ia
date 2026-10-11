function Resolve-FredPython {
    param([string]$Requested, [string]$ProjectRoot)
    $candidates = @()
    if ($Requested) {
        $candidates += $Requested
    } else {
        $candidates += Join-Path $ProjectRoot 'Strata-src\.venv\Scripts\python.exe'
        $candidates += Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
        $command = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notmatch '\\Microsoft\\WindowsApps\\') {
            $candidates += $command.Source
        }
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            & $candidate -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { return (Resolve-Path -LiteralPath $candidate).Path }
        }
    }
    throw 'Python 3.10+ absent. Indiquer son chemin avec -Python.'
}
