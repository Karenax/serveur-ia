param([Parameter(Mandatory=$true)][int]$ReaderPid)
$ErrorActionPreference = 'Stop'
$readerInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$ReaderPid"
if (!$readerInfo -or $readerInfo.CommandLine -notlike '*Prelire-Experts-Strata.py*') { throw 'Le PID ne correspond pas au lecteur des experts.' }
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class StrataReadCache {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool SetProcessWorkingSetSize(IntPtr process, IntPtr minimum, IntPtr maximum);
}
'@
$readerProcess = Get-Process -Id $ReaderPid
$readerHandle = $readerProcess.Handle
while (!$readerProcess.HasExited) {
    if (![StrataReadCache]::SetProcessWorkingSetSize($readerHandle, [IntPtr]::new(-1), [IntPtr]::new(-1))) {
        $readerProcess.Refresh()
        if (!$readerProcess.HasExited) { throw "Impossible de libérer le working set : $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }
    }
    Start-Sleep -Seconds 5
    $readerProcess.Refresh()
}
Write-Output 'Lecteur terminé ; surveillance du cache arrêtée.'
