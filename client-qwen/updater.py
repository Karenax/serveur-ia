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

VERSION='3.5.34'
AGENT_PROTOCOL=4

def client_filename(number,name):
    version(number)
    label=re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]','-',str(name)).strip(' .')[:80] or 'Client'
    return f'Accès serveur Fred {number} - {label}.exe'

def recipient_name(profile,path,release):
    for value in (release.get('client_name'),profile.get('client_name')):
        if isinstance(value,str) and value.strip():return value
    stem=re.sub(r'(?:\.previous-\d+\.\d+\.\d+)+$','',path.stem)
    match=re.fullmatch(r'Accès serveur Fred v?\d+\.\d+\.\d+ - (.+)',stem)
    return match.group(1) if match else 'Client'

def verify(release, pinned):
    if not isinstance(release,dict) or type(release.get('bytes')) is not int or not 1<=release['bytes']<=256*1024*1024:
        raise ValueError('Taille de mise à jour invalide.')
    if type(release.get('protocol')) is not int or release['protocol'] not in (3,4):raise ValueError('Version incompatible.')
    version(release.get('version'))
    if not isinstance(release.get('sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',release['sha256']):raise ValueError('Empreinte de mise à jour invalide.')
    canonical=json.dumps({k:release[k] for k in ('version','protocol','sha256','bytes')},sort_keys=True,separators=(',',':')).encode()
    try:Ed25519PublicKey.from_public_bytes(base64.b64decode(pinned,validate=True)).verify(base64.b64decode(release['signature'],validate=True),canonical)
    except Exception as error:raise ValueError('Signature de mise à jour invalide.') from error
    return release

def version(value):
    try:
        if not isinstance(value,str) or not re.fullmatch(r'(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})',value):raise ValueError()
        parts=value.split('.')
        return tuple(int(x) for x in parts)
    except (ValueError,AttributeError):raise ValueError('Numéro de version invalide.')

def check(remote):
    pinned=remote.profile.get('update_public_key')
    if not pinned:raise ValueError('Redistribuer une fois le nouveau client signé depuis le serveur.')
    with remote.open('/v1/client/release') as response:release=json.loads(response.read(16384))
    verify(release,pinned)
    return {**release,'available':version(release['version'])>version(VERSION),'current':VERSION}

def download(remote, release, directory):
    verify(release,remote.profile['update_public_key'])
    target=Path(directory)/'QwenClient.base.exe';total=0;digest=hashlib.sha256()
    try:
        with remote.open('/v1/client/download') as response,target.open('wb') as stream:
            while block:=response.read(1024*1024):
                total+=len(block)
                if total>release['bytes']:raise ValueError('Téléchargement trop volumineux.')
                digest.update(block);stream.write(block)
        if total!=release['bytes'] or digest.hexdigest()!=release['sha256']:raise ValueError('Fichier reçu incomplet ou altéré.')
        return target
    except Exception:
        target.unlink(missing_ok=True);raise

def prepare(remote, protect):
    if not getattr(sys,'frozen',False):raise ValueError('La mise à jour s’applique au client EXE compilé.')
    release=check(remote)
    if not release['available']:raise ValueError('Le client est déjà à jour.')
    directory=Path(tempfile.mkdtemp(prefix='qwen-update-',dir=Path(sys.executable).parent))
    try:
        source=download(remote,release,directory)
        helper=directory/'QwenUpdate.exe';shutil.copyfile(sys.executable,helper)
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
        for path in directory.iterdir():path.unlink(missing_ok=True)
        directory.rmdir();raise

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
    import psutil
    plan_path=Path(plan_path).resolve();directory=Path(sys.executable).resolve().parent
    trusted=read_profile();plan=json.loads(protect(plan_path.read_bytes(),decrypt=True))
    if not isinstance(plan,dict):raise ValueError('Plan de mise à jour invalide.')
    target=Path(plan['target']).resolve();source=Path(plan['source']).resolve()
    if plan_path.parent!=directory or source.parent!=directory or source.name!='QwenClient.base.exe' or target.parent!=directory.parent or target.suffix.lower()!='.exe':raise ValueError('Chemins de mise à jour invalides.')
    if plan['profile']!=trusted or personal_profile(target)!=trusted:raise ValueError('Profil de mise à jour invalide.')
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
        installed=target.with_name(client_filename(release['version'],name))
        if installed!=target and installed.exists():raise ValueError('Le fichier '+installed.name+' existe déjà. Utiliser ce client ou le déplacer avant de réessayer.')
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
        backup_directory=target.parent/'Sauvegardes client Fred'/hashlib.sha256(trusted['token'].encode()).hexdigest()[:12]/trusted.get('version',VERSION)
        backup_directory.mkdir(parents=True,exist_ok=True)
        backup=backup_directory/target.name
        if backup.exists() and digest(backup)!=digest(target):raise ValueError('Une archive de retour différente existe déjà.')
        if not backup.exists():shutil.copyfile(target,backup)
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
        if installed!=target:target.unlink()
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
            if installed!=target:installed.unlink(missing_ok=True)
            rollback=directory/'rollback.exe';shutil.copyfile(backup,rollback);replace_retry(rollback,target)
        if not running() and personal_profile(target)==trusted:
            subprocess.Popen([str(target)],creationflags=0x08000000,close_fds=True)
        raise
    else:
        try:(target.parent/'QwenClient-update-result.json').write_text(json.dumps({'version':release['version'],'file':installed.name,'ok':True}),encoding='utf-8')
        except OSError:pass
    finally:
        plan_path.unlink(missing_ok=True);source.unlink(missing_ok=True);staged.unlink(missing_ok=True)
