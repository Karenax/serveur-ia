param([switch]$Appliquer, [switch]$Eleve, [switch]$ValiderParWindows)
$ErrorActionPreference = 'Stop'
$targetAddress = '192.168.1.41'
$expectedMac = 'E0-4F-43-E6-50-12'
$gatewayAddress = '192.168.1.1'
$resultPath = Join-Path $PSScriptRoot 'resultat.json'

function Save-Result($State, $Details) {
    @{state=$State;time=(Get-Date).ToString('o');details=$Details} |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding UTF8
}
function Invoke-Netsh([string[]]$Arguments) {
    $output = & "$env:SystemRoot\System32\netsh.exe" @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw ('netsh: ' + ($output -join ' ')) }
}
function Get-OwnerMac([string]$Address) {
    if (-not ('FredNetworkArp' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Net;
using System.Runtime.InteropServices;
public static class FredNetworkArp {
    [DllImport("iphlpapi.dll", ExactSpelling=true)]
    private static extern int SendARP(uint destination, uint source, byte[] mac, ref uint length);
    public static string Owner(string address) {
        byte[] mac = new byte[6]; uint length = 6;
        uint destination = BitConverter.ToUInt32(IPAddress.Parse(address).GetAddressBytes(), 0);
        int result = SendARP(destination, 0, mac, ref length);
        return result == 0 && length == 6 ? BitConverter.ToString(mac) : null;
    }
}
'@
    }
    return [FredNetworkArp]::Owner($Address)
}

$changed = $false
try {
    $adapters = @(Get-NetAdapter | Where-Object { $_.MacAddress -eq $expectedMac })
    if ($adapters.Count -ne 1 -or $adapters[0].Status -ne 'Up') {
        throw 'La carte Marvell attendue doit etre unique et connectee.'
    }
    $adapter = $adapters[0]
    $index = $adapter.InterfaceIndex
    $addresses = @(Get-NetIPAddress -InterfaceIndex $index -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike '169.254.*' })
    if ($addresses.Count -ne 1 -or $addresses[0].PrefixLength -ne 24 -or
        $addresses[0].IPAddress -notin @('192.168.1.40', $targetAddress)) {
        throw 'Configuration IPv4 inattendue : aucun changement effectue.'
    }
    $ipInterface = Get-NetIPInterface -InterfaceIndex $index -AddressFamily IPv4
    $routes = @(Get-NetRoute -InterfaceIndex $index -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0')
    if ($routes.Count -ne 1 -or $routes[0].NextHop -ne $gatewayAddress) {
        throw 'Passerelle inattendue : aucun changement effectue.'
    }
    $dns = @((Get-DnsClientServerAddress -InterfaceIndex $index -AddressFamily IPv4).ServerAddresses)
    if ($dns.Count -ne 1 -or $dns[0] -ne $gatewayAddress) {
        throw 'DNS inattendu : aucun changement effectue.'
    }
    $registryPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\' + $adapter.InterfaceGuid
    $dnsManual = (Get-ItemProperty -LiteralPath $registryPath -Name NameServer -ErrorAction SilentlyContinue).NameServer
    $before = @{interface=$adapter.Name;index=$index;mac=$adapter.MacAddress;
        address=$addresses[0].IPAddress;prefix=24;dhcp=$ipInterface.Dhcp.ToString();
        gateway=$routes[0].NextHop;gateway_metric=$routes[0].RouteMetric;dns=$dns;dns_manual=$dnsManual}
    $plan = @{before=$before;requested=@{address=$targetAddress;mask='255.255.255.0';prefix=24;
        gateway=$gatewayAddress;dns=$dns;dhcp='Disabled';persistent=$true}}
    if (-not $Appliquer) {
        $plan['target_owner_mac'] = Get-OwnerMac $targetAddress
        $plan | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'plan.json') -Encoding UTF8
        $plan | ConvertTo-Json -Depth 8
        exit 0
    }
    $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        if ($Eleve) { throw 'Droits administrateur Windows requis.' }
        Save-Result 'elevation_requested' $plan
        $arguments = @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'),'-Appliquer','-Eleve')
        if ($ValiderParWindows) { $arguments += '-ValiderParWindows' }
        $process = Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList $arguments -PassThru
        @{state='elevation_requested';pid=$process.Id} | ConvertTo-Json
        exit 0
    }
    if ($addresses[0].IPAddress -ne $targetAddress) {
        # Clear only this neighbour entry, then resolve it again to detect a real conflict.
        Remove-NetNeighbor -InterfaceIndex $index -IPAddress $targetAddress -Confirm:$false -ErrorAction SilentlyContinue
        $ownerMac = Get-OwnerMac $targetAddress
        if ($ownerMac -and $ownerMac -ne $expectedMac -and -not $ValiderParWindows) {
            Save-Result 'address_conflict' @{address=$targetAddress;owner_mac=$ownerMac;before=$before}
            exit 2
        }
    }
    $backupPath = Join-Path $PSScriptRoot ('avant-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')
    $before | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $backupPath -Encoding UTF8
    $changed = $true
    Invoke-Netsh -Arguments @('interface','ipv4','set','address',('name='+$adapter.Name),'source=static',
        ('address='+$targetAddress),'mask=255.255.255.0',('gateway='+$gatewayAddress),'gwmetric=1','store=persistent')
    Set-DnsClientServerAddress -InterfaceIndex $index -ServerAddresses $dns
    $deadline = (Get-Date).AddSeconds(20)
    do {
        $actual = Get-NetIPAddress -InterfaceIndex $index -AddressFamily IPv4 -IPAddress $targetAddress -ErrorAction SilentlyContinue
        if ($actual.AddressState -eq 'Duplicate') { throw 'Conflit IPv4 detecte par Windows.' }
        if ($actual.AddressState -eq 'Preferred') { break }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    $actualInterface = Get-NetIPInterface -InterfaceIndex $index -AddressFamily IPv4
    $persistent = Get-NetIPAddress -InterfaceIndex $index -AddressFamily IPv4 -PolicyStore PersistentStore -IPAddress $targetAddress
    if ($actual.AddressState -ne 'Preferred' -or $actual.PrefixOrigin -ne 'Manual' -or
        $actualInterface.Dhcp -ne 'Disabled' -or -not $persistent) {
        throw 'IP fixe persistante non confirmee.'
    }
    $ping = New-Object System.Net.NetworkInformation.Ping
    try { $gatewayReply = $ping.Send($gatewayAddress,2000) } finally { $ping.Dispose() }
    if ($gatewayReply.Status -ne 'Success') { throw 'Passerelle inaccessible apres modification.' }
    Save-Result 'succeeded' @{address=$targetAddress;prefix=24;gateway=$gatewayAddress;dns=$dns;
        interface=$adapter.Name;mac=$expectedMac;dhcp='Disabled';persistent=$true;backup=$backupPath}
} catch {
    $failure = $_.Exception.Message
    $rollback = 'not_needed'
    if ($changed) {
        try {
            if ($before.dhcp -eq 'Enabled') {
                Invoke-Netsh -Arguments @('interface','ipv4','set','address',('name='+$before.interface),'source=dhcp','store=persistent')
            } else {
                Invoke-Netsh -Arguments @('interface','ipv4','set','address',('name='+$before.interface),'source=static',
                    ('address='+$before.address),'mask=255.255.255.0',('gateway='+$before.gateway),
                    ('gwmetric='+$before.gateway_metric),'store=persistent')
            }
            if ($before.dns_manual) { Set-DnsClientServerAddress -InterfaceIndex $before.index -ServerAddresses $before.dns }
            else { Set-DnsClientServerAddress -InterfaceIndex $before.index -ResetServerAddresses }
            $rollback = 'restored'
        } catch { $rollback = $_.Exception.Message }
    }
    Save-Result 'failed' @{message=$failure;rollback=$rollback}
    throw
}
