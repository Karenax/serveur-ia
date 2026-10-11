param([string]$DistributionDirectory, [switch]$SkipManifest, [string]$WireGuardBinary)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (!$DistributionDirectory) { $DistributionDirectory = Join-Path $PSScriptRoot 'dist' }
$DistributionDirectory = [System.IO.Path]::GetFullPath($DistributionDirectory)
$python = Join-Path $root 'Strata-src\.venv\Scripts\python.exe'
$env:PYTHONPATH = Join-Path $PSScriptRoot 'build-tools'
if (!$WireGuardBinary) { $WireGuardBinary = Join-Path $PSScriptRoot 'wireguard-bridge.exe' }
if ([System.IO.Path]::GetFileName($WireGuardBinary) -ne 'wireguard-bridge.exe') { throw 'Le moteur embarqué doit se nommer wireguard-bridge.exe.' }
if (!(Test-Path -LiteralPath $WireGuardBinary)) { throw 'Compiler le moteur WireGuard avec Build-WireGuard.ps1.' }
& $python (Join-Path $PSScriptRoot 'generate_version.py')
if ($LASTEXITCODE -ne 0) { throw 'Metadata du produit invalide.' }
& $python (Join-Path $PSScriptRoot 'generate_icon.py')
if ($LASTEXITCODE -ne 0) { throw 'Icone du produit invalide.' }
& (Join-Path $root 'client-voice\Build-Voice.cmd')
if ($LASTEXITCODE -ne 0) { throw 'Compilation du moteur vocal impossible.' }
& (Join-Path $root 'client-voice\Prepare-Windows.ps1')
& (Join-Path $root 'client-voice\Build-Conversation.ps1')
& (Join-Path $root 'client-voice\Prepare-Windows.ps1')
$voiceData = (Join-Path $PSScriptRoot 'voice') + ';voice'
$voiceJsData = (Join-Path $PSScriptRoot 'voice.js') + ';.'
$conversationJsData = (Join-Path $PSScriptRoot 'conversation.js') + ';.'
$workspaceData = (Join-Path $PSScriptRoot 'workspace.html') + ';.'
$uiCssData = (Join-Path $PSScriptRoot 'ui.css') + ';.'
$uiJsData = (Join-Path $PSScriptRoot 'ui.js') + ';.'
$attachmentsData = (Join-Path $PSScriptRoot 'attachments.js') + ';.'
$selectionData = (Join-Path $PSScriptRoot 'selection.js') + ';.'
$thinkingData = (Join-Path $PSScriptRoot 'thinking.js') + ';.'
$markdownData = (Join-Path $PSScriptRoot 'markdown.js') + ';.'
$correctorData = (Join-Path $PSScriptRoot 'corrector.js') + ';.'
$markdownVendor = (Join-Path $PSScriptRoot 'vendor') + ';vendor'
& $python -m PyInstaller --noconfirm --onefile --windowed --collect-all webview --collect-all pythonnet --collect-all clr_loader --name "Accès serveur Fred" --icon (Join-Path $PSScriptRoot "fred.ico") --version-file (Join-Path $PSScriptRoot "product-version.txt") --add-data $voiceData --add-data $voiceJsData --add-data $conversationJsData --add-data $workspaceData --add-data $uiCssData --add-data $uiJsData --add-data $attachmentsData --add-data $selectionData --add-data $thinkingData --add-data $markdownData --add-data $correctorData --add-data $markdownVendor --add-data ((Join-Path $PSScriptRoot 'chat.html') + ';.') --add-data ((Join-Path $PSScriptRoot 'LICENSE.txt') + ';.') --add-data ((Join-Path $PSScriptRoot 'THIRD-PARTY.txt') + ';.') --add-binary ($WireGuardBinary + ';.') --distpath $DistributionDirectory --workpath (Join-Path $PSScriptRoot 'build') --specpath $PSScriptRoot (Join-Path $PSScriptRoot 'client.py')
if ($LASTEXITCODE -ne 0) { throw 'La compilation du client a echoue.' }
if (!$SkipManifest) {
    if ($DistributionDirectory -ne [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'dist'))) { throw 'La signature du manifeste nécessite le dossier de distribution par défaut ; utiliser -SkipManifest pour une compilation isolée.' }
    & $python (Join-Path $root 'lanceur\releases.py')
    if ($LASTEXITCODE -ne 0) { throw 'La creation du manifeste de version a echoue.' }
}
