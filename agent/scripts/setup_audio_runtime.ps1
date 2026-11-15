param([ValidateSet('base', 'small', 'medium', 'large-v3-turbo')][string]$Model = 'small')
$ErrorActionPreference = 'Stop'
$taskRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$speechRoot = Join-Path $taskRoot '.venv-speech'
$speechPython = Join-Path $speechRoot 'Scripts\python.exe'
$modelsDirectory = Join-Path $taskRoot $(if ($Model -eq 'small') { '.models\audio' } else { ".models\audio-$Model" })
if (-not (Test-Path -LiteralPath $speechPython)) {
    & python -m venv $speechRoot
    if ($LASTEXITCODE -ne 0) { throw 'Creation du runtime audio isole impossible' }
}
& $speechPython -m pip install -r (Join-Path $taskRoot 'requirements-audio.txt')
if ($LASTEXITCODE -ne 0) { throw 'Installation des dependances audio impossible' }
& $speechPython (Join-Path $taskRoot 'scripts\setup_meeting_audio.py') --directory $modelsDirectory --model $Model
if ($LASTEXITCODE -ne 0) { throw 'Installation des modeles audio impossible' }
# Enumeration only. No microphone or loopback stream is opened by this step.
if ($env:OS -eq 'Windows_NT') {
    & $speechPython (Join-Path $taskRoot 'scripts\native_audio_capture.py') --inventory
    if ($LASTEXITCODE -ne 0) { throw 'Runtime installe, mais inventaire WASAPI indisponible' }
}
Write-Output 'Runtime installe. La capture, la transcription et leur qualite restent a qualifier.'
Write-Output "Modele conserve dans $modelsDirectory (activer explicitement PB_SPEECH_MODELS_DIR pour un profil alternatif)."
