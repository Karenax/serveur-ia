param([ValidateRange(1,65535)][int]$Port=51820,[Parameter(Mandatory=$true)][string]$Program,[Parameter(Mandatory=$true)][string]$ResultPath,[switch]$Nettoyer)
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
    if ($allowed -and !$Nettoyer) {
        Save-Result 'ready' ('Port UDP '+$Port+' déjà autorisé pour WireGuard. Autorisation Windows conservée.')
        exit
    }
} catch {}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    if ($Nettoyer) { throw "Ouvrez PowerShell en tant qu'administrateur pour nettoyer les regles WireGuard." }
    Save-Result 'waiting' 'Validation administrateur Windows en attente.'
    $arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'),'-Port',$Port,'-Program',('"'+$Program+'"'),'-ResultPath',('"'+$ResultPath+'"'))
    try { Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList $arguments }
    catch { Save-Result 'failed' $_.Exception.Message }
    exit
}
try {
    $ruleId='Qwen-WireGuard-UDP'
    $rule=Get-NetFirewallRule -PolicyStore PersistentStore -Name $ruleId -ErrorAction SilentlyContinue
    if (!$rule) {
        New-NetFirewallRule -PolicyStore PersistentStore -Name $ruleId -DisplayName 'Kiara WireGuard UDP' -Direction Inbound -Action Allow -Protocol UDP -LocalPort $Port -Program $resolved -Profile Any | Out-Null
    } else {
        $application=$rule | Get-NetFirewallApplicationFilter
        $portFilter=$rule | Get-NetFirewallPortFilter
        if ($rule.Enabled -ne 'True' -or $rule.Direction -ne 'Inbound' -or $rule.Action -ne 'Allow' -or $rule.Profile -ne 'Any' -or
            $application.Program -ine $resolved -or $portFilter.Protocol -ne 'UDP' -or $portFilter.LocalPort -ne [string]$Port) {
            Set-NetFirewallRule -PolicyStore PersistentStore -Name $ruleId -Enabled True -Direction Inbound -Action Allow -Protocol UDP -LocalPort $Port -Program $resolved -Profile Any | Out-Null
        }
    }
    $removed=0
    if ($Nettoyer) {
        $legacyIds=@('Kiara-WireGuard-Cache-Recette-TCP','Kiara-WireGuard-Cache-Recette-UDP','Kiara-WireGuard-Bridge-Private-UDP')
        $legacy=@(Get-NetFirewallRule -PolicyStore PersistentStore | Where-Object {
            $_.Name -in $legacyIds -or $_.DisplayName -in @('wireguard-bridge.exe','wireguard-recette','wireguard-recette.exe')
        })
        # Read the paths before removing rules, since deleting one notification rule can remove its companion.
        $targets=foreach ($candidate in $legacy) {
            if ($candidate.Name -in $legacyIds) { $candidate.Name; continue }
            $path=($candidate | Get-NetFirewallApplicationFilter -ErrorAction SilentlyContinue).Program
            if (!$path -and $candidate.Name -match '^\w+ Query User\{[0-9a-f-]+\}([A-Z]:\\.+)$') { $path=$Matches[1] }
            if ($path -ieq $resolved -or $path -match '(?i)\\(?:kiara\\integration-agent|kiara-integration|serveur ia\\toolchain|accesserveurfred\\wireguard|temp\\kiara-[^\\]+)\\') { $candidate.Name }
        }
        foreach ($target in $targets) {
            if (Get-NetFirewallRule -PolicyStore PersistentStore -Name $target -ErrorAction SilentlyContinue) {
                Remove-NetFirewallRule -PolicyStore PersistentStore -Name $target
                $removed++
            }
        }
        Write-Output "$removed anciennes regles Kiara WireGuard supprimees. UDP $Port autorise pour $resolved."
    }
    Save-Result 'ready' ('Port UDP '+$Port+' autorisé dans Windows pour WireGuard.')
} catch {
    Save-Result 'failed' $_.Exception.Message
    if ($Nettoyer) { throw }
}
