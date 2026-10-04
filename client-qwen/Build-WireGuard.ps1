param()
$ErrorActionPreference='Stop'
$env:GOMAXPROCS='2'
$env:GOPATH=Join-Path $PSScriptRoot 'wireguard-tools\workspace'
$env:GOCACHE=Join-Path $PSScriptRoot 'wireguard-tools\cache'
$go=Join-Path $PSScriptRoot 'wireguard-tools\go\bin\go.exe'
if (!(Test-Path -LiteralPath $go)) { $go=(Get-Command go).Source }
Push-Location (Join-Path $PSScriptRoot 'wireguard-bridge')
try {
    & $go mod verify
    if ($LASTEXITCODE -ne 0) { throw 'Vérification des dépendances WireGuard échouée.' }
    & $go build -p 2 -trimpath -ldflags '-s -w' -o (Join-Path $PSScriptRoot 'wireguard-bridge.exe') .
    if ($LASTEXITCODE -ne 0) { throw 'Compilation WireGuard échouée.' }
} finally { Pop-Location }
