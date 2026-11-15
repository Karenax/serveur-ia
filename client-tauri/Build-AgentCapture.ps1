param(
    [Parameter(Mandatory)][string]$Python,
    [Parameter(Mandatory)][string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$agent = Join-Path $root 'agent'
$pythonExe = (Get-Item -LiteralPath $Python).FullName
$output = [IO.Path]::GetFullPath($OutputDirectory)
$entrypoint = Join-Path $agent 'scripts\native_audio_capture.py'
$env:PYTHONPATH = $agent

& $pythonExe -m PyInstaller --noconfirm --onefile --console --name kiara-agent-capture `
    --paths $agent --copy-metadata PyAudioWPatch --collect-all av `
    --distpath $output --workpath (Join-Path $output 'build') --specpath $output $entrypoint
if ($LASTEXITCODE -ne 0) { throw 'Compilation du helper WASAPI échouée.' }

$exe = Join-Path $output 'kiara-agent-capture.exe'
$inventory = & $exe --inventory
if ($LASTEXITCODE -ne 0) { throw 'Inventaire WASAPI indisponible.' }
$devices = ($inventory | ConvertFrom-Json)
if (!$devices.installed) { throw 'WASAPI absent du helper compilé.' }
Write-Output $exe
