param([switch]$SansMTP, [ValidateRange(1,16)][int]$Parallel = 1,
      [ValidateRange(512,262144)][int]$Context = 4096)
$ErrorActionPreference = 'Stop'
if ($SansMTP) {
 & (Join-Path $PSScriptRoot 'Start-Qwen-GPU.ps1') -Parallel $Parallel -Context $Context
} else {
 & (Join-Path $PSScriptRoot 'Start-Qwen-GPU.ps1') -MTP -Parallel $Parallel -Context $Context
}
