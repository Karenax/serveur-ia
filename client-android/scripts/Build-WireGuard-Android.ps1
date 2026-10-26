param([switch]$Force)
$ErrorActionPreference = 'Stop'
$projetAndroid = Split-Path $PSScriptRoot -Parent
$projetRacine = Split-Path $projetAndroid -Parent
. (Join-Path $projetRacine 'client-qwen\android-outils\Environnement-Android.ps1')
$versionGo = Get-Content -LiteralPath (Join-Path $projetRacine 'client-qwen/wireguard-toolchain.json') -Raw | ConvertFrom-Json
$goAndroid = Join-Path $projetRacine ('client-qwen/wireguard-tools/versions/' + $versionGo.version + '/go/bin/go.exe')
if (!(Test-Path -LiteralPath $goAndroid)) { throw 'Préparer le Go épinglé avec maintenance/prepare_go.py.' }
$versionGoReelle = (& $goAndroid version)
if ($LASTEXITCODE -ne 0 -or $versionGoReelle -notmatch [regex]::Escape($versionGo.version)) { throw 'Version Go Android inattendue.' }
$sourcesBridge = Join-Path $projetRacine 'client-qwen\wireguard-bridge'
$travailBridge = Join-Path $projetRacine 'toolchain\android-wireguard-build'
New-Item -ItemType Directory -Force -Path $travailBridge | Out-Null
foreach ($sourceBridge in @('main.go','go.mod','go.sum')) {
    Copy-Item -LiteralPath (Join-Path $sourcesBridge $sourceBridge) -Destination (Join-Path $travailBridge $sourceBridge) -Force
}
$clangAndroid = Join-Path $env:ANDROID_HOME 'ndk\27.3.13750724\toolchains\llvm\prebuilt\windows-x86_64\bin\clang.exe'
$empreinteSources = ((@('main.go','go.mod','go.sum') | ForEach-Object { (Get-FileHash -LiteralPath (Join-Path $travailBridge $_)).Hash }) -join '-') + '-go' + $versionGo.version + '-ndk27-api26-pie-16k-v1'
$variablesGoAvant = @{}
foreach ($nomGo in @('GOOS','GOARCH','CGO_ENABLED','CC','GOPATH','GOCACHE','GOMAXPROCS','CGO_LDFLAGS','GOTOOLCHAIN')) { $variablesGoAvant[$nomGo] = [Environment]::GetEnvironmentVariable($nomGo,'Process') }
Push-Location $travailBridge
try {
    $env:GOOS = 'android'
    $env:CGO_ENABLED = '1'
    $env:GOMAXPROCS = '2'
    $env:GOPATH = Join-Path $projetRacine 'client-qwen\wireguard-tools\workspace'
    $env:GOCACHE = Join-Path $projetRacine 'toolchain\android-go-cache'
    $env:GOTOOLCHAIN = 'local'
    $env:CGO_LDFLAGS = '-Wl,-z,max-page-size=16384'
    & $goAndroid mod verify
    if ($LASTEXITCODE -ne 0) { throw 'Dependencies WireGuard invalides.' }
    foreach ($cibleGo in @(
        @{Abi='arm64-v8a'; Arch='arm64'; Target='aarch64-linux-android26'},
        @{Abi='x86_64'; Arch='amd64'; Target='x86_64-linux-android26'}
    )) {
        $env:GOARCH = $cibleGo.Arch
        $env:CC = '"' + $clangAndroid + '" --target=' + $cibleGo.Target
        $repertoireAbi = Join-Path $projetAndroid ('app\src\main\jniLibs\' + $cibleGo.Abi)
        New-Item -ItemType Directory -Force -Path $repertoireAbi | Out-Null
        $binaireBridge = Join-Path $repertoireAbi 'libfredwireguard.so'
        $marqueurBridge = Join-Path $travailBridge ($cibleGo.Abi + '.sources.sha256')
        if (!$Force -and (Test-Path -LiteralPath $binaireBridge) -and (Test-Path -LiteralPath $marqueurBridge) -and (Get-Content -LiteralPath $marqueurBridge -Raw).Trim() -eq $empreinteSources) { continue }
        Write-Host ('Compilation WireGuard Android : ' + $cibleGo.Abi)
        & $goAndroid build -p 2 -trimpath -buildmode=pie -ldflags '-s -w' -o $binaireBridge .
        if ($LASTEXITCODE -ne 0) { throw ('Compilation WireGuard Android echouee : ' + $cibleGo.Abi) }
        $empreinteSources | Set-Content -LiteralPath $marqueurBridge -Encoding ascii
    }
} finally {
    Pop-Location
    foreach ($nomGo in $variablesGoAvant.Keys) { [Environment]::SetEnvironmentVariable($nomGo,$variablesGoAvant[$nomGo],'Process') }
}
