"""Create a source-only archive from an explicit list; never package access keys."""
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parent.parent
files=[
 'SOURCES-WIREGUARD.txt',
 'Serveur Qwen.cmd','Start-Interface-Qwen.ps1',
 'lanceur/app.py','lanceur/core.py','lanceur/runtime.py','lanceur/remote.py',
 'lanceur/scheduler.py','lanceur/operations.py','lanceur/releases.py','lanceur/deploy_v2.py',
 'lanceur/signing.py','lanceur/accounts.py','lanceur/profiles.py',
 'lanceur/workspace.py','lanceur/extract_document.py','lanceur/test_workspace.py',
 'lanceur/PLAN-ESPACES-FRED.txt','lanceur/ESPACES-FRED.txt','lanceur/AUDIT-ESPACES-FRED.txt','lanceur/web/workspace.js',
 'lanceur/web/interface.css','lanceur/web/interface.js','lanceur/REFONTE-INTERFACE.txt',
 'lanceur/test_accounts_updates.py','lanceur/test_audit_fred.py','lanceur/AUDIT-FRED.txt',
 'lanceur/verify_fred_native.py','lanceur/verify_fred_update.py',
 'lanceur/verify_workspaces_live.py','lanceur/verify_js.py',
 'lanceur/test_improvements.py','lanceur/CHANGEMENTS-V2.txt',
 'lanceur/wg_crypto.py','lanceur/wireguard_access.py','lanceur/Appliquer-WireGuard.py',
 'lanceur/Autoriser-WireGuard.ps1','lanceur/test_launcher.py','lanceur/test_remote.py',
 'lanceur/LISEZ-MOI.txt','lanceur/LICENSE.txt','lanceur/requirements.txt',
 'lanceur/web/index.html','lanceur/web/app.js','lanceur/web/app.css',
 'client-qwen/client.py','client-qwen/wg_bridge.py','client-qwen/chat.html',
 'client-qwen/workspace.html','client-qwen/ui.css','client-qwen/ui.js',
 'client-qwen/markdown.js','client-qwen/vendor/markdown-it.min.js',
 'client-qwen/vendor/markdown-it-LICENSE.txt','client-qwen/vendor/README.txt',
 'lanceur/test_markdown.js','lanceur/NOUVEAUTES-3.5.0.txt',
 'lanceur/test_history_sync.py',
 'lanceur/test_connection_settings.py','lanceur/test_connection_settings.js',
 'lanceur/preview_conversations.py',
 'client-qwen/corrector.js','client-qwen/history_sync.py',
 'client-qwen/updater.py','client-qwen/product.py','client-qwen/generate_version.py',
 'client-qwen/history_store.py','client-qwen/file_lock.py',
 'client-qwen/draft_store.py',
 'client-qwen/connection_settings.py',
 'client-qwen/app_integrations.py','lanceur/test_app_integrations.py',
 'client-qwen/Build-Client.ps1','client-qwen/Build-WireGuard.ps1',
 'client-qwen/Verifier-Connexion.py','client-qwen/Creer-Archive-Sources.py',
 'client-qwen/Mettre-A-Jour-Clients.py',
 'client-qwen/LISEZ-MOI.txt','client-qwen/LICENSE.txt','client-qwen/THIRD-PARTY.txt',
 'client-qwen/requirements-build.txt','client-qwen/wireguard-bridge/main.go',
 'client-qwen/wireguard-bridge/go.mod','client-qwen/wireguard-bridge/go.sum',
]
target=root/'client-qwen/Acces-serveur-Fred-sources.zip'
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
    for name in files:archive.write(root/name,name)
print(target)
