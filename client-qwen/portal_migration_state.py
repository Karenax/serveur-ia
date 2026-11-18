"""Encrypted, non-destructive checkpoints for migrated browser origins.

The caller must hold the desktop profile lock and supply OS-backed encryption.
Checkpoints contain only source counts and hashes, never draft values.
"""
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from portal_origin_state import FIRST_PORT,LAST_PORT


class MigrationStateError(RuntimeError):
    pass


def _validate(value):
    if (not isinstance(value,dict) or type(value.get('format')) is not int or value.get('format') not in (1,2,3,4,5,6)
            or set(value)!=({'format','profile','port','sources'} if value['format']==1
                            else {'format','profile','port','sources','protected','destinationArchives'} if value['format']==6
                            else {'format','profile','port','sources','protected'})
            or type(value['port']) is not int
            or not isinstance(value['profile'],str) or not re.fullmatch(r'[0-9a-f]{20}',value['profile'])
            or not FIRST_PORT<=value['port']<=LAST_PORT or not isinstance(value['sources'],list)
            or len(value['sources'])>20):
        raise ValueError('invalid checkpoint')
    sources=[];seen=set()
    for item in value['sources']:
        counts=('localEntries','audioChunks','audioArchives') if value['format'] in (5,6) else ('localEntries','audioChunks')
        if (not isinstance(item,dict) or set(item)!={'engine','port','digest',*counts}
                or item['engine'] not in ('qt','tauri') or type(item['port']) is not int
                or not FIRST_PORT<=item['port']<=LAST_PORT
                or (item['engine']=='tauri' and item['port']==value['port'])
                or any(type(item[key]) is not int or not 0<=item[key]<=9007199254740991 for key in counts)
                or (value['format'] in (5,6) and item['audioArchives']>3000)
                or not isinstance(item['digest'],str) or not re.fullmatch(r'[0-9a-f]{64}',item['digest'])):
            raise ValueError('invalid source')
        identity=(item['engine'],item['port'])
        if identity in seen:raise ValueError('duplicate source')
        seen.add(identity);sources.append(dict(item))
    result={'format':value['format'],'profile':value['profile'],'port':value['port'],
            'sources':sorted(sources,key=lambda item:(item['engine'],item['port']))}
    if value['format'] in (2,3,4,5,6):
        protected=value['protected']
        if not isinstance(protected,list) or (not protected and value['format'] not in (5,6)) or len(protected)>len(sources):raise ValueError('invalid protection')
        guarded=[];guarded_seen=set()
        for entry in protected:
            if (not isinstance(entry,dict) or set(entry)!=({'engine','port'} if value['format']==2 else {'engine','port','ids'})
                    or entry['engine'] not in ('qt','tauri') or type(entry['port']) is not int):
                raise ValueError('invalid protection')
            identity=(entry['engine'],entry['port'])
            if identity not in seen or identity in guarded_seen:raise ValueError('invalid protection')
            if value['format'] in (3,4,5,6):
                ids=entry['ids']
                if (not isinstance(ids,list) or not ids or len(ids)>1024
                        or any(not isinstance(item,str) or not re.fullmatch(
                            r'(?:audio-)?[0-9a-f]{64}' if value['format'] in (4,5,6) else r'[0-9a-f]{64}',item) for item in ids)
                        or len(set(ids))!=len(ids)):raise ValueError('invalid archive ids')
                guarded.append({'engine':entry['engine'],'port':entry['port'],'ids':sorted(ids)})
            else:guarded.append(dict(entry))
            guarded_seen.add(identity)
        if value['format'] in (3,4,5,6) and sum(len(item['ids']) for item in guarded)>3000:raise ValueError('too many archive ids')
        result['protected']=sorted(guarded,key=lambda item:(item['engine'],item['port']))
    if value['format']==6:
        ids=value['destinationArchives']
        if (not isinstance(ids,list) or len(ids)>3000
                or any(not isinstance(item,str) or not re.fullmatch(r'[0-9a-f]{64}',item) for item in ids)
                or len(set(ids))!=len(ids)):
            raise ValueError('invalid destination archive ids')
        required={identifier[6:] for item in result['protected'] for identifier in item['ids'] if identifier.startswith('audio-')}
        if not required <= set(ids):raise ValueError('missing protected destination archives')
        result['destinationArchives']=sorted(ids)
    return result


def read_state(path,profile,decrypt):
    """Missing means unknown; invalid or unreadable is never treated as empty."""
    if not callable(decrypt) or not isinstance(profile,str) or not re.fullmatch(r'[0-9a-f]{20}',profile):
        raise ValueError('Déchiffrement invalide.')
    path=Path(path)
    try:
        if path.is_symlink():raise MigrationStateError('Suivi de migration illisible.')
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0))
    except FileNotFoundError:return None
    except OSError as error:raise MigrationStateError('Suivi de migration illisible.') from error
    try:
        with os.fdopen(fd,'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise MigrationStateError('Suivi de migration illisible.')
            encrypted=stream.read(1024*1024+1)
        if not encrypted or len(encrypted)>1024*1024:raise ValueError('invalid size')
        plain=decrypt(encrypted)
        if not isinstance(plain,bytes) or not plain or len(plain)>256*1024:raise ValueError('invalid plaintext')
        def unique(pairs):
            result={}
            for key,item in pairs:
                if key in result:raise ValueError('duplicate field')
                result[key]=item
            return result
        value=_validate(json.loads(plain.decode('utf-8'),object_pairs_hook=unique))
        if value['profile']!=profile:raise ValueError('different profile')
        return value
    except MigrationStateError:raise
    except Exception as error:raise MigrationStateError('Le suivi de migration est illisible ; les sources sont conservées.') from error


def write_state(path,profile,port,sources,encrypt,decrypt,*,protected=(),archives=None,extended=False,destination_archives=None):
    """Atomically replace a previously validated encrypted checkpoint."""
    if not callable(encrypt) or not callable(decrypt) or type(extended) is not bool:raise ValueError('Chiffrement invalide.')
    if not isinstance(protected,(list,tuple,set,frozenset)):raise ValueError('Protection de migration invalide.')
    try: guarded=[{'engine':engine,'port':source_port} for engine,source_port in protected]
    except (TypeError,ValueError) as error:raise ValueError('Protection de migration invalide.') from error
    if archives is not None:
        if guarded or not isinstance(archives,dict):raise ValueError('Protection de migration invalide.')
        try:
            guarded=[{'engine':engine,'port':source_port,'ids':sorted(ids)}
                     for (engine,source_port),ids in archives.items()]
        except (TypeError,ValueError) as error:raise ValueError('Protection de migration invalide.') from error
    # Format 4 distinguishes audio archive fingerprints from older local-value
    # fingerprints. It remains experimental until the receiver can verify both.
    has_audio=archives is not None and any(isinstance(item,str) and item.startswith('audio-')
                                           for entry in guarded for item in entry['ids'])
    extended=extended or (isinstance(sources,list) and any(isinstance(item,dict) and 'audioArchives' in item for item in sources))
    if destination_archives is not None:
        if not extended or not isinstance(destination_archives,(list,tuple,set,frozenset)):
            raise ValueError('Copies de destination invalides.')
    if extended and guarded and archives is None:raise ValueError('Protection de migration invalide.')
    value={'format':6 if destination_archives is not None else 5 if extended else (4 if has_audio else 3 if archives is not None else 2) if guarded else 1,
           'profile':profile,'port':port,'sources':sources}
    if guarded or extended:value['protected']=guarded
    if destination_archives is not None:value['destinationArchives']=list(destination_archives)
    path=Path(path);value=_validate(value)
    previous=read_state(path,profile,decrypt)
    if previous is not None and previous['port']!=port:
        raise MigrationStateError('Le suivi concerne un autre port local.')
    old_protected={(item['engine'],item['port']) for item in previous.get('protected',[])} if previous else set()
    if not old_protected <= {(item['engine'],item['port']) for item in value.get('protected',[])}:
        raise MigrationStateError('Une protection de copie ne peut pas être retirée automatiquement.')
    if previous and previous['format'] in (5,6) and value['format'] not in (5,6):
        raise MigrationStateError('Le suivi étendu ne peut pas être remplacé automatiquement.')
    if previous and previous['format']==6 and (value['format']!=6
            or not set(previous['destinationArchives']) <= set(value['destinationArchives'])):
        raise MigrationStateError('Une copie audio de destination ne peut pas être retirée automatiquement.')
    if previous and previous['format'] in (3,4,5,6):
        old_ids={(item['engine'],item['port']):set(item['ids']) for item in previous['protected']}
        new_ids={(item['engine'],item['port']):set(item.get('ids',[])) for item in value.get('protected',[])}
        if any(not ids <= new_ids.get(identity,set()) for identity,ids in old_ids.items()):
            raise MigrationStateError('Une empreinte de copie ne peut pas être retirée automatiquement.')
    if previous==value:return value
    name=None
    try:
        payload=json.dumps(value,ensure_ascii=True,separators=(',',':')).encode('utf-8')
        encrypted=encrypt(payload)
        if not isinstance(encrypted,bytes) or not encrypted or len(encrypted)>1024*1024:
            raise ValueError('invalid ciphertext')
        fd,name=tempfile.mkstemp(prefix='.kiara-migration-',suffix='.tmp',dir=path.parent)
        with os.fdopen(fd,'wb') as stream:
            stream.write(encrypted);stream.flush();os.fsync(stream.fileno())
        # The profile lock prevents other recent clients from writing here.
        os.replace(name,path);name=None
        if os.name!='nt':
            directory=os.open(path.parent,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
            try:os.fsync(directory)
            finally:os.close(directory)
    except Exception as error:
        if isinstance(error,MigrationStateError):raise
        raise MigrationStateError('Le suivi de migration ne peut pas être enregistré.') from error
    finally:
        if name is not None:
            try:os.unlink(name)
            except FileNotFoundError:pass
    if read_state(path,profile,decrypt)!=value:raise MigrationStateError('Le suivi de migration ne peut pas être vérifié.')
    return value
