param([switch]$SansMTP)
$ErrorActionPreference = 'Stop'
if ($SansMTP) {
 & (Join-Path $PSScriptRoot 'Start-Qwen-GPU.ps1')
} else {
 & (Join-Path $PSScriptRoot 'Start-Qwen-GPU.ps1') -MTP
}
