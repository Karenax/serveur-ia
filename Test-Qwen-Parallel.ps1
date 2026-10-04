# Validate the launch arguments without starting a model or changing PID files.
$ErrorActionPreference = 'Stop'
function Get-NetTCPConnection { param($State, $LocalPort) }
function Start-Process {
    param($FilePath, $ArgumentList, $WorkingDirectory, $WindowStyle,
          $RedirectStandardOutput, $RedirectStandardError, [switch]$PassThru)
    $global:qwenParallelTestArgs = $ArgumentList
    [pscustomobject]@{Id = 12345}
}
function Set-Content { param($Path) process {} }
function Assert-Argument($Name, $Value) {
    $index = [array]::IndexOf($global:qwenParallelTestArgs, $Name)
    if ($index -lt 0 -or $global:qwenParallelTestArgs[$index + 1] -ne $Value) {
        throw "Argument incorrect : $Name $Value"
    }
}
& (Join-Path $PSScriptRoot 'Start-Qwen.ps1') -SansMTP -Parallel 2 -Context 8192
Assert-Argument '-np' '2'
Assert-Argument '-c' '8192'
if ('--cont-batching' -notin $global:qwenParallelTestArgs) { throw 'Batching absent' }
if ('--spec-type' -in $global:qwenParallelTestArgs) { throw 'MTP actif malgré SansMTP' }
& (Join-Path $PSScriptRoot 'Start-Qwen.ps1')
Assert-Argument '-np' '1'
Assert-Argument '-c' '4096'
Assert-Argument '--spec-type' 'draft-mtp'
Remove-Variable -Name qwenParallelTestArgs -Scope Global
'PASS : deux conversations, contexte total, batching, défauts et MTP.'
