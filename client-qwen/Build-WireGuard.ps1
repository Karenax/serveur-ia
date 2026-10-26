param([string]$OutputBinary)
$ErrorActionPreference='Stop'
$env:GOMAXPROCS='2'
$env:GOPATH=Join-Path $PSScriptRoot 'wireguard-tools\workspace'
$env:GOCACHE=Join-Path $PSScriptRoot 'wireguard-tools\cache'
$spec=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'wireguard-toolchain.json') -Raw | ConvertFrom-Json
if ($spec.version -notmatch '^go1\.\d+\.\d+$') { throw 'Version Go épinglée invalide.' }
$go=Join-Path $PSScriptRoot ('wireguard-tools\versions\'+$spec.version+'\go\bin\go.exe')
if (!(Test-Path -LiteralPath $go)) { throw 'Préparer Go avec maintenance/prepare_go.py.' }
if (!$OutputBinary) { $OutputBinary=Join-Path $PSScriptRoot 'wireguard-bridge.exe' }
$env:GOTOOLCHAIN='local'
Push-Location (Join-Path $PSScriptRoot 'wireguard-bridge')
try {
    & $go mod verify
    if ($LASTEXITCODE -ne 0) { throw 'Vérification des dépendances WireGuard échouée.' }
    & $go build -p 2 -trimpath -ldflags '-s -w' -o $OutputBinary .
    if ($LASTEXITCODE -ne 0) { throw 'Compilation WireGuard échouée.' }
} finally { Pop-Location }
