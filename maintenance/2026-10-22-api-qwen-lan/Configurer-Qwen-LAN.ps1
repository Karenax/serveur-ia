param([switch]$Retirer)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskResult = Join-Path $taskRoot 'installation.json'
$taskAddress = '192.168.1.41'
$taskSubnet = '192.168.1.0/24'
$taskPort = 8080
$taskRule = 'Qwen-API-LAN-TCP-8080'
$taskRegistry = 'HKLM:\SYSTEM\CurrentControlSet\Services\PortProxy\v4tov4\tcp'
$taskMapping = "$taskAddress/$taskPort"
$taskTarget = "127.0.0.1/$taskPort"

try {
    $taskIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    if (!([Security.Principal.WindowsPrincipal]::new($taskIdentity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Exécuter ce script en administrateur Windows.'
    }
    $taskExisting = Get-ItemPropertyValue -LiteralPath $taskRegistry -Name $taskMapping -ErrorAction SilentlyContinue
    if ($taskExisting -and $taskExisting -ne $taskTarget) {
        throw 'Une autre redirection utilise cette adresse et ce port ; elle est conservée.'
    }
    if ($Retirer) {
        if ($taskExisting -eq $taskTarget) {
            & netsh interface portproxy delete v4tov4 "listenaddress=$taskAddress" "listenport=$taskPort" protocol=tcp | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Suppression de la redirection impossible.' }
        }
        Get-NetFirewallRule -Name $taskRule -ErrorAction SilentlyContinue | Remove-NetFirewallRule
        @{state='removed'; address=$taskAddress; port=$taskPort; checked_at=(Get-Date).ToString('o')} |
            ConvertTo-Json | Set-Content -LiteralPath $taskResult -Encoding UTF8
        exit 0
    }
    if (!(Get-NetIPAddress -IPAddress $taskAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue)) {
        throw 'L adresse locale prévue n est pas configurée sur ce serveur.'
    }
    $taskHealth = Invoke-RestMethod 'http://127.0.0.1:8080/health' -TimeoutSec 5
    if ($taskHealth.service -ne 'strata' -or $taskHealth.api_key -ne $false) {
        throw 'Le moteur Strata sans authentification attendu n est pas disponible.'
    }
    # Persisted by Windows; the existing loopback listener and model remain untouched.
    Set-Service iphlpsvc -StartupType Automatic
    Start-Service iphlpsvc
    # Install the restricted firewall rule before opening the LAN listener.
    $taskFirewall = Get-NetFirewallRule -Name $taskRule -ErrorAction SilentlyContinue
    if ($taskFirewall) {
        $taskFirewall | Set-NetFirewallRule -Enabled True -Direction Inbound -Action Allow -Profile Any -Protocol TCP -LocalAddress $taskAddress -LocalPort $taskPort -RemoteAddress $taskSubnet -EdgeTraversalPolicy Block
    } else {
        New-NetFirewallRule -Name $taskRule -DisplayName 'Qwen API - réseau local uniquement' -Enabled True -Direction Inbound -Action Allow -Profile Any -Protocol TCP -LocalAddress $taskAddress -LocalPort $taskPort -RemoteAddress $taskSubnet -EdgeTraversalPolicy Block | Out-Null
    }
    & netsh interface portproxy add v4tov4 "listenaddress=$taskAddress" "listenport=$taskPort" connectaddress=127.0.0.1 "connectport=$taskPort" protocol=tcp | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Installation de la redirection impossible.' }
    $taskVerified = Get-ItemPropertyValue -LiteralPath $taskRegistry -Name $taskMapping
    if ($taskVerified -ne $taskTarget) { throw 'La redirection persistante ne correspond pas à la configuration attendue.' }
    @{state='ready'; base_url="http://${taskAddress}:$taskPort/v1"; source_subnet=$taskSubnet; authentication=$false; upstream="127.0.0.1:$taskPort"; persistent=$true; checked_at=(Get-Date).ToString('o')} |
        ConvertTo-Json | Set-Content -LiteralPath $taskResult -Encoding UTF8
} catch {
    @{state='failed'; message=$_.Exception.Message; checked_at=(Get-Date).ToString('o')} |
        ConvertTo-Json | Set-Content -LiteralPath $taskResult -Encoding UTF8
    exit 1
}
