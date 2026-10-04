param([switch]$Plan)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (!$Plan) {
    $benchmark = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*Tester-Strata-8coeurs.py*' }
    if ($benchmark) { throw 'Attendre la fin du comparatif CPU avant cette copie de 71,7 Gio.' }
}
$python = Join-Path $root 'Strata-src\.venv\Scripts\python.exe'
$script = Join-Path $root 'Preparer-Cache-Q4.py'
if ($Plan) { & $python $script --plan } else { & $python $script }
if ($LASTEXITCODE -ne 0) { throw "La préparation a échoué (code $LASTEXITCODE)." }
