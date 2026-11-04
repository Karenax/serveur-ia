param([Parameter(Mandatory=$true)][string]$RunDirectory)
$ErrorActionPreference = 'Stop'
$run = [IO.Path]::GetFullPath($RunDirectory)
if (!$run.StartsWith('F:\Kiara-tests\installation-58180-', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Unexpected installation report directory.'
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Administrator elevation is required to install the display drivers.'
}
[void][IO.Directory]::CreateDirectory($run)
$state = [ordered]@{phase='preflight';started=(Get-Date).ToString('o');updates=@();reboot_required=$false}
function Save-State {
    $state.updated=(Get-Date).ToString('o')
    $state | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath (Join-Path $run 'state.json') -Encoding UTF8
}
function Cards {
    @(Get-CimInstance Win32_PnPSignedDriver | Where-Object {$_.DeviceClass -eq 'DISPLAY' -and $_.DeviceID -like 'PCI\VEN_10DE*'} |
        Select-Object DeviceName,DeviceID,DriverVersion,InfName)
}
function Get-LocalJson([string]$url) {
    $client = New-Object Net.WebClient
    $client.Proxy=$null
    try { return ($client.DownloadString($url) | ConvertFrom-Json) } finally {$client.Dispose()}
}
function Console-Post([string]$route,[object]$body) {
    $client = New-Object Net.WebClient
    $client.Proxy=$null
    try {
        $html=$client.DownloadString('http://127.0.0.1:8765/')
        $match=[regex]::Match($html,'name="launcher-token" content="([^"]+)"')
        if (!$match.Success) {throw 'Launcher token unavailable.'}
        $client.Headers['X-Launcher-Token']=$match.Groups[1].Value
        $client.Headers['Origin']='http://127.0.0.1:8765'
        $client.Headers['Content-Type']='application/json'
        return ($client.UploadString('http://127.0.0.1:8765'+$route,($body | ConvertTo-Json -Depth 5)) | ConvertFrom-Json)
    } finally {$client.Dispose()}
}
Save-State
Start-Transcript -LiteralPath (Join-Path $run 'installation.log') -Force | Out-Null
try {
    $packages=@(
        @{family='geforce';file='581.80-desktop-win10-win11-64bit-international-dch-whql.exe';sha='0a08462764f4d36eeecb8da6abfc01a6e32c94359b9e1e3287399f057c1d2839'},
        @{family='quadro';file='581.80-quadro-rtx-desktop-notebook-win10-win11-64bit-international-dch-whql.exe';sha='cfe62fb91fe2c258dd0fbe38b3b8941b1c039e4422bf2e08f9ea0e8a577bfa44'}
    )
    foreach ($package in $packages) {
        $folder=Join-Path 'F:\Kiara-tests\pilotes-581.80' $package.family
        $file=Join-Path $folder $package.file
        if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $package.sha) {throw 'Installer hash mismatch.'}
        if ((Get-AuthenticodeSignature -LiteralPath $file).Status -ne 'Valid') {throw 'Invalid NVIDIA installer signature.'}
        $driver=Join-Path $folder 'extracted\Display.Driver'
        if ((Get-FileHash -LiteralPath (Join-Path $driver 'nvlddmkm.sys') -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'f2c2a13c47f4cae5dc91aa245b99a2a7794b5c77be1d12276adc3ae2e55cf9c3') {throw 'Driver payload mismatch.'}
        if ((Get-AuthenticodeSignature -LiteralPath (Join-Path $driver 'nv_disp.cat')).Status -ne 'Valid') {throw 'Invalid driver catalog signature.'}
    }
    $before=Cards
    if ($before.Count -ne 4) {throw 'Expected exactly four NVIDIA display adapters.'}
    $before | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'drivers-before.json') -Encoding UTF8
    $state.phase='backup';Save-State
    foreach ($inf in @($before.InfName | Sort-Object -Unique)) {
        $backup=Join-Path $run ('backup\'+$inf)
        [void][IO.Directory]::CreateDirectory($backup)
        & "$env:SystemRoot\System32\pnputil.exe" /export-driver $inf $backup 2>&1 |
            Out-File -LiteralPath (Join-Path $run ('export-'+$inf+'.log')) -Encoding UTF8
        if ($LASTEXITCODE -ne 0) {throw ('Driver backup failed: '+$inf)}
    }
    $state.phase='stopping-model';Save-State
    $health=$null
    try {$health=Get-LocalJson 'http://127.0.0.1:8080/health'} catch {}
    $state.model_was_loaded=[bool]($health -and $health.loaded)
    if ($state.model_was_loaded) {
        $live=(Get-LocalJson 'http://127.0.0.1:8080/metrics').live
        if ($live.state -ne 'idle' -or $live.queued -gt 0) {throw 'Model request active; driver installation deferred.'}
        $stopped=Console-Post '/api/stop' @{}
        $stopped | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'model-stop.json') -Encoding UTF8
        $deadline=(Get-Date).AddSeconds(45)
        while ((Get-Process -Name strata -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) {Start-Sleep -Seconds 1}
    }
    if (Get-Process -Name strata -ErrorAction SilentlyContinue) {throw 'An inference engine is still running.'}
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class KiaraDriverUpdate58180 {
    [DllImport("newdev.dll",CharSet=CharSet.Unicode,SetLastError=true,ExactSpelling=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool UpdateDriverForPlugAndPlayDevicesW(
        IntPtr window,string hardwareId,string inf,uint flags,
        [MarshalAs(UnmanagedType.Bool)] out bool reboot);
}
'@
    $targets=@(
        @{label='RTX 3080';id='PCI\VEN_10DE&DEV_2216&SUBSYS_403F1458&REV_A1';inf='geforce\extracted\Display.Driver\nv_dispi.inf'},
        @{label='Two Tesla P100';id='PCI\VEN_10DE&DEV_15F8&SUBSYS_118F10DE&REV_A1';inf='quadro\extracted\Display.Driver\nv_dispwi.inf'},
        @{label='Quadro P2200';id='PCI\VEN_10DE&DEV_1C31&SUBSYS_131B10DE&REV_A1';inf='quadro\extracted\Display.Driver\nvlwwi.inf'}
    )
    foreach ($target in $targets) {
        $state.phase='installing '+$target.label;Save-State
        $inf=Join-Path 'F:\Kiara-tests\pilotes-581.80' $target.inf
        $reboot=$false
        # FORCE is necessary for the explicitly requested downgrade from 582.99.
        # A non-null reboot output keeps reboot decisions with the caller.
        $ok=[KiaraDriverUpdate58180]::UpdateDriverForPlugAndPlayDevicesW([IntPtr]::Zero,$target.id,$inf,1,[ref]$reboot)
        $code=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
        $state.updates+=@{card=$target.label;hardware_id=$target.id;inf=$inf;success=$ok;win32_error=$(if($ok){0}else{$code});reboot_required=$reboot}
        $state.reboot_required=($state.reboot_required -or $reboot)
        Save-State
    }
    $state.phase='verification';Save-State
    $after=Cards
    $after | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'drivers-after.json') -Encoding UTF8
    $state.all_associations_58180=($after.Count -eq 4 -and @($after | Where-Object DriverVersion -ne '32.0.15.8180').Count -eq 0)
    $state.all_updates_succeeded=(@($state.updates | Where-Object {!$_.success}).Count -eq 0)
    Get-PnpDevice -PresentOnly -Class Display | Select-Object Status,FriendlyName,InstanceId,Problem |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'pnp-after.json') -Encoding UTF8
    & nvidia-smi --query-gpu=index,name,driver_version,uuid --format=csv 2>&1 |
        Out-File -LiteralPath (Join-Path $run 'nvidia-smi-after.txt') -Encoding UTF8
    $state.phase=$(if($state.all_associations_58180 -and $state.all_updates_succeeded){'installed'}else{'needs-attention'})
    Save-State
} catch {
    $state.phase='error';$state.error=$_.Exception.Message;Save-State
} finally {
    Stop-Transcript | Out-Null
}
