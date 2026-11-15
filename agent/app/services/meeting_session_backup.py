"""Offline chunk closure and safe relocation into a new restored copy only."""
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import sqlite3


def _chunks(database):
    with sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'meeting_session_chunks' not in tables:
            return []
        if 'meeting_sessions' not in tables:
            raise ValueError('Capture sans parent de séance')
        if db.execute('PRAGMA foreign_key_check(meeting_session_chunks)').fetchone():
            raise ValueError('Fragment sans séance valide')
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute('SELECT id,storage_path,sha256,size_bytes FROM meeting_session_chunks')]


def _verify(path, row):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        size = 0
        while block := stream.read(1024 * 1024):
            size += len(block)
            digest.update(block)
    if size != row['size_bytes'] or digest.hexdigest() != row['sha256']:
        raise ValueError('Fragment de capture modifié ou tronqué')


def collect(database, storage):
    root = Path(storage).resolve()
    result = {}
    for row in _chunks(database):
        original = Path(row['storage_path'])
        path = original.resolve()
        if (not path.is_relative_to(root / 'meeting-sessions') or not path.is_file()
                or any(p.is_symlink() or (p.exists() and p.is_junction()) for p in [original, *original.parents] if p.is_relative_to(root))):
            raise ValueError('Fragment absent ou stockage de capture redirigé')
        _verify(path, row)
        result[row['id']] = {'path': 'storage/' + path.relative_to(root).as_posix(),
                             'sha256': row['sha256'], 'size_bytes': row['size_bytes']}
    return result


def validate(database, backup, manifest):
    rows = _chunks(database)
    bindings = manifest.get('meeting_session_files', {})
    if set(bindings) != {row['id'] for row in rows}:
        raise ValueError('Manifeste de captures incomplet')
    for row in rows:
        binding = bindings[row['id']]
        relative = PurePosixPath(binding['path'])
        if (relative.is_absolute() or '..' in relative.parts or '\\' in binding['path'] or ':' in binding['path']
                or relative.as_posix() != binding['path'] or relative.parts[:2] != ('storage', 'meeting-sessions')):
            raise ValueError('Chemin de capture interdit')
        original = Path(backup) / binding['path']
        path = original.resolve()
        if original.is_symlink() or not path.is_relative_to(Path(backup).resolve()) or not path.is_file():
            raise ValueError('Capture de sauvegarde absente ou redirigée')
        if (binding['sha256'], binding['size_bytes']) != (row['sha256'], row['size_bytes']):
            raise ValueError('Empreinte de capture non conforme à sa base')
        if manifest['files'].get(binding['path']) != row['sha256']:
            raise ValueError('Capture non couverte par la sauvegarde')
        _verify(path, row)
    return bindings


def relocate(database, output, bindings):
    with sqlite3.connect(database) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'meeting_sessions' not in tables:
            return
        for identifier, binding in bindings.items():
            db.execute('UPDATE meeting_session_chunks SET storage_path=?,speech_status=CASE WHEN speech_status=? THEN ? ELSE speech_status END WHERE id=?',
                       (str(Path(output) / binding['path']), 'running', 'pending', identifier))
        db.execute("UPDATE meeting_sessions SET state='interrupted',pending_command_id=NULL WHERE state IN ('recording','finalizing')")
        if 'meeting_session_commands' in tables:
            db.execute("UPDATE meeting_session_commands SET status='rejected',error='Restauration sur copie : commande ancienne gelée, vérifier puis créer une nouvelle commande' WHERE status='prepared'")
            db.execute('UPDATE meeting_sessions SET pending_command_id=NULL')
        if 'meeting_session_events' in tables:
            # The offline backup caller invokes relocate only on its new copy.
            # Preserve original owners/receipts; this does not attest closure of
            # any stream on the original installation and is not a release RPC.
            latest = {}
            for sid, kind, packet in db.execute("SELECT session_id,kind,data FROM meeting_session_events WHERE kind IN ('browser.capture.owner','browser.capture.released','browser.capture.frozen-on-copy') ORDER BY id"):
                latest[sid] = (kind, json.loads(packet or '{}'))
            for sid, (kind, packet) in latest.items():
                if kind == 'browser.capture.owner':
                    db.execute("UPDATE meeting_sessions SET state='interrupted' WHERE id=? AND state IN ('recording','paused')", (sid,))
                    revision = db.execute('SELECT revision FROM meeting_sessions WHERE id=?', (sid,)).fetchone()[0]
                    db.execute('INSERT INTO meeting_session_events(session_id,kind,data,revision,created_at) VALUES(?,?,?,?,?)',
                        (sid, 'browser.capture.frozen-on-copy', json.dumps({'owner_id': packet.get('owner_id'),
                            'reason': 'Offline restoration on a new copy; original physical streams not observed'}),
                         revision, datetime.now(timezone.utc).replace(tzinfo=None).isoformat(' ')))
        # A restored copy must never resume microphone or an inference job on
        # the authority of settings captured on another installation.
        row = db.execute("SELECT value FROM app_settings WHERE key='foresight'").fetchone() if 'app_settings' in tables else None
        if row:
            value = json.loads(row[0] or '{}')
            value.update(enabled=False, proactive_enabled=False, auto_enhancement_enabled=False,
                         live_transcription_enabled=False)
            db.execute("UPDATE app_settings SET value=? WHERE key='foresight'", (json.dumps(value),))


def relocate_derived_storage(output):
    """Retain every restored projection/journal, never resume old authority."""
    storage = Path(output).resolve() / 'storage'
    native = storage / 'meeting-sessions' / 'native'
    if native.is_dir():
        for manifest in native.glob('*/*.json'):
            packet = json.loads(manifest.read_text(encoding='utf-8'))
            if packet.get('kind') == 'chunk':
                path = manifest.parent / Path(packet['path']).name
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != packet.get('sha256'):
                    raise ValueError('Journal natif restauré sans original conforme')
                packet['path'] = str(path)
            elif manifest.name == 'capture-request.json':
                packet.update(storage=str(storage), directory=str(manifest.parent))
            else:
                continue
            manifest.write_text(json.dumps(packet, ensure_ascii=False), encoding='utf-8')
