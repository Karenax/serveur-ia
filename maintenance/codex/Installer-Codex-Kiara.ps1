param(
    [string]$CodexDirectory = (Join-Path $env:USERPROFILE '.codex'),
    [string]$BaseUrl = 'https://ia.karenax.net/v1',
    [switch]$Application,
    [switch]$EnregistrerCle
)
$ErrorActionPreference = 'Stop'
$endpoint = [Uri]$BaseUrl
if ($endpoint.Scheme -ne 'https' -and !($endpoint.Scheme -eq 'http' -and $endpoint.IsLoopback)) {
    throw 'Utilisez une adresse HTTPS ou une passerelle locale.'
}
New-Item -ItemType Directory -Path $CodexDirectory -Force | Out-Null
$catalog = Join-Path $CodexDirectory 'kiara-models.json'
$profile = Join-Path $CodexDirectory 'kiara.config.toml'
foreach ($target in @($catalog, $profile)) {
    if (Test-Path -LiteralPath $target) {
        Copy-Item -LiteralPath $target -Destination ($target + '.before-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    }
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'qwen-models.json') -Destination $catalog
$catalogToml = ConvertTo-Json ($catalog.Replace('\', '/')) -Compress
$urlToml = ConvertTo-Json ($BaseUrl.TrimEnd('/')) -Compress
$content = @"
model = "fred-qwen"
model_provider = "kiara"
model_catalog_json = $catalogToml
model_reasoning_effort = "none"
model_reasoning_summary = "none"
web_search = "disabled"

[model_providers.kiara]
name = "Qwen via Kiara"
base_url = $urlToml
env_key = "KIARA_API_KEY"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 0
stream_max_retries = 0
stream_idle_timeout_ms = 900000

[agents]
enabled = true
max_concurrent_threads_per_session = 3
default_subagent_model = "fred-qwen"
default_subagent_reasoning_effort = "none"

[features]
apps = false
plugins = false
"@
if ($EnregistrerCle) {
    & (Join-Path $PSScriptRoot 'Enregistrer-Cle-Codex-Kiara.ps1') -CodexDirectory $CodexDirectory
    $resolver = Join-Path $CodexDirectory 'Lire-Cle-Codex-Kiara.ps1'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Lire-Cle-Codex-Kiara.ps1') -Destination $resolver -Force
    $resolverToml = ConvertTo-Json ($resolver.Replace('\', '/')) -Compress
    $auth = @"
[model_providers.kiara.auth]
command = "powershell.exe"
args = ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", $resolverToml]
timeout_ms = 10000
refresh_interval_ms = 300000

[agents]
"@
    $content = $content.Replace('env_key = "KIARA_API_KEY"', '').Replace('requires_openai_auth = false', '').Replace('[agents]', $auth)
}
[IO.File]::WriteAllText($profile, $content + "`n", [Text.UTF8Encoding]::new($false))


# Register an optional provider; do not replace the user's global defaults.
if ($Application) {
    $mainConfig = Join-Path $CodexDirectory 'config.toml'
    $beginMarker = '# BEGIN KIARA PROVIDER'
    $endMarker = '# END KIARA PROVIDER'
    $existing = if (Test-Path -LiteralPath $mainConfig) { [IO.File]::ReadAllText($mainConfig) } else { '' }
    if ($existing -match '(?m)^\s*\[model_providers\.kiara\]' -and !$existing.Contains($beginMarker)) {
        throw 'Un fournisseur kiara existe déjà. Le profil Qwen est disponible ; les réglages existants sont conservés.'
    }
    if ($existing.Contains($beginMarker) -and ($existing.Contains(([string][char]34)*3) -or $existing.Contains(([string][char]39)*3))) {
        throw 'Le fournisseur Kiara existe dans une configuration multiligne. Le profil Qwen est disponible ; les réglages existants sont conservés.'
    }
    $provider = (($content -split '\[model_providers\.kiara\]')[1] -split '\[agents\]')[0]
    $catalogUrlToml = ConvertTo-Json ($BaseUrl.TrimEnd('/') + '/client/codex/models') -Compress
    $provider = "`nmodel_catalog_url = $catalogUrlToml`n" + $provider
    $addition = $beginMarker + "`n[model_providers.kiara]" + $provider + $endMarker + "`n"
    if ($existing.Contains($beginMarker)) {
        $updated = [regex]::Replace($existing, '(?ms)^# BEGIN KIARA PROVIDER\r?\n.*?^# END KIARA PROVIDER\r?\n?', [Text.RegularExpressions.MatchEvaluator]{ param($match) $addition })
    } else {
        $updated = $existing + "`n" + $addition
    }
    if ($updated -ne $existing) {
        if (Test-Path -LiteralPath $mainConfig) {
            Copy-Item -LiteralPath $mainConfig -Destination ($mainConfig + '.before-kiara-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
        }
        [IO.File]::WriteAllText($mainConfig, $updated, [Text.UTF8Encoding]::new($false))
    }
    Write-Output 'Fournisseur Kiara ajouté. Les modèles et les réglages ChatGPT par défaut sont conservés.'
}
Write-Output "Profil Qwen disponible : $profile"
Write-Output 'Session Qwen optionnelle : codex --profile kiara.'
