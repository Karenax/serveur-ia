param()
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root 'Strata-src\.venv\Scripts\python.exe'
$env:PYTHONPATH = Join-Path $PSScriptRoot 'build-tools'
if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'wireguard-bridge.exe'))) { throw 'Compiler le moteur WireGuard avec Build-WireGuard.ps1.' }
& $python (Join-Path $PSScriptRoot 'generate_version.py')
if ($LASTEXITCODE -ne 0) { throw 'Metadata du produit invalide.' }
& $python (Join-Path $PSScriptRoot 'generate_icon.py')
if ($LASTEXITCODE -ne 0) { throw 'Icone du produit invalide.' }
$workspaceData = (Join-Path $PSScriptRoot 'workspace.html') + ';.'
$uiCssData = (Join-Path $PSScriptRoot 'ui.css') + ';.'
$uiJsData = (Join-Path $PSScriptRoot 'ui.js') + ';.'
$attachmentsData = (Join-Path $PSScriptRoot 'attachments.js') + ';.'
$selectionData = (Join-Path $PSScriptRoot 'selection.js') + ';.'
$thinkingData = (Join-Path $PSScriptRoot 'thinking.js') + ';.'
$markdownData = (Join-Path $PSScriptRoot 'markdown.js') + ';.'
$correctorData = (Join-Path $PSScriptRoot 'corrector.js') + ';.'
$markdownVendor = (Join-Path $PSScriptRoot 'vendor') + ';vendor'
& $python -m PyInstaller --noconfirm --onefile --windowed --collect-all webview --collect-all pythonnet --collect-all clr_loader --name "Accès serveur Fred" --icon (Join-Path $PSScriptRoot "fred.ico") --version-file (Join-Path $PSScriptRoot "product-version.txt") --add-data $workspaceData --add-data $uiCssData --add-data $uiJsData --add-data $attachmentsData --add-data $selectionData --add-data $thinkingData --add-data $markdownData --add-data $correctorData --add-data $markdownVendor --add-data ((Join-Path $PSScriptRoot 'chat.html') + ';.') --add-data ((Join-Path $PSScriptRoot 'LICENSE.txt') + ';.') --add-data ((Join-Path $PSScriptRoot 'THIRD-PARTY.txt') + ';.') --add-binary ((Join-Path $PSScriptRoot 'wireguard-bridge.exe') + ';.') --distpath (Join-Path $PSScriptRoot 'dist') --workpath (Join-Path $PSScriptRoot 'build') --specpath $PSScriptRoot (Join-Path $PSScriptRoot 'client.py')
if ($LASTEXITCODE -ne 0) { throw 'La compilation du client a echoue.' }
& $python (Join-Path $root 'lanceur\releases.py')
if ($LASTEXITCODE -ne 0) { throw 'La creation du manifeste de version a echoue.' }
