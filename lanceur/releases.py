"""Locally built releases with SHA-256 integrity and personal-client rollback."""
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import struct
import time
import threading
import tempfile
from signing import sign,public
from core import HOME
_LOCK=threading.RLock()
_CACHE={}
from core import ROOT, read_json, write_json
from operations import VERSION
from profiles import match,validate_access
from kiara_shared.file_lock import locked
from kiara_shared.releases import version, verify as verify_release

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def profile(path):
    with path.open('rb') as f:
        f.seek(-16,2);footer=f.read(16)
        if footer[4:] != b'QWENPROFILE1': raise ValueError('Profil personnel absent.')
        size=struct.unpack('<I',footer[:4])[0]
        if not 1 <= size <= 65536: raise ValueError('Profil personnel invalide.')
        f.seek(-16-size,2)
        return json.loads(f.read(size))

def download_name(path, name):
    from kiara_shared.releases import client_filename
    return client_filename(profile(path)['version'],name)

def manifest(home=HOME):
    source=ROOT/'client-qwen/dist/Accès serveur Fred.exe'
    versioned=release_binary({'version': VERSION})
    if versioned != source:
        raise ValueError('Augmentez la version avant de signer un nouveau client classique.')
    result={'version':VERSION,'protocol':3,'sha256':digest(source),'bytes':source.stat().st_size}
    result.update(sign(result,home))
    write_json(source.parent/'release.json',result)
    return result

DESKTOP_INSTALLER_VERSION = '4.0.22'
DESKTOP_INSTALLER = f'Kiara_{DESKTOP_INSTALLER_VERSION}_x64-setup.exe'


def windows_installer(home, *, stream=None):
    folder = home / 'installateurs'
    release = read_json(folder / f'kiara-{DESKTOP_INSTALLER_VERSION}.json', {})
    try:
        verify_release(release, public(home, create=False))
        if release['version'] != DESKTOP_INSTALLER_VERSION:
            raise ValueError
        source = folder / DESKTOP_INSTALLER
        if stream is None:
            with source.open('rb') as opened:
                _verify_installer(opened, source, release)
        else:
            _verify_installer(stream, source, release)
        return release, source
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError('Installateur Kiara 4 absent ou invalide.') from error


_INSTALLER_CACHE = {}


def _verify_installer(stream, source, release):
    stat = os.fstat(stream.fileno())
    if stat.st_size != release['bytes']:
        raise ValueError
    key = (source, stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, release['sha256'])
    with _LOCK:
        if key not in _INSTALLER_CACHE:
            _INSTALLER_CACHE.clear()
            _INSTALLER_CACHE[key] = hashlib.file_digest(stream, 'sha256').hexdigest() == release['sha256']
            stream.seek(0)
        if not _INSTALLER_CACHE[key]:
            raise ValueError


def release_binary(release):
    directory = ROOT / 'client-qwen/dist'
    number = release['version']
    version(number)
    sha256 = release.get('sha256', '')
    if isinstance(sha256, str) and re.fullmatch('[0-9a-f]{64}', sha256):
        revision = directory / f'Kiara-classique-{number}-{sha256}.exe'
        if revision.is_file():
            return revision
    staged = directory / f'Kiara-classique-{number}.exe'
    return staged if staged.is_file() else directory / 'Accès serveur Fred.exe'


def publish_pending(home=HOME):
    directory = ROOT / 'client-qwen/dist'
    pending = directory / 'release-pending.json'
    with _LOCK, locked(home / 'versions-clients.json'):
        if not pending.is_file():
            return None
        release = verify_release(read_json(pending, {}), public(home, create=False))
        if release['version'] != VERSION:
            raise ValueError('La version en attente diffère du lanceur démarré.')
        source = release_binary(release)
        if source.stat().st_size != release['bytes'] or digest(source) != release['sha256']:
            raise ValueError('Le client classique en attente est incomplet ou altéré.')
        windows_installer(home)
        _repackage(home, release=release, pending=pending)
        return VERSION


def status(home):
    source=ROOT/'client-qwen/dist/Accès serveur Fred.exe'
    release=read_json(source.parent/'release.json',{})
    verified=False
    try:
        verify_release(release,public(home,create=False))
        source=release_binary(release)
        stat=source.stat();key=(str(source),stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns,release['sha256'])
        if key not in _CACHE:
            _CACHE.clear();_CACHE[key]=digest(source)==release['sha256'] and stat.st_size==release['bytes']
        verified=_CACHE[key] and version(release['version']) <= version(VERSION)
    except (OSError,ValueError,KeyError,TypeError):pass
    except Exception:pass
    return {'server_version':VERSION, 'release':release,
            'verified':verified,
            'clients':read_json(home/'versions-clients.json',{}),
            'rollback_available':bool(read_json(home/'retour-client.json',{}))}

def repackage(home):
    with _LOCK,locked(home/'versions-clients.json'):return _repackage(home)

def _repackage(home, *, release=None, pending=None):
    if release is None:
        info=status(home)
        if not info['verified']:raise ValueError('Binaire absent, signature invalide ou empreinte différente du manifeste.')
        release=info['release']
    source=release_binary(release)
    directory=home/'clients';directory.mkdir(exist_ok=True)
    number=release['version'];folder_name='clients-retour-'+release['version']+'-'+release['sha256'][:12]
    archive=home/folder_name
    from wg_crypto import private_directory
    private_directory(archive)
    records=validate_access(read_json(home/'acces-distants.json',{}))['clients']
    restored={};saved=home/'wireguard-prive/profils-restaures.dpapi'
    if saved.exists():
        from wg_crypto import protect
        restored=json.loads(protect(saved.read_bytes(),decrypt=True))
    settings=read_json(home/'wireguard.json',{})
    from wireguard_access import network_routes, UDP_PORT
    routes=network_routes(settings.get('listen_port',UDP_PORT))
    vault={};vault_path=home/'wireguard-prive/secrets.dpapi'
    if vault_path.exists():
        from wg_crypto import protect
        vault=json.loads(protect(vault_path.read_bytes(),decrypt=True))
    selected=[]
    for record in records:
        if record['revoked']:continue
        target=directory/(record['id']+'.exe')
        if record.get('desktop_profile') and not target.exists():continue
        values=profile(target) if target.exists() else restored.get(record['id'])
        if values is None:continue
        match(record,values,settings.get('public_key') or None,vault.get('peers',{}).get(record['id']))
        values.update(version=number,protocol=3,update_public_key=public(home),client_name=record.get('name',values.get('client_name','Client')),local_routes=routes)
        selected.append((target,values))
    stage=Path(tempfile.mkdtemp(prefix='preparation-',dir=directory));prepared=[];committed=[]
    original_versions=read_json(home/'versions-clients.json',{})
    rollback_path=home/'retour-client.json'
    original_rollback=read_json(rollback_path,{})
    versions=dict(original_versions);hashes=read_json(archive/'hashes.json',{})
    try:
        for target,values in selected:
            temporary=stage/target.name;shutil.copyfile(source,temporary)
            encoded=json.dumps(values,ensure_ascii=False).encode()
            with temporary.open('ab') as stream:stream.write(encoded+struct.pack('<I',len(encoded))+b'QWENPROFILE1')
            if target.exists() and digest(target)==digest(temporary):continue
            previous=stage/(target.stem+'.previous')
            if target.exists():
                shutil.copyfile(target,previous)
                old=archive/target.name
                if not old.exists():shutil.copyfile(target,old);hashes[target.name]=digest(old)
                elif digest(old)!=hashes.get(target.name):raise ValueError('Archive précédente altérée.')
            prepared.append((target,temporary,previous))
        if not (archive/'versions.json').exists():write_json(archive/'versions.json',original_versions)
        write_json(archive/'hashes.json',hashes)
        for target,temporary,previous in prepared:
            temporary.replace(target);committed.append((target,previous))
            versions[target.stem]={'version':number,'sha256':digest(target),'epoch':time.time()}
        write_json(home/'versions-clients.json',versions)
        if prepared:write_json(rollback_path,{'folder':folder_name})
        if pending is not None:pending.replace(pending.with_name('release.json'))
    except Exception:
        for target,previous in reversed(committed):
            if previous.exists():shutil.copyfile(previous,target)
            else:target.unlink(missing_ok=True)
        write_json(home/'versions-clients.json',original_versions)
        if prepared:
            if original_rollback:write_json(rollback_path,original_rollback)
            else:rollback_path.unlink(missing_ok=True)
        raise
    finally:
        for temporary in stage.iterdir():temporary.unlink()
        stage.rmdir()
    return {'message':str(len(prepared))+' clients préparés. Distribuer les EXE personnels à leurs destinataires.', 'count':len(prepared)}

def rollback(home):
    with _LOCK,locked(home/'versions-clients.json'):return _rollback(home)

def _rollback(home):
    name=read_json(home/'retour-client.json',{}).get('folder','clients-retour')
    if Path(name).name!=name or not name.startswith('clients-retour'):raise ValueError('Archive de retour invalide.')
    folder=home/name
    if not folder.is_dir():raise ValueError('Aucune version précédente.')
    hashes=read_json(folder/'hashes.json',{})
    sources=list(folder.glob('*.exe'))
    records={r['id']:r for r in read_json(home/'acces-distants.json',{'clients':[]})['clients']}
    sources=[p for p in sources if p.stem in records and not records[p.stem]['revoked']]
    for source in sources:
        if source.name not in hashes or digest(source)!=hashes[source.name]:raise ValueError('Archive de retour non vérifiée. Recompiler et redistribuer si nécessaire.')
        match(records[source.stem],profile(source))
    clients=home/'clients';stage=Path(tempfile.mkdtemp(prefix='retour-',dir=clients));committed=[]
    original_versions=read_json(home/'versions-clients.json',{});versions=dict(original_versions)
    archived_versions=read_json(folder/'versions.json',{})
    try:
        for source in sources:
            target=clients/source.name;temporary=stage/source.name;previous=stage/(source.stem+'.previous')
            shutil.copyfile(source,temporary)
            if target.exists():shutil.copyfile(target,previous)
        for source in sources:
            target=clients/source.name;os_replace=stage/source.name
            os_replace.replace(target);committed.append((target,stage/(source.stem+'.previous')))
            if source.stem in archived_versions:versions[source.stem]=archived_versions[source.stem]
            else:versions.pop(source.stem,None)
        write_json(home/'versions-clients.json',versions)
    except Exception:
        for target,previous in reversed(committed):
            if previous.exists():shutil.copyfile(previous,target)
            else:target.unlink(missing_ok=True)
        write_json(home/'versions-clients.json',original_versions)
        raise
    finally:
        for temporary in stage.iterdir():temporary.unlink()
        stage.rmdir()
    return {'message':str(len(sources))+' versions précédentes restaurées. Redistribuer les EXE.'}

if __name__=='__main__':
    print(json.dumps(manifest()))
