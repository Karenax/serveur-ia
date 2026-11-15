param(
    [string]$ToolsRoot = (Join-Path (Split-Path $PSScriptRoot -Parent) 'toolchain'),
    [string]$WorkRoot = (Join-Path (Split-Path $PSScriptRoot -Parent) 'toolchain\tauri-work')
)

$ErrorActionPreference = 'Stop'
$toolchain = $ToolsRoot
if (-not (Test-Path -LiteralPath (Join-Path $toolchain 'MSVC') -PathType Container)) {
    $toolchain = Join-Path $ToolsRoot 'Toolchain'
}
$vc = Join-Path $toolchain 'MSVC\VC\Tools\MSVC\14.44.35207'
$kit = Join-Path $toolchain 'MSVC\Windows Kits\10'
$sdk = '10.0.22621.0'
foreach ($required in @((Join-Path $vc 'bin\Hostx64\x64\link.exe'),
                         (Join-Path $kit "Lib\$sdk\um\x64\kernel32.lib"),
                         (Join-Path $kit "bin\$sdk\x64\rc.exe"))) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Outil de compilation absent : $required" }
}
$env:TEMP = Join-Path $WorkRoot 'Temp'
$env:TMP = $env:TEMP
$env:CARGO_HOME = Join-Path $WorkRoot 'Cache\cargo'
$rust = Join-Path $toolchain 'Rust'
if (Test-Path -LiteralPath (Join-Path $rust 'cargo\bin\cargo.exe')) {
    $env:RUSTUP_HOME = Join-Path $rust 'rustup'
    $env:PATH = "$(Join-Path $rust 'cargo\bin');$env:PATH"
}
$env:CARGO_TARGET_DIR = Join-Path $WorkRoot 'Build\tauri-prototype'
$env:npm_config_cache = Join-Path $WorkRoot 'Cache\npm'
foreach ($directory in @($env:TEMP, $env:CARGO_HOME, $env:CARGO_TARGET_DIR, $env:npm_config_cache)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
$env:PATH = "$vc\bin\Hostx64\x64;$kit\bin\$sdk\x64;$env:PATH"
$env:LIB = "$vc\lib\x64;$kit\Lib\$sdk\ucrt\x64;$kit\Lib\$sdk\um\x64"
$env:INCLUDE = "$vc\include;$kit\Include\$sdk\ucrt;$kit\Include\$sdk\shared;$kit\Include\$sdk\um;$kit\Include\$sdk\winrt"
