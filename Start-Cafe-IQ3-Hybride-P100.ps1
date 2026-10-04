param([ValidateRange(0.01,1)][double]$CpuFraction = 1,
      [ValidateRange(512,4096)][int]$ReserveMiB = 1024,
      [ValidateRange(1,16)][int]$CpuThreads = 15)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'Start-Cafe-IQ3-P100.ps1') -MTP -CacheMiB 0 -CpuFraction $CpuFraction -ReserveMiB $ReserveMiB -CpuThreads $CpuThreads
