"""Pinned Ed25519 updates; the detached helper verifies before replacing the EXE."""
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from kiara_shared.releases import DESKTOP_DOWNLOAD, DESKTOP_RELEASE, verify, version, client_filename

from kiara_shared.version import VERSION, AGENT_PROTOCOL


def recipient_name(profile,path,release):
    for value in (release.get('client_name'),profile.get('client_name')):
        if isinstance(value,str) and value.strip():return value
    stem=re.sub(r'(?:\.previous-\d+\.\d+\.\d+)+$','',path.stem)
    match=re.fullmatch(r'Accès serveur Fred v?\d+\.\d+\.\d+ - (.+)',stem)
    return match.group(1) if match else 'Client'



def check(remote):
    pinned=remote.profile.get('update_public_key')
    if not pinned:raise ValueError('Redistribuer une fois le nouveau client signé depuis le serveur.')
    with remote.open('/v1/client/release') as response:release=json.loads(response.read(16384))
    verify(release,pinned)
    return {**release,'available':version(release['version'])>version(VERSION),'current':VERSION}

def desktop_release(remote):
    with remote.open(DESKTOP_RELEASE) as response:
        release = verify(json.loads(response.read(16384)), remote.profile['update_public_key'])
    if version(release['version'])[0] != 4 or release['protocol'] != AGENT_PROTOCOL:
        raise ValueError('Version de Kiara 4 incompatible.')
    return {**release, 'available': version(release['version']) > version(remote.version), 'current': remote.version}


def download(remote, release, directory, *, installer=False):
    verify(release,remote.profile['update_public_key'])
    filename = f"Kiara_{release['version']}_x64-setup.exe" if installer else 'QwenClient.base.exe'
    route = DESKTOP_DOWNLOAD if installer else '/v1/client/download'
    target=Path(directory)/filename;total=0;digest=hashlib.sha256()
    try:
        with remote.open(route) as response,target.open('wb') as stream:
            while block:=response.read(1024*1024):
                total+=len(block)
                if total>release['bytes']:raise ValueError('Téléchargement trop volumineux.')
                digest.update(block);stream.write(block)
        if total!=release['bytes'] or digest.hexdigest()!=release['sha256']:raise ValueError('Fichier reçu incomplet ou altéré.')
        return target
    except Exception:
        target.unlink(missing_ok=True);raise

def prepare_kiara4(remote, folder):
    release = desktop_release(remote)
    if not release['available']:
        raise ValueError('Kiara est à jour.')
    return release, download(remote, release, folder, installer=True)


def installed_kiara4():
    import winreg

    registry = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\Kiara'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry) as key:
        installed, _ = winreg.QueryValueEx(key, 'DisplayVersion')
        folder, _ = winreg.QueryValueEx(key, 'InstallLocation')
    executable = Path(folder.strip('"')) / 'Kiara.exe'
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError('Installation de Kiara introuvable.')
    return installed, executable


def install_kiara4(remote):
    with tempfile.TemporaryDirectory(prefix='kiara-install-') as folder:
        release, installer = prepare_kiara4(remote, folder)
        try:
            completed = subprocess.run([str(installer), '/S'], timeout=600)
        except subprocess.TimeoutExpired as error:
            raise ValueError('Kiara 4 n’a pas confirmé son installation. Réessayez.') from error
        if completed.returncode:
            raise ValueError(f'Installation de Kiara 4 en échec (code {completed.returncode}).')

    installed, executable = installed_kiara4()
    if installed != release['version']:
        raise ValueError('L’installation de Kiara 4 n’a pas été confirmée.')
    return executable


def stage_desktop(remote, root):
    installed, executable = installed_kiara4()
    if installed != remote.version or executable.resolve().parent != Path(sys.executable).resolve().parent:
        raise ValueError('Ouvrez Kiara depuis le menu Démarrer pour installer la mise à jour.')
    root.mkdir(parents=True, exist_ok=True)
    for previous in root.glob('kiara-update-*'):
        if previous.is_dir() and not previous.is_symlink() and not previous.is_junction():
            try:
                if time.time() - previous.stat().st_mtime > 86400:
                    for old in previous.glob('Kiara_4.*_x64-setup.exe'):
                        old.unlink()
                    previous.rmdir()
            except OSError:
                pass
    folder = Path(tempfile.mkdtemp(prefix='kiara-update-', dir=root))
    try:
        return prepare_kiara4(remote, folder)
    except Exception:
        folder.rmdir()
        raise


class DesktopUpdate:
    """Stage a signed installer and hand it to the desktop over its private pipes."""

    def __init__(self, root, commands, events):
        self.root = root
        self.commands = commands
        self.events = events
        self.installer = None

    def stage(self, remote):
        release, installer = stage_desktop(remote, self.root)
        self.installer = installer
        try:
            remote.update_state = {'busy': True, 'message': 'Mise à jour vérifiée. Enregistrement avant redémarrage…'}
            self.events.write(f'KIARA_RELAY_UPDATE {release["sha256"]} {installer}\n'.encode('utf-8'))
            self.events.flush()
        except OSError:
            self.discard()
            raise ValueError('Impossible de fermer Kiara pour la mise à jour. Réessayez.') from None

    def discard(self):
        installer, self.installer = self.installer, None
        if installer is not None:
            try:
                installer.unlink(missing_ok=True)
                installer.parent.rmdir()
            except OSError:
                pass

    def wait(self, remote):
        while command := self.commands.read(1):
            if command == b'u':
                self.installer = None  # Windows installer owns the file until it exits.
                break
            if command == b'c':
                with remote.update_lock, remote.activity_lock:
                    self.discard()
                    remote.applying_update = False
                    remote.update_state = {'busy': False, 'available': True, 'error': True,
                        'message': 'Installation interrompue. Vérifiez vos modifications en cours puis réessayez.'}
        self.discard()


def update_directory(target):
    target=Path(target).resolve()
    return target.parent/target.stem

def work_directory(target,profile):
    """A single persistent sibling directory, owned by this personal client."""
    directory=update_directory(target)
    if directory.is_symlink() or directory.is_junction():raise ValueError('Le dossier de mise à jour ne doit pas être un lien.')
    directory.mkdir(exist_ok=True)
    marker=directory/'client.json'
    owner={'format':1,'client':hashlib.sha256((profile['url']+'\0'+profile['token']).encode()).hexdigest()}
    if marker.exists():
        if json.loads(marker.read_text(encoding='utf-8'))!=owner:raise ValueError('Ce dossier appartient à un autre client.')
    elif any(directory.iterdir()):
        raise ValueError('Le dossier '+directory.name+' existe déjà et contient des fichiers. Renommez ce dossier avant la mise à jour.')
    else:marker.write_text(json.dumps(owner),encoding='utf-8')
    return directory

def prepare(remote, protect):
    if not getattr(sys,'frozen',False):raise ValueError('La mise à jour s’applique au client EXE compilé.')
    release=check(remote)
    if not release['available']:raise ValueError('Le client est déjà à jour.')
    directory=work_directory(sys.executable,remote.profile)
    from file_lock import locked
    with locked(directory/'update'):
        return _prepare(remote,protect,release,directory)

def _prepare(remote,protect,release,directory):
    try:
        source=download(remote,release,directory)
        helper=directory/'QwenUpdate.exe';helper_staged=directory/'helper.tmp'
        shutil.copyfile(sys.executable,helper_staged);replace_retry(helper_staged,helper)
        import psutil
        process=psutil.Process(os.getpid())
        identities=[{'pid':process.pid,'created':process.create_time()}]
        parent=process.parent()
        if parent and Path(parent.exe()).resolve()==Path(sys.executable).resolve():identities.append({'pid':parent.pid,'created':parent.create_time()})
        plan={'target':str(Path(sys.executable).resolve()),'source':str(source.resolve()),'profile':remote.profile,
              'release':release,'pid':os.getpid(),'created':process.create_time(),'processes':identities}
        plan_path=directory/'plan.dpapi';plan_path.write_bytes(protect(json.dumps(plan).encode()))
        subprocess.Popen([str(helper),'--apply-update',str(plan_path)],creationflags=0x08000000,close_fds=True)
        return directory
    except Exception:
        for name in ('plan.dpapi','QwenClient.base.exe','QwenUpdate.exe','helper.tmp'):
            try:(directory/name).unlink(missing_ok=True)
            except OSError:pass
        raise

def personal_profile(path):
    from wg_bridge import validate_profile
    with Path(path).open('rb') as stream:
        stream.seek(-16,2);footer=stream.read(16)
        if footer[4:]!=b'QWENPROFILE1':raise ValueError('Profil personnel absent.')
        size=struct.unpack('<I',footer[:4])[0]
        if not 1<=size<=65536:raise ValueError('Profil personnel invalide.')
        stream.seek(-16-size,2)
        return validate_profile(json.loads(stream.read(size)))

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def replace_retry(source,target):
    deadline=time.monotonic()+10
    while True:
        try:os.replace(source,target);return
        except PermissionError:
            if time.monotonic()>=deadline:raise
            time.sleep(.2)

def apply(plan_path, protect, read_profile):
    from file_lock import locked
    with locked(Path(sys.executable).resolve().parent/'update'):
        return _apply(plan_path,protect,read_profile)

def _apply(plan_path, protect, read_profile):
    import psutil
    plan_path=Path(plan_path).resolve();directory=Path(sys.executable).resolve().parent
    trusted=read_profile();plan=json.loads(protect(plan_path.read_bytes(),decrypt=True))
    if not isinstance(plan,dict):raise ValueError('Plan de mise à jour invalide.')
    target=Path(plan['target']).resolve();source=Path(plan['source']).resolve()
    if plan_path.parent!=directory or source.parent!=directory or source.name!='QwenClient.base.exe' or directory!=update_directory(target) or target.suffix.lower()!='.exe':raise ValueError('Chemins de mise à jour invalides.')
    if plan['profile']!=trusted or personal_profile(target)!=trusted:raise ValueError('Profil de mise à jour invalide.')
    work_directory(target,trusted)
    identities=plan.get('processes',[{'pid':plan['pid'],'created':plan['created']}])
    if not isinstance(identities,list) or not 1<=len(identities)<=2:raise ValueError('Processus client invalide.')
    for identity in identities:
        if type(identity.get('pid')) is not int or not 1<=identity['pid']<2**31 or type(identity.get('created')) not in (float,int) or not 0<=identity['created']<10**12:raise ValueError('Processus client invalide.')
    def running():
        for identity in identities:
            try:
                process=psutil.Process(identity['pid'])
                if abs(process.create_time()-identity['created'])<.01 and process.is_running():return True
            except psutil.NoSuchProcess:pass
        return False
    staged=directory/'QwenClient.personal.exe';backup=None;launched=None;replaced=False;installed=target
    try:
        release=verify(plan['release'],trusted['update_public_key'])
        if version(release['version'])<=version(trusted.get('version',VERSION)):raise ValueError('Version ancienne refusée.')
        if source.stat().st_size!=release['bytes'] or digest(source)!=release['sha256']:raise ValueError('Binaire altéré après téléchargement.')
        name=recipient_name(trusted,target,release)
        deadline=time.monotonic()+60
        while running():
            if time.monotonic()>=deadline:raise ValueError('Le client est encore ouvert. Fermer puis réessayer.')
            time.sleep(.25)
        shutil.copyfile(source,staged)
        profile=dict(trusted);profile.update(version=release['version'],protocol=release['protocol'],client_name=name)
        encoded=json.dumps(profile,ensure_ascii=False).encode()
        with staged.open('ab') as stream:stream.write(encoded+struct.pack('<I',len(encoded))+b'QWENPROFILE1')
        smoke=subprocess.run([str(staged),'--self-test','--with-profile'],timeout=60,creationflags=0x08000000)
        if smoke.returncode:raise ValueError('La nouvelle version a échoué au contrôle de démarrage.')
        backup=directory/'previous.exe'
        backup_staged=directory/'previous.tmp'
        shutil.copyfile(target,backup_staged);replace_retry(backup_staged,backup)
        replace_retry(staged,installed);replaced=True
        acknowledgement=directory/'started.json';acknowledgement.unlink(missing_ok=True)
        launched=subprocess.Popen([str(installed),'--update-ack',str(acknowledgement)],creationflags=0x08000000,close_fds=True)
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if acknowledgement.exists():
                ready=json.loads(acknowledgement.read_text(encoding='utf-8'))
                if ready.get('version')!=release['version'] or not ready.get('ready'):raise ValueError('La nouvelle fenêtre ne confirme pas la version attendue.')
                break
            if launched.poll() is not None:raise ValueError('La nouvelle application s’est arrêtée au démarrage.')
            time.sleep(.25)
        else:raise ValueError('La nouvelle fenêtre n’a pas confirmé son démarrage. Retour à la version précédente.')
    except Exception:
        if replaced:
            if launched and launched.poll() is None:
                try:
                    process=psutil.Process(launched.pid);children=process.children(recursive=True)
                    for child in reversed(children):child.terminate()
                    process.terminate();_,alive=psutil.wait_procs(children+[process],timeout=10)
                    for child in alive:child.kill()
                    _,alive=psutil.wait_procs(alive,timeout=10)
                    if alive:raise ValueError('La nouvelle application reste ouverte. La copie précédente est conservée dans '+backup.name+'.')
                except psutil.NoSuchProcess:pass
            rollback=directory/'rollback.exe';shutil.copyfile(backup,rollback);replace_retry(rollback,target)
        if not running() and personal_profile(target)==trusted:
            subprocess.Popen([str(target)],creationflags=0x08000000,close_fds=True)
        raise
    else:
        try:(directory/'update-result.json').write_text(json.dumps({'version':release['version'],'file':installed.name,'ok':True}),encoding='utf-8')
        except OSError:pass
    finally:
        plan_path.unlink(missing_ok=True);source.unlink(missing_ok=True);staged.unlink(missing_ok=True)
        (directory/'previous.tmp').unlink(missing_ok=True);(directory/'rollback.exe').unlink(missing_ok=True)

def cleanup_legacy_update(acknowledgement,executable=None,timeout=120):
    """Retire only the old helper directory that handed off to this EXE.

    The previous binary creates its random directory before it downloads us.
    Wait until that helper finishes; never recursively delete or scan siblings.
    """
    target=Path(executable or sys.executable).resolve();acknowledgement=Path(acknowledgement).resolve()
    legacy=acknowledgement.parent
    if acknowledgement.name!='started.json' or legacy.parent!=target.parent or not legacy.name.startswith('qwen-update-'):return False
    helper=legacy/'QwenUpdate.exe'
    allowed={'QwenUpdate.exe','QwenClient.base.exe','QwenClient.personal.exe','plan.dpapi','started.json','error.txt'}
    try:
        current=personal_profile(target);old=personal_profile(helper)
        if any(old.get(key)!=current.get(key) for key in ('token','url','wireguard','update_public_key')):return False
        ready=json.loads(acknowledgement.read_text(encoding='utf-8'))
        if not ready.get('ready') or ready.get('version')!=current.get('version'):return False
        directory=work_directory(target,current)
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            files=list(legacy.iterdir())
            if any(not path.is_file() or path.is_symlink() or path.name not in allowed for path in files):return False
            if (legacy/'plan.dpapi').exists():time.sleep(.2);continue
            try:helper.unlink(missing_ok=True)
            except PermissionError:time.sleep(.2);continue
            for path in files:
                if path!=helper:path.unlink(missing_ok=True)
            legacy.rmdir()
            result=target.parent/'QwenClient-update-result.json'
            if result.is_file():
                value=json.loads(result.read_text(encoding='utf-8'))
                if value.get('ok') and value.get('file')==target.name and value.get('version')==current.get('version'):
                    os.replace(result,directory/'update-result.json')
            return True
    except (OSError,ValueError,KeyError):return False
    return False
