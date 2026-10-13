$ErrorActionPreference = 'Stop'
$eg2Root = $PSScriptRoot
$eg2BasePython = Join-Path $eg2Root 'Strata-src\.venv\Scripts\python.exe'
$eg2Env = Join-Path $eg2Root 'toolchain\eg2-python'
$eg2Python = Join-Path $eg2Env 'Scripts\python.exe'
if (!(Test-Path -LiteralPath $eg2Python)) {
    & $eg2BasePython -m venv $eg2Env
    if ($LASTEXITCODE -ne 0) { throw "Création de l'environnement EG2 impossible." }
}
& $eg2Python -m pip install -r (Join-Path $eg2Root 'lanceur\requirements-eg2.txt')
if ($LASTEXITCODE -ne 0) { throw 'Installation des dépendances EG2 impossible.' }
$env:HF_HUB_DISABLE_TELEMETRY = '1'
& $eg2Python (Join-Path $eg2Root 'lanceur\install_eg2.py')
if ($LASTEXITCODE -ne 0) { throw 'Téléchargement du modèle EG2 impossible.' }
Write-Output 'Installation terminée. Activer EG2 dans la console, rubrique Mémoire et connaissances.'
