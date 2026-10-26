"""Optional voice pack installation. No ML imports or downloads on application startup."""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import threading
import time
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .http_download import HTTPSRedirect
import urllib.request

PACK_FORMAT = 2
LIMIT = 4 * 1024**3


def canonical(value):
    return json.dumps({k: v for k, v in value.items() if k != 'signature'},
                      ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def relative_path(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or '\x00' in name:
        raise ValueError('Chemin du complément vocal invalide.')
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in name.split('/')):
        raise ValueError('Chemin du complément vocal invalide.')
    if any(re.fullmatch(r'(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?', p, re.I) for p in path.parts):
        raise ValueError('Chemin du complément vocal invalide.')
    return path


def verify_catalogue(value, pinned):
    if not isinstance(value, dict) or value.get('format') != PACK_FORMAT:
        raise ValueError('Complément Max incompatible. Mettez Kiara à jour.')
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(pinned, validate=True)).verify(
            base64.b64decode(value['signature'], validate=True), canonical(value))
    except Exception as error:
        raise ValueError('La signature du complément Max est invalide.') from error
    if not re.fullmatch(r'[a-z0-9-]{1,64}', value.get('revision', '')):
        raise ValueError('Version du complément Max invalide.')
    api=value.get('runtime_api',0)
    if type(api) is not int or not 0<=api<=6:
        raise ValueError('Complément Max incompatible. Mettez Kiara à jour.')
    seen = set()
    for item in [value.get('runtime', {}), *value.get('models', [])]:
        path = relative_path(item.get('name'))
        if str(path).casefold() in seen:
            raise ValueError('Fichiers du complément Max en double.')
        seen.add(str(path).casefold())
        if type(item.get('bytes')) is not int or not 0 < item['bytes'] <= LIMIT:
            raise ValueError('Taille du complément Max invalide.')
        if not re.fullmatch('[a-f0-9]{64}', item.get('sha256', '')):
            raise ValueError('Empreinte du complément Max invalide.')
        if item is not value['runtime']:
            # Models are immutable, public files; runtime code comes only from
            # the authenticated Kiara endpoint and its pinned signing key.
            if not (re.fullmatch(r'https://huggingface\.co/[A-Za-z0-9_./-]+/resolve/[a-f0-9]{40}/[A-Za-z0-9_.-]+', item.get('url', '')) or
                    item.get('name') == 'asr/silero-vad.onnx' and item.get('url') == 'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx'):
                raise ValueError('Source du modèle vocal invalide.')
    entries = value['runtime'].get('files', [])
    if not entries or len(entries) > 3000:
        raise ValueError('Inventaire du complément Max invalide.')
    seen = set()
    for entry in entries:
        path = str(relative_path(entry.get('name')))
        if path.casefold() in seen or type(entry.get('bytes')) is not int or not 0 <= entry['bytes'] <= LIMIT:
            raise ValueError('Inventaire du complément Max invalide.')
        if not re.fullmatch('[a-f0-9]{64}', entry.get('sha256', '')):
            raise ValueError('Inventaire du complément Max invalide.')
        seen.add(path.casefold())
    native='native/kiara-asr.dll' if value.get('runtime_api',0)>=6 else 'native/qwen.dll'
    if 'max-worker.exe' not in seen or native not in seen:
        raise ValueError('Le complément Max est incomplet.')
    if sum(x['bytes'] for x in value['models']) + sum(x['bytes'] for x in entries) > 8 * 1024**3:
        raise ValueError('Complément Max trop volumineux.')
    return value


def matches(path, item):
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size != item['bytes']:
            return False
        with path.open('rb') as source:
            return hashlib.file_digest(source, 'sha256').hexdigest() == item['sha256']
    except OSError:
        return False


def safe_directory(root, path):
    """Never follow a pre-existing junction/symlink while installing executable code."""
    root = Path(root).absolute()
    path = Path(path).absolute()
    if not path.is_relative_to(root):
        raise ValueError('Dossier du complément Max invalide.')
    current = root
    for part in (None, *path.relative_to(root).parts):
        if part is not None:
            current = current/part
        if current.is_symlink() or current.is_junction():
            raise ValueError('Le dossier Max ne doit pas contenir de lien vers un autre dossier.')


def hardware():
    """Offer AMD/NVIDIA; native Vulkan access determines runtime compatibility."""
    command = 'Get-CimInstance Win32_VideoController | Select-Object Name,PNPDeviceID,AdapterRAM | ConvertTo-Json -Compress'
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                                capture_output=True, text=True, timeout=10,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=True)
        data = json.loads(result.stdout[:32768])
        data = data if isinstance(data, list) else [data]
        cards = []
        for item in data:
            identifier = str(item.get('PNPDeviceID', '')).upper()
            vendor = 'nvidia' if 'VEN_10DE' in identifier else 'amd' if 'VEN_1002' in identifier else None
            if vendor:
                cards.append({'vendor': vendor, 'name': str(item.get('Name', vendor))[:120]})
        return {'checked': True, 'eligible': bool(cards), 'cards': cards}
    except (OSError, ValueError, subprocess.SubprocessError, AttributeError):
        return {'checked': True, 'eligible': False, 'cards': [], 'message': 'Carte graphique non identifiée. Réessayez la détection.'}


class MaxInstallation:
    def __init__(self, home, remote, runtime, shared_asr):
        self.home = Path(home)
        self.remote = remote
        self.runtime = runtime
        self.shared_asr = Path(shared_asr)
        self.lock = threading.RLock()
        self.cancelled = threading.Event()
        self.closed = False
        self.thread = None
        self.catalogue = None
        self.plan_id = None
        self.device = {'checked': False, 'eligible': False, 'cards': []}
        self.value = {'phase': 'idle', 'downloaded_bytes': 0, 'message': ''}
        self.storage_cache = None
        threading.Thread(target=self.detect, daemon=True).start()

    def detect(self):
        device = hardware()
        with self.lock:
            self.device = device

    def status(self):
        with self.lock:
            value={**self.value,'hardware':self.device}
        return {**value,'storage':self.storage()}

    def _owned_root(self):
        root=self.home.absolute()
        safe_directory(root,root)
        resolved=root.resolve()
        shared=self.shared_asr.resolve()
        if resolved==Path(resolved.anchor) or resolved==Path.home().resolve() or shared.is_relative_to(resolved) or resolved.is_relative_to(shared):
            raise ValueError('Le dossier Max doit rester séparé des fichiers Low.')
        return root

    def _files(self,root):
        """Reject links/junctions and inspect every resolved deletion target before removal."""
        files=[]
        if not root.exists():return files
        if not root.is_dir():raise ValueError('Le chemin Max doit être un dossier.')
        pending=[root]
        while pending:
            folder=pending.pop()
            for child in folder.iterdir():
                safe_directory(root,child)
                if not child.resolve().is_relative_to(root.resolve()):raise ValueError('Un fichier Max pointe hors de son dossier.')
                if child.is_dir():pending.append(child)
                elif child.is_file():files.append(child)
                else:raise ValueError('Un fichier Max ne peut pas être supprimé automatiquement.')
        return files

    def storage(self):
        now=time.monotonic()
        if self.storage_cache and now-self.storage_cache[0]<5:return dict(self.storage_cache[1])
        root=self.home.absolute();seen=set();size=0;count=0
        try:
            root=self._owned_root()
            # A legacy Python pack can contain tens of thousands of files.
            # Counting its size must not resolve every ancestor of every file,
            # or hold the download's progress lock while doing so. Removal still
            # performs its complete, separate resolved-target validation.
            pending=[root] if root.exists() else []
            while pending:
                folder=pending.pop()
                with os.scandir(folder) as children:
                    for child in children:
                        info=child.stat(follow_symlinks=False)
                        if child.is_symlink() or getattr(info,'st_file_attributes',0)&0x400:
                            raise ValueError('Lien dans le dossier Max.')
                        if child.is_dir(follow_symlinks=False):pending.append(child.path)
                        elif child.is_file(follow_symlinks=False):
                            identity=(info.st_dev,info.st_ino) if info.st_ino else child.path
                            count+=1
                            if identity not in seen:size+=info.st_size;seen.add(identity)
                        else:raise ValueError('Fichier Max non reconnu.')
            value={'path':str(root),'exists':root.is_dir(),'bytes':size,'files':count,'removable':True}
        except (OSError,ValueError):
            value={'path':str(root),'exists':root.is_dir(),'bytes':None,'files':None,'removable':False,
                   'message':'Le dossier contient un fichier ou un lien qui nécessite une vérification manuelle.'}
        self.storage_cache=(time.monotonic(),value)
        return dict(value)

    def open_folder(self):
        root=self._owned_root()
        if not root.is_dir():raise ValueError('Aucun fichier Max n’est installé sur ce PC.')
        os.startfile(str(root))
        return {'opened':True}

    def remove(self):
        with self.lock:
            if self.closed or self.thread and self.thread.is_alive():raise ValueError('Attendez la fin de l’installation Max avant de supprimer ses fichiers.')
            root=self._owned_root()
            self.runtime.begin_maintenance()
            removed=False
            try:
                from .file_lock import locked
                with locked(root/'installation'):
                    self._files(root)
                    self.runtime.unload()
                    # Check again after worker shutdown; only the fixed owned root is deleted.
                    self._files(root)
                    if root.exists():shutil.rmtree(root)
                    removed=True
                    self.catalogue=None;self.plan_id=None;self.storage_cache=None
                    self.value={'phase':'idle','downloaded_bytes':0,'message':'Tous les fichiers Max de ce PC ont été supprimés.'}
            except PermissionError as error:
                raise ValueError('Un fichier Max est encore utilisé. Fermez les autres clients Kiara puis réessayez.') from error
            finally:
                self.storage_cache=None
                self.runtime.end_maintenance(removed)
            return self.status()

    def cached_model(self, item, target):
        candidates = [self.home/'models'/item['name'], target/item['name']]
        if item['name'].startswith('asr/'):
            candidates.append(self.shared_asr/Path(item['name']).name)
        previous = self.runtime.configuration() if hasattr(self.runtime, 'configuration') else {}
        if previous.get('format') == 2:
            root = Path(previous.get('root', '')).absolute()
            if root.is_relative_to(self.home.absolute()):
                candidates.append(root/item['name'])
        return next((path for path in candidates if matches(path, item)), None)

    def plan(self):
        if self.closed:
            raise ValueError('Kiara est en cours de fermeture.')
        if self.thread and self.thread.is_alive():
            raise ValueError('Attendez la fin de l’installation Max.')
        if not self.device['checked']:
            raise ValueError('Détection de la carte graphique en cours. Réessayez.')
        if not self.device['eligible']:
            raise ValueError('Installation locale Max proposée pour les cartes AMD et NVIDIA. Le serveur reste disponible.')
        pinned = self.remote.profile.get('update_public_key')
        if not pinned:
            raise ValueError('Mettez Kiara à jour pour télécharger un complément signé.')
        with self.remote.open('/v1/voice/max/package') as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('Catalogue Max trop volumineux.')
        catalogue = verify_catalogue(json.loads(raw), pinned)
        revision = self.home/'packs'/catalogue['revision']
        models = [item for item in catalogue['models'] if not matches(revision/item['name'], item)]
        reused = sum(item['bytes'] for item in models if self.cached_model(item, revision))
        download = catalogue['runtime']['bytes'] + sum(item['bytes'] for item in models) - reused
        uncached = sum(item['bytes'] for item in models if not self.cached_model(item, revision))
        # Reserve a full copy if the filesystem cannot hard-link the model cache.
        disk = catalogue['runtime']['bytes'] + sum(x['bytes'] for x in catalogue['runtime']['files']) + sum(x['bytes'] for x in models) + uncached + 256*1024**2
        identifier = hashlib.sha256(canonical(catalogue)).hexdigest()
        with self.lock:
            self.catalogue = catalogue
            self.plan_id = identifier
            self.value.update(download_bytes=download, required_disk_bytes=disk, reused_bytes=reused)
        return {'plan': identifier, 'download_bytes': download, 'required_disk_bytes': disk,
                'reused_bytes': reused, 'engine': catalogue.get('engine','Vocal Max'), 'hardware': self.device}

    def install(self, identifier):
        with self.lock:
            if self.closed or self.thread and self.thread.is_alive():
                raise ValueError('Une installation Max est déjà en cours.')
            if not self.catalogue or identifier != self.plan_id:
                raise ValueError('Affichez la taille du téléchargement avant de lancer l’installation.')
            if self.runtime.status()['busy'] or self.runtime.testing:
                raise ValueError('Raccrochez et attendez la fin du test avant d’installer Max.')
            self.cancelled.clear()
            self.value.update(phase='downloading', downloaded_bytes=0, message='Téléchargement de Max…')
            self.thread = threading.Thread(target=self._run, args=(self.catalogue,), daemon=True)
            self.thread.start()
        return self.status()

    def cancel(self):
        self.cancelled.set()
        return self.status()

    def _download(self, source, target, item, done):
        safe_directory(self.home, target.parent)
        if target.is_symlink() or target.is_junction() or target.with_suffix(target.suffix+'.part').is_symlink():
            raise ValueError('Fichier du complément Max invalide.')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and matches(target, item):
            return done + item['bytes']
        part = target.with_suffix(target.suffix+'.part')
        total = 0
        digest = hashlib.sha256()
        with source() as response, part.open('wb') as output:
            while block := response.read(256*1024):
                if self.cancelled.is_set():
                    raise InterruptedError()
                total += len(block)
                if total > item['bytes']:
                    raise ValueError('Le téléchargement Max dépasse la taille annoncée.')
                output.write(block)
                digest.update(block)
                with self.lock:
                    self.value['downloaded_bytes'] = done + total
        if total != item['bytes'] or digest.hexdigest() != item['sha256']:
            raise ValueError('Téléchargement Max incomplet ou altéré. Réessayez.')
        part.replace(target)
        return done + total

    def _extract(self, archive, target, entries):
        inventory = {x['name']: x for x in entries}
        with zipfile.ZipFile(archive) as source:
            files = source.infolist()
            if len(files) != len(inventory) or len({x.filename.casefold() for x in files}) != len(files):
                raise ValueError('Archive Max différente de son inventaire.')
            for item in files:
                relative_path(item.filename)
                expected = inventory.get(item.filename)
                if not expected or item.file_size != expected['bytes'] or stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError('Archive Max invalide.')
            for item in files:
                if self.cancelled.is_set():
                    raise InterruptedError()
                path = target/item.filename
                self._download(lambda: source.open(item), path, inventory[item.filename], 0)

    def _materialize(self, cached, path):
        safe_directory(self.home, path.parent)
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(path.suffix+'.reuse.part')
        if part.is_symlink() or path.is_symlink():
            raise ValueError('Fichier du complément Max invalide.')
        part.unlink(missing_ok=True)
        if cached.absolute().is_relative_to(self.home.absolute()):
            try:
                os.link(cached, part)
            except OSError:
                shutil.copyfile(cached, part)
        else:
            # Low keeps its own independent cache and immutable files.
            shutil.copyfile(cached, part)
        part.replace(path)

    def _run(self, catalogue):
        try:
            from .file_lock import locked
            self.home.mkdir(parents=True, exist_ok=True)
            with locked(self.home/'installation'):
                if self.cancelled.is_set():
                    raise InterruptedError()
                if self.home.is_symlink() or self.home.is_junction():
                    raise ValueError('Le dossier Max doit être un dossier local indépendant.')
                if shutil.disk_usage(self.home).free < self.value['required_disk_bytes']:
                    raise ValueError('Espace disque insuffisant pour Max. Libérez de la place puis réessayez.')
                target = self.home/'packs'/catalogue['revision']
                safe_directory(self.home, target)
                target.mkdir(parents=True, exist_ok=True)
                done = self._download(lambda: self.remote.open('/v1/voice/max/package/download'),
                                      self.home/'runtime.zip', catalogue['runtime'], 0)
                opener = urllib.request.build_opener(HTTPSRedirect())
                for item in catalogue['models']:
                    if self.cancelled.is_set():
                        raise InterruptedError()
                    path = target/item['name']
                    if matches(path, item):
                        continue
                    cached = self.cached_model(item, target)
                    if cached:
                        self._materialize(cached, path)
                    else:
                        cache = self.home/'models'/item['name']
                        done = self._download(lambda i=item: opener.open(i['url'], timeout=30), cache, item, done)
                        self._materialize(cache, path)
                with self.lock:
                    self.value.update(phase='verifying', message='Vérification du complément Max…')
                self._extract(self.home/'runtime.zip', target, catalogue['runtime']['files'])
                manifest = {x['name']: {'bytes': x['bytes'], 'sha256': x['sha256']}
                            for x in [*catalogue['models'], *catalogue['runtime']['files']]}
                configuration = {'format': 2, 'root': str(target), 'asr': str(target/'asr'),
                                 'tts': str(target/'tts'), 'device': 'vulkan', 'manifest': manifest,
                                 'engine': catalogue.get('engine','Whisper Turbo + Phonon français'), 'catalogue': catalogue}
                if self.cancelled.is_set():
                    raise InterruptedError()
                self.runtime.unload()
                temporary = self.home/'runtime.json.part'
                temporary.write_text(json.dumps(configuration, ensure_ascii=False), encoding='utf-8')
                temporary.replace(self.home/'runtime.json')
                with self.lock:
                    self.value.update(phase='testing', message='Vérification de la fluidité de Max…', downloaded_bytes=self.value['download_bytes'])
                self.runtime.test()
                while self.runtime.testing:
                    if self.cancelled.wait(.2) or self.closed:
                        self.runtime.unload()
                        raise InterruptedError()
                status = self.runtime.status()
                with self.lock:
                    self.storage_cache=None
                    self.value.update(phase='ready' if status['available'] else 'limited', message=status['message'])
        except InterruptedError:
            with self.lock:
                self.value.update(phase='cancelled', message='Installation Max arrêtée. Vous pouvez la relancer.')
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            with self.lock:
                self.value.update(phase='cancelled' if self.cancelled.is_set() else 'error',
                    message='Installation Max arrêtée. Vous pouvez la relancer.' if self.cancelled.is_set() else
                    'Téléchargement Max interrompu. Vérifiez votre connexion puis réessayez.')
        except Exception as error:
            with self.lock:
                self.value.update(phase='error', message=str(error) if isinstance(error, ValueError) else
                    'Espace disque insuffisant pour Max. Libérez de la place puis réessayez.' if getattr(error, 'errno', None)==28 or getattr(error, 'winerror', None)==112 else
                    'Installation Max impossible. Vérifiez l’espace libre et les autorisations du dossier, puis réessayez.')

    def close(self):
        self.closed = True
        self.cancelled.set()
