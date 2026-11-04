"""Install server-supplied Codex configuration after checking its pinned signature."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

from file_lock import locked
from history_store import atomic
from kiara_shared.releases import verify

FILES={'Installer-Codex-Kiara.ps1','Enregistrer-Cle-Codex-Kiara.ps1',
       'Lire-Cle-Codex-Kiara.ps1','qwen-models.json','manifest.json'}
TARGETS=('config.toml','kiara.config.toml','kiara-models.json','kiara-api-key.dpapi','Lire-Cle-Codex-Kiara.ps1')


def unpack(value,pinned,directory):
    if not isinstance(value,dict):raise ValueError('Téléchargement Codex invalide. Réessayez.')
    release=verify(value.get('release'),pinned)
    if release['bytes']>128*1024:raise ValueError('Fichiers Codex trop volumineux.')
    try:data=base64.b64decode(value['archive'],validate=True)
    except (ValueError,TypeError,KeyError) as error:raise ValueError('Téléchargement Codex incomplet. Réessayez.') from error
    if len(data)!=release['bytes'] or hashlib.sha256(data).hexdigest()!=release['sha256']:
        raise ValueError('Les fichiers Codex n’ont pas pu être vérifiés. Réessayez.')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if set(archive.namelist())!=FILES or len(archive.namelist())!=len(FILES):raise ValueError('Contenu Codex inattendu.')
            if any(item.file_size>128*1024 or item.is_dir() for item in archive.infolist()):raise ValueError('Contenu Codex trop volumineux.')
            manifest=json.loads(archive.read('manifest.json'))
            if manifest.get('kind')!='kiara-codex-setup' or manifest.get('model')!='fred-qwen':raise ValueError('Fichiers incompatibles avec Codex.')
            for name in FILES:(directory/name).write_bytes(archive.read(name))
    except (zipfile.BadZipFile,KeyError,UnicodeError) as error:
        raise ValueError('Téléchargement Codex illisible. Réessayez.') from error


def install(remote,config_path):
    if os.name!='nt':raise ValueError('L’ajout automatique à Codex est disponible sous Windows.')
    pinned=remote.profile.get('update_public_key')
    if not pinned:raise ValueError('La clé de vérification du serveur manque. Mettez à jour le client Kiara.')
    with remote.open('/v1/client/codex') as response:
        raw=response.read(256*1024+1)
    if len(raw)>256*1024:raise ValueError('Téléchargement Codex trop volumineux.')
    value=json.loads(raw)
    path=Path(config_path);directory=path.parent
    with tempfile.TemporaryDirectory(prefix='kiara-codex-setup-') as temporary:
        source=Path(temporary);unpack(value,pinned,source)
        with locked(path):
            before={name:(directory/name).read_bytes() if (directory/name).is_file() else None for name in TARGETS}
            if any(data is not None and len(data)>2*1024*1024 for data in before.values()):
                raise ValueError('Configuration Codex trop volumineuse : fichiers conservés.')
            old_backups=set(directory.glob('config.toml.before-kiara-*')) if directory.exists() else set()
            try:
                result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                    '-File',str(source/'Installer-Codex-Kiara.ps1'),'-CodexDirectory',str(directory),'-Application','-EnregistrerCle'],
                    env=dict(os.environ,KIARA_API_KEY=remote.token),stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if result.returncode:raise ValueError('La configuration de Codex a échoué. Les réglages précédents ont été conservés. Consultez le guide ci-dessous.')
            except (OSError,subprocess.TimeoutExpired,ValueError):
                for name,data in before.items():
                    target=directory/name
                    if data is not None:atomic(target,data)
                    elif target.exists():target.unlink()
                raise
            backups=sorted(str(p) for p in set(directory.glob('config.toml.before-kiara-*'))-old_backups)
    return {'app':'codex','model':'fred-qwen','provider':'kiara','config_path':str(path),'backups':backups,
            'message':'Fournisseur Kiara ajouté. Les réglages ChatGPT par défaut sont conservés. Pour une session Qwen, lancez codex --profile kiara. Votre clé est chiffrée sur ce PC.'}
