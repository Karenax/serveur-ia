"""Locally built releases with SHA-256 integrity and personal-client rollback."""
import hashlib
import json
import re
from pathlib import Path
import shutil
import struct
import subprocess
import time
import threading
import tempfile
from signing import sign,verify,public
from core import HOME
_LOCK=threading.RLock()
_CACHE={}
from core import ROOT, HIDDEN, read_json, write_json
from operations import VERSION
from profiles import match,validate_access
from file_lock import locked
from updater import verify as verify_release

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
    return 'Accès serveur Fred.exe'

def manifest(home=HOME):
    source=ROOT/'client-qwen/dist/Accès serveur Fred.exe'
    result={'version':VERSION,'protocol':3,'sha256':digest(source),'bytes':source.stat().st_size}
    result.update(sign(result,home))
    write_json(source.parent/'release.json',result)
    return result

def status(home):
    source=ROOT/'client-qwen/dist/Accès serveur Fred.exe'
    release=read_json(source.parent/'release.json',{})
    verified=False
    try:
        verify_release(release,public(home,create=False))
        stat=source.stat();key=(str(source),stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns,release['sha256'])
        if key not in _CACHE:
            _CACHE.clear();_CACHE[key]=digest(source)==release['sha256'] and stat.st_size==release['bytes']
        verified=_CACHE[key] and release['version']==VERSION
    except (OSError,ValueError,KeyError,TypeError):pass
    except Exception:pass
    return {'server_version':VERSION, 'release':release,
            'verified':verified,
            'clients':read_json(home/'versions-clients.json',{}),
            'rollback_available':bool(read_json(home/'retour-client.json',{}))}

def repackage(home):
    with _LOCK,locked(home/'versions-clients.json'):return _repackage(home)

def _repackage(home):
    info=status(home)
    if not info['verified']:raise ValueError('Binaire absent, signature invalide ou empreinte différente du manifeste.')
    source=ROOT/'client-qwen/dist/Accès serveur Fred.exe'
    directory=home/'clients';directory.mkdir(exist_ok=True)
    release=info['release'];folder_name='clients-retour-'+release['version']+'-'+release['sha256'][:12]
    archive=home/folder_name
    from wg_crypto import private_directory
    private_directory(archive)
    records=validate_access(read_json(home/'acces-distants.json',{}))['clients']
    restored={};saved=home/'wireguard-prive/profils-restaures.dpapi'
    if saved.exists():
        from wg_crypto import protect
        restored=json.loads(protect(saved.read_bytes(),decrypt=True))
    settings=read_json(home/'wireguard.json',{})
    vault={};vault_path=home/'wireguard-prive/secrets.dpapi'
    if vault_path.exists():
        from wg_crypto import protect
        vault=json.loads(protect(vault_path.read_bytes(),decrypt=True))
    selected=[]
    for record in records:
        if record['revoked']:continue
        target=directory/(record['id']+'.exe')
        values=profile(target) if target.exists() else restored.get(record['id'])
        if values is None:continue
        match(record,values,settings.get('public_key') or None,vault.get('peers',{}).get(record['id']))
        values.update(version=VERSION,protocol=3,update_public_key=public(home),client_name=record['name'])
        selected.append((target,values))
    stage=Path(tempfile.mkdtemp(prefix='preparation-',dir=directory));prepared=[];committed=[]
    original_versions=read_json(home/'versions-clients.json',{})
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
            versions[target.stem]={'version':VERSION,'sha256':digest(target),'epoch':time.time()}
        write_json(home/'versions-clients.json',versions)
        if prepared:write_json(home/'retour-client.json',{'folder':folder_name})
    except Exception:
        for target,previous in reversed(committed):
            if previous.exists():shutil.copyfile(previous,target)
            else:target.unlink(missing_ok=True)
        write_json(home/'versions-clients.json',original_versions)
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
