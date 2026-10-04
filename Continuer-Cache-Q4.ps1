$ErrorActionPreference = 'Stop'
$archive = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'comparatif-cpu8-courant.txt') -Raw).Trim()
$statePath = Join-Path $archive 'etat-cache-ssd.json'
try {
    @{status='running';started=(Get-Date -Format o);launcher_pid=$PID} | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
    & (Join-Path $PSScriptRoot 'Strata-src\.venv\Scripts\python.exe') -u (Join-Path $PSScriptRoot 'Preparer-Cache-Q4.py') 1> (Join-Path $archive 'preparation-cache-ssd-reprise.stdout.log') 2> (Join-Path $archive 'preparation-cache-ssd-reprise.stderr.log')
    if ($LASTEXITCODE -ne 0) { throw "Conversion interrompue (code $LASTEXITCODE)." }
    @{status='complete';finished=(Get-Date -Format o);launcher_pid=$PID} | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
} catch {
    @{status='failed';finished=(Get-Date -Format o);error=$_.Exception.Message;launcher_pid=$PID} | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
    exit 1
}
