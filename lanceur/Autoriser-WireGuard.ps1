param([ValidateRange(1,65535)][int]$Port=51820,[Parameter(Mandatory=$true)][string]$Program,[Parameter(Mandatory=$true)][string]$ResultPath)
$ErrorActionPreference='Stop'
function Save-Result($State,$Message) {
    @{state=$State;message=$Message;port=$Port;checked_at=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $ResultPath -Encoding UTF8
}
$resolved=(Resolve-Path -LiteralPath $Program).Path
if ((Split-Path $resolved -Leaf) -ne 'wireguard-bridge.exe') { throw 'Moteur WireGuard invalide.' }
# Reading COM firewall policy needs no elevation: retain an existing authorization.
try {
    $policy=New-Object -ComObject HNetCfg.FwPolicy2
    $allowed=@($policy.Rules) | Where-Object {
        $_.Enabled -and $_.Direction -eq 1 -and $_.Action -eq 1 -and
        $_.Protocol -eq 17 -and $_.LocalPorts -eq [string]$Port -and
        $_.ApplicationName -ieq $resolved -and $_.Profiles -eq 2147483647
    }
    if ($allowed) {
        Save-Result 'ready' ('Port UDP '+$Port+' déjà autorisé pour WireGuard. Autorisation Windows conservée.')
        exit
    }
} catch {}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Save-Result 'waiting' 'Validation administrateur Windows en attente.'
    $arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'),'-Port',$Port,'-Program',('"'+$Program+'"'),'-ResultPath',('"'+$ResultPath+'"'))
    try { Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList $arguments }
    catch { Save-Result 'failed' $_.Exception.Message }
    exit
}
try {
    Get-NetFirewallRule -Name 'Qwen-WireGuard-UDP' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -Name 'Qwen-WireGuard-UDP' -DisplayName 'Qwen · WireGuard UDP' -Direction Inbound -Action Allow -Protocol UDP -LocalPort $Port -Program $resolved -Profile Any | Out-Null
    Save-Result 'ready' ('Port UDP '+$Port+' autorisé dans Windows pour WireGuard.')
} catch { Save-Result 'failed' $_.Exception.Message }
