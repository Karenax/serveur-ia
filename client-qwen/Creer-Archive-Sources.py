"""Archive reviewed first-party sources; never package private runtime files."""
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parent.parent
# Git defines the reviewed source boundary and excludes private/runtime files.
# Include newly added sources while preparing a release before its commit.
import subprocess
source_paths = subprocess.check_output([
    'git', '-C', str(root), 'ls-files', '--cached', '--others', '--exclude-standard', '-z',
    'lanceur', 'client-qwen', 'client-android', 'client-voice', 'maintenance', 'dependances',
    'README.md', 'CONTEXTE-PROJET.md', 'HISTORIQUE-PROJET-AVANT-AUDIT-20261012.md',
    'RECONSTRUIRE-FRED.md', 'ARCHIVES-ET-PREUVES.md', 'SOURCES-WIREGUARD.txt', 'Serveur Qwen.cmd', 'Start-Interface-Qwen.ps1'
]).decode('utf-8').split('\0')
suffixes={'.py','.js','.cjs','.html','.css','.md','.txt','.ps1','.cmd','.bat','.go','.mod','.sum','.java','.gradle','.xml','.toml','.properties','.pro','.sh','.c','.cc','.cpp','.h','.hpp','.cmake','.patch','.svg','.ico'}
public_json={'package.json','package-lock.json','model.json','conversation-models.json','ui-package.json','native-manifest.json','build-info.json','moteurs.json'}
files=sorted({name for name in source_paths if name and (root/name).is_file() and
              ((root/name).suffix.lower() in suffixes or (root/name).name in {'gradlew','LICENSE','settings.gradle'}|public_json)})
target=root/'client-qwen/Acces-serveur-Fred-sources.zip'
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
    for name in files:archive.write(root/name,name)
print(target)
