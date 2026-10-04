$ErrorActionPreference = 'Stop'
$warmupPath = Join-Path $PSScriptRoot 'strata-warmup.pid'
if (Test-Path -LiteralPath $warmupPath) {
    $warmupPid = [int](Get-Content -LiteralPath $warmupPath)
    $warmupProc = Get-CimInstance Win32_Process -Filter "ProcessId=$warmupPid" -ErrorAction SilentlyContinue
    if ($warmupProc -and $warmupProc.CommandLine -like '*Warmup-Strata-P100.ps1*') {
        Stop-Process -Id $warmupPid -ErrorAction SilentlyContinue
    }
}
$pidPath = Join-Path $PSScriptRoot 'strata-server.pid'
if (Test-Path -LiteralPath $pidPath) {
    $serverPid = [int](Get-Content -LiteralPath $pidPath)
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$serverPid" -ErrorAction SilentlyContinue
    if ($process -and $process.CommandLine -like '*serve.server*' -and
        ($process.CommandLine -like '*strata-q4-p100.json*' -or $process.CommandLine -like '*strata-q4-p100-hybride.json*' -or $process.CommandLine -like '*strata-q4-p100-8coeurs.json*' -or $process.CommandLine -like '*strata-q4-p100-cache.json*' -or $process.CommandLine -like '*strata-q4-p100-cache-8coeurs.json*')) {
        # The Windows venv launcher adds another Python process to the parent chain.
        $children = Get-CimInstance Win32_Process -Filter "Name='strata.exe'" | Where-Object {
            $_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -eq (Join-Path $PSScriptRoot 'strata-build-p100\strata.exe')
        }
        foreach ($child in $children) {
            Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
        }
        Stop-Process -Id $serverPid
        Wait-Process -Id $serverPid -Timeout 30 -ErrorAction SilentlyContinue
        foreach ($child in $children) {
            Wait-Process -Id $child.ProcessId -Timeout 30 -ErrorAction SilentlyContinue
            if (Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue) {
                throw 'Le processus CUDA libère encore sa mémoire ; attendre avant de reconstruire ou redémarrer.'
            }
        }
        Write-Output 'Strata arrêté ; le processus CUDA enfant est contenu dans le même job Windows.'
    }
}
