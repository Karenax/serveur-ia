param(
    [Parameter(Mandatory)][string]$Relay,
    [Parameter(Mandatory)][string]$TauriCli,
    [string]$AgentCapture,
    [string]$ToolsRoot = (Join-Path (Split-Path $PSScriptRoot -Parent) 'toolchain'),
    [string]$WorkRoot = (Join-Path (Split-Path $PSScriptRoot -Parent) 'toolchain\tauri-work'),
    [string]$Version,
    [string]$SigningTool,
    [string[]]$SigningArguments = @(),
    [string]$SignerThumbprint
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$relayFile = Get-Item -LiteralPath $Relay
$cli = (Get-Item -LiteralPath $TauriCli).FullName
if ($relayFile.Name -ne 'kiara-relay.exe' -or $relayFile.PSIsContainer) {
    throw 'Choisir le fichier kiara-relay.exe produit par Build-Client.ps1.'
}
$signed = [bool]$SigningTool
$distribution = [bool]$Version
if ($distribution -and $Version -cnotmatch '^(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})$') {
    throw 'La version Windows doit avoir trois composantes numériques.'
}
if ($distribution -and !$AgentCapture) {
    throw 'Fournir AgentCapture pour installer le composant de capture Windows.'
}
if ($signed -or $SigningArguments.Count -or $SignerThumbprint) {
    if (!$signed -or $SignerThumbprint -notmatch '^[a-fA-F0-9]{40}$' -or !$distribution) {
        throw 'Pour une livraison signée, fournir Version, SigningTool, SignerThumbprint et AgentCapture.'
    }
    $tool = Get-Item -LiteralPath $SigningTool
    if ($tool.PSIsContainer -or $tool.Extension -ne '.exe' -or @($SigningArguments -match '%1').Count) {
        throw 'Fournir un outil de signature EXE. Le chemin du binaire est ajouté en dernier argument.'
    }
    $signCommand = @{ cmd = $tool.FullName; args = @($SigningArguments) + '%1' }
}

function Assert-Publisher([string]$Path) {
    $signature = Get-AuthenticodeSignature -LiteralPath $Path
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Thumbprint -ne $SignerThumbprint) {
        throw "Signature Authenticode invalide ou éditeur inattendu pour $Path ($($signature.Status))."
    }
}

function Sign-Sidecar([string]$Path) {
    & $tool.FullName @SigningArguments $Path
    if ($LASTEXITCODE -ne 0) { throw "La signature de $Path a échoué." }
    Assert-Publisher $Path
}
function Assert-DesktopSubsystem([string]$Path) {
    $reader = [IO.BinaryReader]::new([IO.File]::OpenRead($Path))
    try {
        $reader.BaseStream.Position = 0x3c
        $optionalHeader = $reader.ReadUInt32() + 24
        $reader.BaseStream.Position = $optionalHeader + 68
        if ($reader.ReadUInt16() -ne 2) {
            throw 'Kiara.exe doit utiliser le sous-système graphique Windows.'
        }
    } finally {
        $reader.Dispose()
    }
}
$cliVersion = & $cli tauri --version
if ($LASTEXITCODE -ne 0 -or $cliVersion -ne 'tauri-cli 2.12.2') {
    throw 'Utiliser Tauri CLI 2.12.2.'
}
. (Join-Path $root 'maintenance\tauri-dev-env.ps1') -ToolsRoot $ToolsRoot -WorkRoot $WorkRoot

$stage = Join-Path $PSScriptRoot 'installer-input'
New-Item -ItemType Directory -Path $stage -Force | Out-Null
$sidecar = Join-Path $stage 'kiara-relay'
$stagedRelay = "$sidecar-x86_64-pc-windows-msvc.exe"
Copy-Item -LiteralPath $relayFile.FullName -Destination $stagedRelay
$externalBinaries = @('installer-input/kiara-relay')
if ($AgentCapture) {
    $captureFile = Get-Item -LiteralPath $AgentCapture
    if ($captureFile.Name -ne 'kiara-agent-capture.exe' -or $captureFile.PSIsContainer) {
        throw 'Choisir le fichier kiara-agent-capture.exe produit par Build-AgentCapture.ps1.'
    }
    $stagedCapture = Join-Path $stage 'kiara-agent-capture-x86_64-pc-windows-msvc.exe'
    Copy-Item -LiteralPath $captureFile.FullName -Destination $stagedCapture
    $externalBinaries += 'installer-input/kiara-agent-capture'
}
$config = @{
    bundle = @{
        active = $true
        targets = @('nsis')
        useLocalToolsDir = $true
        externalBin = $externalBinaries
        windows = @{ nsis = @{ installMode = 'currentUser'; languages = @('French'); installerHooks = 'installer-hooks.nsh' } }
    }
}
$buildProfile = @('--debug')
if ($distribution) {
    $config.productName = 'Kiara'
    $config.identifier = 'fr.kiara.desktop'
    $config.mainBinaryName = 'Kiara'
    $config.version = $Version
    $buildProfile = @()
}
if ($signed) {
    Sign-Sidecar $stagedRelay
    Sign-Sidecar $stagedCapture
    $config.bundle.windows.signCommand = $signCommand
}
$configPath = Join-Path $stage 'installer.json'
[IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))

Push-Location $PSScriptRoot
try {
    & $cli tauri build @buildProfile --target x86_64-pc-windows-msvc --bundles nsis --config $configPath --no-binary-patching -- --locked -j 2
    if ($LASTEXITCODE -ne 0) { throw "La compilation de l’installateur Kiara a échoué." }
    if ($distribution) {
        $release = Join-Path $env:CARGO_TARGET_DIR 'x86_64-pc-windows-msvc\release'
        $installer = Join-Path $release "bundle\nsis\Kiara_${Version}_x64-setup.exe"
        Assert-DesktopSubsystem (Join-Path $release 'Kiara.exe')
        if ($signed) {
            Assert-Publisher (Join-Path $release 'Kiara.exe')
            Assert-Publisher $installer
        }
        Get-FileHash -LiteralPath $installer -Algorithm SHA256
    }
} finally {
    Pop-Location
}
