param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CodexArguments)
$ErrorActionPreference = 'Stop'
$profile = Join-Path $env:USERPROFILE '.codex\kiara.config.toml'
if (!(Test-Path -LiteralPath $profile)) { & (Join-Path $PSScriptRoot 'Installer-Codex-Kiara.ps1') }
$previousKey = $env:KIARA_API_KEY
try {
    $usesHelper = ([IO.File]::ReadAllText($profile)) -match '\[model_providers\.kiara\.auth\]'
    if (!$env:KIARA_API_KEY -and !$usesHelper) {
        $secret = Read-Host 'Clé API personnelle Kiara' -AsSecureString
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
        try { $env:KIARA_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer); $secret.Dispose() }
    }
    & codex --profile kiara @CodexArguments
    $result = $LASTEXITCODE
} finally { $env:KIARA_API_KEY = $previousKey }
exit $result
