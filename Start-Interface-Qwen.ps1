param([switch]$SansNavigateur,[switch]$PreserverEtatModele)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$url = 'http://127.0.0.1:8765'
$existing = $null
try { $existing = Invoke-RestMethod ($url + '/health') -TimeoutSec 2 } catch {}
if ($existing.service -ne 'qwen-launcher') {
    if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) {
        throw 'Le port 8765 est occupe par une autre application.'
    }
    $python = Join-Path $root 'Strata-src\.venv\Scripts\python.exe'
    $app = Join-Path $root 'lanceur\app.py'
    $command = '"' + $python + '" "' + $app + '" --port 8765'
    if ($PreserverEtatModele) { $command += ' --preserve-model-state' }
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
    $result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$command;CurrentDirectory=$root;ProcessStartupInformation=$startup}
    if ($result.ReturnValue -ne 0) { throw "Windows ne lance pas l'interface (code $($result.ReturnValue))." }
    $ready = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        try {
            $response = Invoke-RestMethod ($url + '/health') -TimeoutSec 1
            if ($response.service -eq 'qwen-launcher') { $ready = $true; break }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    if (!$ready) { throw "L'interface ne repond pas sur le port 8765." }
}
if (!$SansNavigateur) { Start-Process $url }
Write-Output "Interface disponible : $url. Le serveur LLM conserve son etat."
