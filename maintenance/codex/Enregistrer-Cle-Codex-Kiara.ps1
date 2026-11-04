param([string]$CodexDirectory = (Join-Path $env:USERPROFILE '.codex'))
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security
$pointer = [IntPtr]::Zero
try {
    if ($env:KIARA_API_KEY) { $value = $env:KIARA_API_KEY }
    else {
        $secret = Read-Host 'Clé API personnelle Kiara (stockage chiffré pour ce compte Windows)' -AsSecureString
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
        $value = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    if ($value -notmatch '^qwen_[0-9a-f]{16}_[A-Za-z0-9_-]{43}$') { throw 'Clé API Kiara invalide.' }
    $plain = [Text.Encoding]::UTF8.GetBytes($value)
    try {
        $encrypted = [Security.Cryptography.ProtectedData]::Protect($plain, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
        New-Item -ItemType Directory -Path $CodexDirectory -Force | Out-Null
        [IO.File]::WriteAllBytes((Join-Path $CodexDirectory 'kiara-api-key.dpapi'), $encrypted)
    } finally { [Array]::Clear($plain, 0, $plain.Length); $value = $null }
} finally {
    if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer); $secret.Dispose() }
}
Write-Output 'Clé Kiara chiffrée pour ce compte Windows.'
