param([string]$CredentialPath = (Join-Path $PSScriptRoot 'kiara-api-key.dpapi'))
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security
$encrypted = [IO.File]::ReadAllBytes($CredentialPath)
$plain = [Security.Cryptography.ProtectedData]::Unprotect($encrypted, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
try { [Console]::Out.Write([Text.Encoding]::UTF8.GetString($plain)) }
finally { [Array]::Clear($plain, 0, $plain.Length) }
