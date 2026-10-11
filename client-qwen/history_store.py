"""Encrypted, atomic history with optimistic concurrency and corruption protection."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import secrets
from file_lock import locked
from chat_attachments import validate_message

LOCK = threading.RLock()
HISTORY_RESET_ID = '20261006-remove-assistants'

class HistoryError(ValueError):
    pass

class HistoryConflict(HistoryError):
    pass

def validate(value):
    if not isinstance(value, dict) or set(value) - {'conversations', 'currentId'}:
        raise HistoryError('Historique invalide.')
    rows = value.get('conversations')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 200:
        raise HistoryError('Conserver entre 1 et 200 conversations.')
    ids = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) - {'id', 'title', 'messages','project_id','document_id','server_revision','archived'}:
            raise HistoryError('Conversation invalide.')
        if 'archived' in row and type(row['archived']) is not bool:
            raise HistoryError('Archivage de conversation invalide.')
        identity, title, messages = row.get('id'), row.get('title'), row.get('messages')
        if not isinstance(identity, str) or not 1 <= len(identity) <= 80 or identity in ids:
            raise HistoryError('Identifiant de conversation invalide ou dupliqué.')
        ids.add(identity)
        for field in ('project_id','document_id'):
            if row.get(field) is not None and (not isinstance(row[field],str) or len(row[field])!=32 or any(c not in '0123456789abcdef' for c in row[field])):raise HistoryError('Projet ou document invalide.')
        if 'server_revision' in row and (type(row['server_revision']) is not int or row['server_revision']<0):raise HistoryError('Révision invalide.')
        if not isinstance(title, str) or not 1 <= len(title) <= 120 or not isinstance(messages, list) or len(messages) > 1000:
            raise HistoryError('Titre ou messages invalides.')
        for message in messages:
            try:validate_message(message)
            except ValueError as error:raise HistoryError(str(error)) from error
            if not isinstance(message, dict) or set(message) - {'role', 'content', 'reasoning_content', 'interrupted', 'attachments', 'turn_id'}:
                raise HistoryError('Message invalide.')
            if message.get('role') not in ('user', 'assistant') or not isinstance(message.get('content'), str):
                raise HistoryError('Message texte attendu.')
            if 'reasoning_content' in message and not isinstance(message['reasoning_content'], str):
                raise HistoryError('Réflexion invalide.')
            if 'interrupted' in message and type(message['interrupted']) is not bool:
                raise HistoryError('État du message invalide.')
    if value.get('currentId') not in ids:
        raise HistoryError('Conversation sélectionnée introuvable.')
    if len(json.dumps(value, ensure_ascii=False).encode()) > 9 * 1024 * 1024:
        raise HistoryError('Historique limité à 9 Mo. Exporter puis supprimer des conversations.')
    return value

def atomic(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

def read(path, protect):
    with LOCK, locked(path):
        try: raw = Path(path).read_bytes()
        except FileNotFoundError: return {'history': None, 'revision': ''}
        try: value = validate(json.loads(protect(raw, decrypt=True)))
        except (OSError, ValueError, TypeError) as error:
            raise HistoryError('Historique illisible : le fichier original est conservé. Exportez vos conversations avant toute récupération.') from error
        return {'history': value, 'revision': hashlib.sha256(raw).hexdigest()}

def write(path, protect, value, revision):
    with LOCK, locked(path):
        current = read(path, protect)
        if revision != current['revision']:
            raise HistoryConflict('Historique modifié par une autre fenêtre. Exportez votre travail puis rechargez le client.')
        raw = protect(json.dumps(validate(value), ensure_ascii=False).encode())
        atomic(path, raw)
        return {'saved': True, 'revision': hashlib.sha256(raw).hexdigest()}

def recover(path,protect,value):
    """Explicit user recovery preserves the unreadable encrypted original."""
    with LOCK,locked(path):
        try:read(path,protect)
        except HistoryError:pass
        else:raise HistoryError('L’historique est lisible. Rechargez le client pour éviter de l’écraser.')
        path=Path(path);original=path.read_bytes();validate(value)
        backup=path.with_name(path.stem+'.unreadable-'+secrets.token_hex(6)+'.dpapi')
        atomic(backup,original)
        raw=protect(json.dumps(value,ensure_ascii=False).encode())
        atomic(path,raw)
        return {'saved':True,'revision':hashlib.sha256(raw).hexdigest(),'backup':backup.name}
