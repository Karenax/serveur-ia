param([string]$DistributionDirectory, [switch]$SkipManifest, [string]$WireGuardBinary, [switch]$Relay, [switch]$UsePreparedVoice)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (!$DistributionDirectory) { $DistributionDirectory = Join-Path $PSScriptRoot 'dist' }
$DistributionDirectory = [System.IO.Path]::GetFullPath($DistributionDirectory)
if ($Relay -and !$SkipManifest) { throw 'Le relais Tauri nécessite -SkipManifest.' }
$binaryName = if ($Relay) { 'kiara-relay' } else { 'Accès serveur Fred' }
$consoleMode = if ($Relay) { '--console' } else { '--windowed' }
$python = Join-Path $root 'toolchain\build-python\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Préparer le constructeur isolé avec maintenance/prepare_build_environment.py.' }
& $python (Join-Path $root 'maintenance/2026-10-25-assistant-integration/prepare_wakeword.py')
if ($LASTEXITCODE -ne 0) { throw 'Préparer les ressources vocales avec prepare_wakeword.py --download.' }
$env:PYTHONPATH = Join-Path $root 'shared'
if (!$WireGuardBinary) { $WireGuardBinary = Join-Path $PSScriptRoot 'wireguard-bridge.exe' }
if ([System.IO.Path]::GetFileName($WireGuardBinary) -ne 'wireguard-bridge.exe') { throw 'Le moteur embarqué doit se nommer wireguard-bridge.exe.' }
if (!(Test-Path -LiteralPath $WireGuardBinary)) { throw 'Compiler le moteur WireGuard avec Build-WireGuard.ps1.' }
& $python (Join-Path $PSScriptRoot 'generate_version.py')
if ($LASTEXITCODE -ne 0) { throw 'Metadata du produit invalide.' }
& $python (Join-Path $PSScriptRoot 'generate_icon.py')
if ($LASTEXITCODE -ne 0) { throw 'Icone du produit invalide.' }
if (!$Relay -and !$UsePreparedVoice) {
    & (Join-Path $root 'client-voice\Build-Voice.cmd')
    if ($LASTEXITCODE -ne 0) { throw 'Compilation du moteur vocal impossible.' }
    & (Join-Path $root 'client-voice\Prepare-Windows.ps1')
    & (Join-Path $root 'client-voice\Build-Conversation.ps1')
    & (Join-Path $root 'client-voice\Prepare-Windows.ps1')
} elseif (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'voice\native-manifest.json'))) {
    throw 'Préparer les ressources vocales Windows avant de compiler Kiara.'
}
$voiceData = (Join-Path $PSScriptRoot 'voice') + ';voice'
$voiceJsData = (Join-Path $PSScriptRoot 'voice.js') + ';.'
$conversationJsData = (Join-Path $PSScriptRoot 'conversation.js') + ';.'
$workspaceData = (Join-Path $PSScriptRoot 'workspace.html') + ';.'
$uiCssData = (Join-Path $PSScriptRoot 'ui.css') + ';.'
$uiJsData = (Join-Path $PSScriptRoot 'ui.js') + ';.'
$projectConversationData = (Join-Path $PSScriptRoot 'project-conversation.js') + ';.'
$attachmentsData = (Join-Path $PSScriptRoot 'attachments.js') + ';.'
$selectionData = (Join-Path $PSScriptRoot 'selection.js') + ';.'
$thinkingData = (Join-Path $PSScriptRoot 'thinking.js') + ';.'
$markdownData = (Join-Path $PSScriptRoot 'markdown.js') + ';.'
$correctorData = (Join-Path $PSScriptRoot 'corrector.js') + ';.'
$markdownVendor = (Join-Path $PSScriptRoot 'vendor') + ';vendor'
$tlsData = @()
$rejectedCas = & $python -c 'import pathlib, ssl; print(pathlib.Path(ssl.__file__).with_name("codex-rejected-cas.pem"))'
if ($LASTEXITCODE -ne 0) { throw 'Vérification du module TLS Python impossible.' }
if (Test-Path -LiteralPath $rejectedCas -PathType Leaf) { $tlsData = @('--add-data', "$rejectedCas;.") }
if ($Relay) {
    $previousBridge = $env:KIARA_BUILD_WIREGUARD
    try {
        $env:KIARA_BUILD_WIREGUARD = (Get-Item -LiteralPath $WireGuardBinary).FullName
        & $python -m PyInstaller --noconfirm --distpath $DistributionDirectory --workpath (Join-Path $DistributionDirectory 'build') (Join-Path $PSScriptRoot 'kiara-relay.spec')
    } finally { $env:KIARA_BUILD_WIREGUARD = $previousBridge }
} else {
    & $python -m PyInstaller --noconfirm --onefile $consoleMode --paths (Join-Path $root 'shared') --collect-all kiara_shared --collect-all webview --collect-all pythonnet --collect-all clr_loader --name $binaryName --icon (Join-Path $PSScriptRoot "fred.ico") --version-file (Join-Path $PSScriptRoot "product-version.txt") --add-data $voiceData --add-data $voiceJsData --add-data $conversationJsData --add-data $workspaceData --add-data $uiCssData --add-data $uiJsData --add-data $projectConversationData --add-data $attachmentsData --add-data $selectionData --add-data $thinkingData --add-data $markdownData --add-data $correctorData --add-data $markdownVendor --add-data ((Join-Path $PSScriptRoot 'chat.html') + ';.') --add-data ((Join-Path $PSScriptRoot 'LICENSE.txt') + ';.') --add-data ((Join-Path $PSScriptRoot 'THIRD-PARTY.txt') + ';.') --add-binary ($WireGuardBinary + ';.') @tlsData --distpath $DistributionDirectory --workpath (Join-Path $PSScriptRoot 'build') --specpath $PSScriptRoot (Join-Path $PSScriptRoot 'client.py')
}
if ($LASTEXITCODE -ne 0) { throw 'La compilation du client a echoue.' }
& $python (Join-Path $root 'maintenance/check_windows_artifact.py') --artifact (Join-Path $DistributionDirectory ("$binaryName.exe")) --result (Join-Path $DistributionDirectory 'self-test.txt')
if ($LASTEXITCODE -ne 0) { throw 'Le client construit ne passe pas sa vérification native.' }
& $python (Join-Path $root 'maintenance\build_manifest.py') --component windows --artifact (Join-Path $DistributionDirectory ("$binaryName.exe")) --output (Join-Path $DistributionDirectory 'build-manifest.json')
if ($LASTEXITCODE -ne 0) { throw 'Inventaire de compilation Windows impossible.' }
if (!$SkipManifest) {
    if ($DistributionDirectory -ne [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'dist'))) { throw 'La signature du manifeste nécessite le dossier de distribution par défaut ; utiliser -SkipManifest pour une compilation isolée.' }
    & $python (Join-Path $root 'lanceur\releases.py')
    if ($LASTEXITCODE -ne 0) { throw 'La creation du manifeste de version a echoue.' }
}
