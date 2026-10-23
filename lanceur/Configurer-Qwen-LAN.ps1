param(
    [Parameter(Mandatory=$true)][ValidateSet('Activer','Couper')][string]$Action,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{32}$')][string]$RequestId
)
$ErrorActionPreference = 'Stop'
$taskResult = Join-Path $PSScriptRoot 'qwen-lan-action.json'
$taskAddress = '192.168.1.41'
$taskSubnet = '192.168.1.0/24'
$taskPort = 8080
$taskRule = 'Qwen-API-LAN-TCP-8080'
$taskRegistry = 'HKLM:\SYSTEM\CurrentControlSet\Services\PortProxy\v4tov4\tcp'
$taskMapping = "$taskAddress/$taskPort"
$taskTarget = "127.0.0.1/$taskPort"
function Save-Result($State,$Message) {
    $taskPrevious = Get-Content -LiteralPath $taskResult -Raw | ConvertFrom-Json
    if ($taskPrevious.request_id -ne $RequestId) { throw 'Une autre demande a remplacé cette opération.' }
    $taskPrevious.state = $State
    $taskPrevious | Add-Member -NotePropertyName message -NotePropertyValue $Message -Force
    $taskTemporary = $taskResult + '.' + $RequestId + '.tmp'
    $taskPrevious | ConvertTo-Json | Set-Content -LiteralPath $taskTemporary -Encoding UTF8
    Move-Item -LiteralPath $taskTemporary -Destination $taskResult -Force
}
try {
    $taskIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    if (!([Security.Principal.WindowsPrincipal]::new($taskIdentity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        $taskArgs = @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'),'-Action',$Action,'-RequestId',$RequestId)
        $taskProcess = Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList $taskArgs -Wait -PassThru
        exit $taskProcess.ExitCode
    }
    $taskPrevious = Get-Content -LiteralPath $taskResult -Raw | ConvertFrom-Json
    if ($taskPrevious.request_id -ne $RequestId -or $taskPrevious.state -ne 'waiting' -or ([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $taskPrevious.started) -gt 300) { throw 'La demande a expiré ou a changé. Réessayez.' }
    $taskExisting = Get-ItemPropertyValue -LiteralPath $taskRegistry -Name $taskMapping -ErrorAction SilentlyContinue
    if ($taskExisting -and $taskExisting -ne $taskTarget) { throw 'Une autre redirection utilise ce port. Elle a été conservée.' }
    if ($Action -eq 'Couper') {
        # Close new connections first, then remove only our own authorization.
        if ($taskExisting -eq $taskTarget) {
            & netsh interface portproxy delete v4tov4 "listenaddress=$taskAddress" "listenport=$taskPort" protocol=tcp | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Impossible de couper la redirection locale. Réessayez.' }
        }
        Get-NetFirewallRule -Name $taskRule -ErrorAction SilentlyContinue | Remove-NetFirewallRule
        Save-Result 'done' 'Accès local coupé.'
        exit 0
    }
    if (!(Get-NetIPAddress -IPAddress $taskAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue)) { throw 'Adresse locale du serveur indisponible. Vérifiez le réseau.' }
    $taskHealth = Invoke-RestMethod 'http://127.0.0.1:8080/health' -TimeoutSec 5
    if ($taskHealth.service -ne 'strata' -or $taskHealth.api_key -ne $false -or $taskHealth.model -notlike '*qwen*') { throw 'Qwen sans authentification est indisponible sur le port local 8080.' }
    Set-Service iphlpsvc -StartupType Automatic
    Start-Service iphlpsvc
    $taskFirewall = Get-NetFirewallRule -Name $taskRule -ErrorAction SilentlyContinue
    if ($taskFirewall) {
        $taskFirewall | Set-NetFirewallRule -Enabled True -Direction Inbound -Action Allow -Profile Any -Protocol TCP -LocalAddress $taskAddress -LocalPort $taskPort -RemoteAddress $taskSubnet -EdgeTraversalPolicy Block
    } else {
        New-NetFirewallRule -Name $taskRule -DisplayName 'Qwen API - LAN uniquement' -Enabled True -Direction Inbound -Action Allow -Profile Any -Protocol TCP -LocalAddress $taskAddress -LocalPort $taskPort -RemoteAddress $taskSubnet -EdgeTraversalPolicy Block | Out-Null
    }
    & netsh interface portproxy add v4tov4 "listenaddress=$taskAddress" "listenport=$taskPort" connectaddress=127.0.0.1 "connectport=$taskPort" protocol=tcp | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Impossible d''activer la redirection locale. Réessayez.' }
    Save-Result 'done' 'Accès local activé.'
} catch {
    $taskMessage = 'La modification a échoué : ' + $_.Exception.Message
    if ($_.Exception.NativeErrorCode -eq 1223 -or $_.Exception.Message -match '(?i)annul|cancel') { $taskMessage = 'Validation Windows annulée. Réessayez pour modifier l''accès local.' }
    try { Save-Result 'failed' $taskMessage } catch {}
    exit 1
}
