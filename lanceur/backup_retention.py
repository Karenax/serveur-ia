"""Recoverable retention of verified, paired backup files.

The journal is written before any rename. Until the catalogue commit, a later
start restores every staged file; after the commit it finishes the deletion.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import secrets

from core import write_json

NAME = re.compile(r'^fred-\d{8}-\d{6}-([0-9a-f]{24})\.qwenbackup$')
HEX64 = re.compile(r'^[0-9a-f]{64}$')
WARNING = 'Un nettoyage de sauvegardes reste à reprendre. Vérifiez les accès aux dossiers, puis redémarrez le serveur.'


def entries(record):
    """Validate the complete set of paths and hashes without touching files."""
    if not isinstance(record, dict): raise ValueError('Invalid retention record')
    main = Path(record['file'])
    match = NAME.fullmatch(main.name)
    if not main.is_absolute() or not match or match.group(1) != record['id']:
        raise ValueError('Invalid retention name')
    digest = record['sha256']
    if not isinstance(digest, str) or not HEX64.fullmatch(digest): raise ValueError('Invalid hash')
    secondary = record.get('secondary') or {}
    other = Path(secondary['file']) if secondary.get('file') else None
    if secondary.get('status') == 'copied' and other is None: raise ValueError('Missing copy')
    if other and (not other.is_absolute() or other.name != main.name or os.path.normcase(str(other)) == os.path.normcase(str(main))):
        raise ValueError('Invalid copy')
    files = [(main, digest)]
    if other: files.append((other, digest))
    agent = record.get('agent')
    if agent:
        expected = main.with_suffix('.kiara-agent')
        agent_hash = agent['sha256']
        if Path(agent['file']) != expected or not isinstance(agent_hash, str) or not HEX64.fullmatch(agent_hash):
            raise ValueError('Invalid project archive')
        files.append((expected, agent_hash))
        if other: files.append((other.with_suffix('.kiara-agent'), agent_hash))
    return files


def _exists(path):
    try:
        path.stat()
        return True
    except FileNotFoundError:
        return False


def _sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): digest.update(block)
    return digest.hexdigest()


def _journal_path(manager):
    return manager.directory / 'retention-en-cours.json'


def recover(manager):
    """Return false and preserve the journal if recovery needs intervention."""
    journal = _journal_path(manager)
    try:
        if not _exists(journal):
            manager.data['retention_warning'] = ''
            return True
        with journal.open('rb') as stream: raw = stream.read(65537)
        if len(raw) > 65536: raise ValueError('Oversized retention journal')
        document = json.loads(raw)
        if not isinstance(document, dict) or document.get('version') != 1:
            raise ValueError('Invalid retention journal')
        token = document['token']
        if not isinstance(token, str) or not re.fullmatch(r'[0-9a-f]{32}', token):
            raise ValueError('Invalid retention token')
        record = document['record']
        files = entries(record)
        matches = [item for item in manager.data['catalog'] if item.get('id') == record['id']]
        if len(matches) > 1 or (matches and matches[0] != record):
            raise ValueError('Ambiguous retention record')
        staged = [(original, original.with_name(original.name + '.kiara-prune-' + token), digest)
                  for original, digest in files]
        # A disconnected share must not be mistaken for already-deleted files.
        for parent in {original.parent for original, _, _ in staged}:
            with os.scandir(parent):
                pass
        if matches:
            # Never overwrite a file that appeared since preparation began.
            states = [(_exists(original), _exists(stage)) for original, stage, _ in staged]
            if any(original == stage for original, stage in states):
                raise ValueError('Incomplete or conflicting retention files')
            for (original, stage, _), (_, has_stage) in zip(staged, states):
                if has_stage: os.rename(stage, original)
        else:
            # Catalogue commit succeeded: only delete the exact staged bytes.
            for original, stage, digest in staged:
                if _exists(original): raise ValueError('Unexpected original after commit')
                if _exists(stage) and _sha256(stage) != digest: raise ValueError('Staged file changed')
            for _, stage, _ in staged:
                try: stage.unlink()
                except FileNotFoundError: pass
        journal.unlink()
        manager.data['retention_warning'] = ''
        return True
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
        manager.data['retention_warning'] = WARNING
        return False


def remove(manager, record):
    """Stage one already-verified record, commit its removal, then clean up."""
    if not recover(manager): return False
    files = entries(record)
    # Recovery must be able to distinguish a prepared operation from a commit.
    manager._save()
    token = secrets.token_hex(16)
    journal = _journal_path(manager)
    document = {'version': 1, 'token': token, 'record': copy.deepcopy(record)}
    write_json(journal, document)
    try:
        for original, _ in files:
            stage = original.with_name(original.name + '.kiara-prune-' + token)
            if _exists(stage): raise FileExistsError('Retention staging collision')
            os.rename(original, stage)
    except OSError:
        recover(manager)
        raise
    index = manager.data['catalog'].index(record)
    manager.data['catalog'].pop(index)
    try:
        manager._save()
    except BaseException:
        # The commit outcome may be unknown; recovery must consult the on-disk
        # catalogue at the next start, without deleting or overwriting files.
        manager.data['catalog'].insert(index, record)
        manager.data['retention_warning'] = WARNING
        raise
    recover(manager)
    return True
