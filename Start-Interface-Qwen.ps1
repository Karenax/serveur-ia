param([switch]$SansNavigateur,[switch]$PreserverEtatModele,[switch]$Redemarrer,[switch]$VerifierBascule)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$url = 'http://127.0.0.1:8765'
$dataDirectory = if ($env:KIARA_DATA_DIR) { $env:KIARA_DATA_DIR } else { Join-Path $root 'lanceur' }
$python = if ($env:KIARA_RUNTIME_PYTHON) {
    [IO.Path]::GetFullPath($env:KIARA_RUNTIME_PYTHON)
} else {
    Join-Path $root 'Strata-src\.venv\Scripts\python.exe'
}
$app = Join-Path $root 'lanceur\app.py'
$pendingRelease = Join-Path $root 'client-qwen\dist\release-pending.json'
$pendingBridge = Join-Path $root 'client-qwen\dist\wireguard-bridge-pending.exe'
$agentConfig = Join-Path $dataDirectory 'agent-service.json'
$expectedAgentProjects = $null
$expectedAgentRuntime = $null
$existing = $null
try { $existing = Invoke-RestMethod ($url + '/health') -TimeoutSec 2 } catch {}
if ($VerifierBascule -and ($existing.service -ne 'qwen-launcher' -or !(Test-Path -LiteralPath $agentConfig -PathType Leaf))) {
    throw 'Le controle de bascule exige un lanceur actif et une configuration Agent.'
}
if (($Redemarrer -or $VerifierBascule) -and $existing.service -eq 'qwen-launcher') {
    if (!(Test-Path -LiteralPath $python -PathType Leaf) -or !(Test-Path -LiteralPath $app -PathType Leaf)) {
        throw 'Le code ou le runtime du lanceur est introuvable.'
    }
    $agentBeforeRestart = $null
    if (Test-Path -LiteralPath $agentConfig -PathType Leaf) {
        $page = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
        $session = [regex]::Match($page.Content, '<meta name="launcher-token" content="([^"]+)">')
        if (!$session.Success) { throw 'Jeton de la console locale absent.' }
        $headers = @{ 'X-Launcher-Token' = $session.Groups[1].Value }
        $agentBeforeRestart = Invoke-RestMethod ($url + '/api/agent-service') -Headers $headers -TimeoutSec 5
        $preflight = @'
from contextlib import closing
from html.parser import HTMLParser
import json
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlsplit

root, data = map(Path, sys.argv[1:3])
sys.path[:0] = [str(root / 'lanceur'), str(root / 'shared')]
from agent_service import AgentService, service_configuration, web_configuration

class FrontendAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.modules = []
        self.styles = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'script' and attrs.get('type') == 'module':
            self.modules.append(attrs.get('src') or '')
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.styles.append(attrs.get('href') or '')

try:
    service = AgentService(None, **service_configuration(data))
    service.preflight()
    web = web_configuration(data)
    dist = root / 'agent/web/dist'
    assets = FrontendAssets()
    assets.feed((dist / 'index.html').read_text(encoding='utf-8'))
    if not assets.modules or not assets.styles:
        raise ValueError('Frontend Agent incomplet. Recompiler agent/web.')
    for reference in assets.modules + assets.styles:
        url = urlsplit(reference)
        file = (dist / url.path.lstrip('/')).resolve()
        if (url.scheme or url.netloc or not url.path.startswith('/assets/')
                or not file.is_relative_to((dist / 'assets').resolve())
                or not file.is_file() or not file.stat().st_size):
            raise ValueError('Ressource du frontend Agent manquante ou invalide. Recompiler agent/web.')
    erp = service.data / 'erp' / 'minipilot.db'
    with closing(sqlite3.connect(erp.as_uri() + '?mode=ro', uri=True, timeout=3)) as db:
        catalogue = [dict(id=identity, code=code, title=title, status=status)
                     for identity, code, title, status in db.execute('SELECT id, code, title, status FROM projects')]
    grants = None
    if sys.argv[3] == 'initial':
        legacy = data.resolve() / 'espaces-prives' / 'espaces.sqlite3'
        grants = 0
        if legacy.is_file():
            with closing(sqlite3.connect(legacy.as_uri() + '?mode=ro', uri=True, timeout=3)) as db:
                counts = [db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                          for table in ('projects', 'documents')]
                grants = db.execute("SELECT count(*) FROM settings WHERE key GLOB 'agent-access:*'").fetchone()[0]
            if any(counts):
                raise ValueError(f'Le catalogue Kiara historique contient encore {counts[0]} projets et {counts[1]} documents.')
    runtime = {'worker_groups': service.worker_groups if service.start_workers else (),
               'document_project_root': service.document_project_root,
               'web': web}
    print(json.dumps({'catalogue': catalogue, 'agent_grants': grants, 'runtime': runtime}, ensure_ascii=True))
except (OSError, ValueError, sqlite3.Error) as error:
    sys.exit(str(error))
'@
        $phase = if ($agentBeforeRestart.configured) { 'restart' } else { 'initial' }
        $checked = $preflight | & $python -B - $root $dataDirectory $phase
        if ($LASTEXITCODE -ne 0) { throw 'La configuration Agent doit etre corrigee avant le redemarrage.' }
        Write-Output 'Frontend Agent : ressources principales presentes.'
        $cutover = ConvertFrom-Json -InputObject $checked
        $expectedAgentRuntime = $cutover.runtime
        $expectedAgentProjects = @($cutover.catalogue)
        Write-Output "Projets ERP Agent attendus : $($expectedAgentProjects.Count)."
        if ($phase -eq 'initial') {
            Write-Output 'Catalogue Kiara historique : 0 projet, 0 document.'
            if ($cutover.agent_grants -eq 0) {
                Write-Output 'Aucune habilitation Agent enregistree. Attribuer les premiers acces dans Acces Agent apres activation.'
            }
        }
    }
    $identity = Get-Content -LiteralPath (Join-Path $dataDirectory 'interface.pid.json') -Raw | ConvertFrom-Json
    $listeners = @(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen)
    if ($listeners.Count -ne 1 -or $listeners[0].OwningProcess -ne $identity.pid) {
        throw 'Identite du lanceur non confirmee.'
    }
    $running = Get-Process -Id $identity.pid
    $created = ([DateTimeOffset]$running.StartTime).ToUnixTimeMilliseconds() / 1000
    if ([math]::Abs($created - $identity.created) -gt 0.05) { throw 'Identite du lanceur modifiee.' }
    $deadline = (Get-Date).AddSeconds(60)
    $waiting = $false
    do {
        $remote = Invoke-RestMethod ($url + '/api/remote') -TimeoutSec 3
        if ($remote.maintenance) { throw 'Kiara est en maintenance.' }
        $backup = Invoke-RestMethod ($url + '/api/backups') -TimeoutSec 3
        $busy = $remote.active -ne 0 -or $remote.agent_active -gt 0 -or $backup.job.state -eq 'running'
        if (!$busy -or $VerifierBascule -or (Get-Date) -ge $deadline) { break }
        if (!$waiting) {
            Write-Output 'Attente de la fin des requetes Kiara et Agent ou de la sauvegarde.'
            $waiting = $true
        }
        Start-Sleep -Milliseconds 500
    } while ($true)
    if ($busy) {
        throw 'Kiara ou Agent traite une requete ou une maintenance.'
    }
    if ($VerifierBascule) {
        Write-Output 'Controle de bascule reussi.'
        return
    }
    $listeners = @(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen)
    if ($running.HasExited -or $listeners.Count -ne 1 -or $listeners[0].OwningProcess -ne $running.Id) {
        throw 'Le processus du lanceur a change pendant le controle.'
    }
    $remote = Invoke-RestMethod ($url + '/api/remote') -TimeoutSec 3
    $backup = Invoke-RestMethod ($url + '/api/backups') -TimeoutSec 3
    if ($remote.active -ne 0 -or $remote.agent_active -gt 0 -or $remote.maintenance -or $backup.job.state -eq 'running') {
        throw 'Une nouvelle requete ou maintenance a demarre.'
    }
    try { Stop-Process -Id $running.Id -ErrorAction Stop }
    catch [System.ComponentModel.Win32Exception] {
        if ($_.Exception.NativeErrorCode -ne 5) { throw }
        throw "Ouvrez PowerShell en tant qu'administrateur pour redemarrer ce lanceur."
    }
    if (!$running.WaitForExit(5000)) { throw 'Le lanceur est toujours actif.' }
    $existing = $null
    $PreserverEtatModele = $true
}
if ($existing.service -ne 'qwen-launcher') {
    if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) {
        throw 'Le port 8765 est occupe par une autre application.'
    }
    if ((Test-Path -LiteralPath $pendingRelease -PathType Leaf) -and (Test-Path -LiteralPath $pendingBridge -PathType Leaf)) {
        $bridge = Join-Path $root 'client-qwen\wireguard-bridge.exe'
        $previousBridge = $pendingBridge + '.previous'
        $deadline = (Get-Date).AddSeconds(10)
        while ($true) {
            try { [IO.File]::Replace($pendingBridge, $bridge, $previousBridge); break }
            catch [IO.IOException] {
                if ((Get-Date) -ge $deadline) { throw }
                Start-Sleep -Milliseconds 250
            }
        }
    }
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
if ($Redemarrer) {
    if (Test-Path -LiteralPath $agentConfig -PathType Leaf) {
        $page = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
        $session = [regex]::Match($page.Content, '<meta name="launcher-token" content="([^"]+)">')
        if (!$session.Success) { throw 'Jeton de la console locale absent.' }
        $headers = @{ 'X-Launcher-Token' = $session.Groups[1].Value }
        $deadline = (Get-Date).AddSeconds(75)
        do {
            try {
                $agent = Invoke-RestMethod ($url + '/api/agent-service') -Headers $headers -TimeoutSec 3
            } catch {
                if ($_.Exception.Response) { throw }
                $agent = $null
                Start-Sleep -Milliseconds 500
                continue
            }
            if ($agent.configuration_error) { throw $agent.configuration_error }
            if ($agent.startup_error) { throw $agent.startup_error }
            if (!$agent.configured) { throw "Le lanceur n'a pas charge la configuration Agent." }
            if (!$agent.running) { Start-Sleep -Milliseconds 500 }
        } while (!$agent.running -and (Get-Date) -lt $deadline)
        if (!$agent.running) { throw 'Agent ne repond pas apres le redemarrage du lanceur.' }
        if ($null -ne $expectedAgentRuntime) {
            if ($agent.document_project_root -cne $expectedAgentRuntime.document_project_root -or
                (($null -eq $agent.worker_groups) -ne ($null -eq $expectedAgentRuntime.worker_groups)) -or
                (($agent.worker_groups -join ',') -cne ($expectedAgentRuntime.worker_groups -join ','))) {
                throw 'Les groupes de traitements ou le dossier client charges par Agent different de la configuration.'
            }
            if ($null -ne $expectedAgentRuntime.web) {
                $sharedAgentWeb = $expectedAgentRuntime.web[1] -eq 0
                $expectedWebPort = if ($sharedAgentWeb) { 8766 } else { $expectedAgentRuntime.web[1] }
                if ($agent.web_error -or $agent.web_origin -cne $expectedAgentRuntime.web[0] -or
                    $agent.web_port -ne $expectedWebPort) {
                    throw 'Le web prive Agent ne correspond pas a la configuration.'
                }
                $webPath = if ($sharedAgentWeb) { '/agent/' } else { '/' }
                $listener = 'http://127.0.0.1:' + $agent.web_port + $webPath
                $webHost = $agent.web_origin.Substring('https://'.Length)
                $probe = Invoke-WebRequest -UseBasicParsing -Uri $listener -Method Head -Headers @{Host=$webHost} -TimeoutSec 5
                if ($probe.StatusCode -ne 200 -or $probe.Headers['Cache-Control'] -notcontains 'no-store') {
                    throw 'Le listener local du web prive Agent ne repond pas comme attendu.'
                }
            }
        }
        $catalogue = Invoke-RestMethod ($url + '/api/agent-service/catalogue') -Headers $headers -TimeoutSec 25
        if ($null -ne $expectedAgentProjects) {
            $expected = [System.Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
            foreach ($project in $expectedAgentProjects) { $expected.Add([string]$project.id, $project) }
            foreach ($project in $catalogue.projects) {
                $identity = [string]$project.id
                $saved = $null
                if (!$expected.TryGetValue($identity, [ref]$saved) -or
                    $saved.code -cne $project.code -or $saved.title -cne $project.title -or
                    $saved.status -cne $project.status) {
                    throw 'Le catalogue Agent ne correspond pas aux projets ERP releves avant la bascule.'
                }
                [void]$expected.Remove($identity)
            }
            if ($expected.Count) { throw 'Certains projets ERP manquent dans le catalogue Agent.' }
        }
        Write-Output "Service Agent actif. Projets dans le catalogue : $(@($catalogue.projects).Count)."
    }
    $remote = Invoke-RestMethod ($url + '/api/remote') -TimeoutSec 5
    if (!$remote.gateway_available -or ($remote.enabled -and !$remote.connection.running)) {
        throw 'La passerelle Kiara ou son tunnel WireGuard doit etre verifie apres le redemarrage.'
    }
    if (Test-Path -LiteralPath $pendingRelease -PathType Leaf) {
        $releaseStatus = Invoke-RestMethod ($url + '/api/releases') -TimeoutSec 10
        $publishRelease = @'
import sys
from pathlib import Path

root, data = map(Path, sys.argv[1:3])
sys.path[:0] = [str(root / 'lanceur'), str(root / 'shared')]
from releases import VERSION, publish_pending
if VERSION != sys.argv[3]:
    raise SystemExit('Le lanceur actif ne correspond pas a la mise a jour en attente.')
number = publish_pending(data)
if number:
    print(f'Mise a jour Kiara classique {number} publiee.')
'@
        $publishRelease | & $python - $root $dataDirectory $releaseStatus.server_version
        if ($LASTEXITCODE -ne 0) { throw 'Publication de la mise a jour Kiara en attente.' }
    }
}
if (!$SansNavigateur) { Start-Process $url }
Write-Output "Interface disponible : $url. Le serveur LLM conserve son etat."
