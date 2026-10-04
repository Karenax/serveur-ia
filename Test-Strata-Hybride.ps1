param([switch]$Comparatif, [ValidateRange(1,10)][int]$Repetitions = 2)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$enginePath = Join-Path $root 'strata-build-p100\strata.exe'
$engine = Get-CimInstance Win32_Process -Filter "Name='strata.exe'" | Where-Object {
    $_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -eq $enginePath
} | Select-Object -First 1
if (!$engine) { throw 'Le moteur Strata P100 est absent.' }
if (Test-Path -LiteralPath (Join-Path $root 'strata-data\cuda-debug.flag')) {
    throw 'Attendre la fin du chargement et de la preparation CUDA.'
}
$python = Join-Path $root 'Strata-src\.venv\Scripts\python.exe'
$script = Join-Path $root 'Test-Strata-Hybride.py'
if ($Comparatif) {
    & $python $script --pid $engine.ProcessId --repeats $Repetitions
} else {
    & $python $script --pid $engine.ProcessId --fractions 0 --repeats $Repetitions --sans-override
}
if ($LASTEXITCODE) { throw "Le comparatif échoue, code $LASTEXITCODE ; les fichiers bruts sont conservés." }
