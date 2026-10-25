"""Durable, owner-scoped notifications for connected clients and the console.

The inbox is part of the existing Workspace SQLite transaction. No message,
document excerpt, API secret or externally supplied URL enters a notification.
Delivery is polling/reconnection, not an external push service.
"""
from __future__ import annotations

import json
import math
import re
import secrets
import sqlite3
import time

MAX_OWNER = 1000
MAX_GLOBAL = 20000
RETENTION_DAYS = 90
MAX_PAGE = 100
JOB_ATTEMPT_PREFIX = 'job_attempt:'
MAX_JOB_ATTEMPT = 2 ** 63 - 1

CLIENT_TYPES = {
    'assistant_reminder': ('Rappel', 'Un rappel ou un travail programmé est arrivé à échéance.'),
    'job_completed': ('Tâche terminée', 'Un résultat est disponible dans vos tâches.'),
    'job_failed': ('Tâche interrompue', 'Consultez votre tâche pour connaître son état.'),
    'document_indexed': ('Document prêt', 'Le document peut être recherché et consulté.'),
    'transcription_ready': ('Transcription disponible', 'Un texte transcrit est prêt à être consulté.'),
}
ADMIN_TYPES = {
    'backup_failed': ('Sauvegarde échouée', 'Consultez les sauvegardes dans la console serveur.'),
    'backup_copy_failed': ('Seconde copie à reprendre', 'La copie de sauvegarde demande votre attention.'),
    'storage_low': ('Stockage à contrôler', 'Vérifiez l’espace disponible dans la console serveur.'),
    'restore_failed': ('Restauration à contrôler', 'Consultez la récupération dans la console serveur.'),
}

SCHEMA = '''
CREATE TABLE IF NOT EXISTS notifications(seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, owner TEXT NOT NULL, type TEXT NOT NULL, source_key TEXT NOT NULL, target TEXT NOT NULL, created REAL NOT NULL, read_at REAL, UNIQUE(owner,source_key));
CREATE TABLE IF NOT EXISTS notification_preferences(owner TEXT PRIMARY KEY, settings TEXT NOT NULL, revision INTEGER NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS notification_subscriptions(owner TEXT NOT NULL, device TEXT NOT NULL, enabled INTEGER NOT NULL, discreet INTEGER NOT NULL, updated REAL NOT NULL, PRIMARY KEY(owner,device));
CREATE TABLE IF NOT EXISTS notification_deliveries(notification TEXT NOT NULL REFERENCES notifications(id) ON DELETE CASCADE, owner TEXT NOT NULL, device TEXT NOT NULL, delivered REAL NOT NULL, PRIMARY KEY(notification,device));
CREATE INDEX IF NOT EXISTS notification_inbox ON notifications(owner,seq);
'''


def migrate(db):
    """Install only our own statements, without committing the caller transaction."""
    for statement in SCHEMA.split(';'):
        if statement.strip():
            db.execute(statement)


def job_attempt(db, identity):
    """The durable retry number survives clock changes and event-log pruning."""
    row = db.execute('SELECT value FROM settings WHERE key=?', (JOB_ATTEMPT_PREFIX + identity,)).fetchone()
    if row is None:
        return 0
    value = row[0]
    if not isinstance(value, str) or not re.fullmatch('[1-9][0-9]{0,18}', value) or int(value) > MAX_JOB_ATTEMPT:
        raise ValueError('Numéro de tentative sauvegardé invalide.')
    return int(value)


def advance_job_attempt(db, identity):
    _id(identity)
    attempt = job_attempt(db, identity)
    if attempt >= MAX_JOB_ATTEMPT:
        raise ValueError('Nombre maximal de relances atteint.')
    db.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)',
               (JOB_ATTEMPT_PREFIX + identity, str(attempt + 1)))
    return attempt + 1


def prune_job_attempts(db):
    db.execute('DELETE FROM settings WHERE substr(key,1,?)=? AND substr(key,?) NOT IN (SELECT id FROM jobs)',
               (len(JOB_ATTEMPT_PREFIX), JOB_ATTEMPT_PREFIX, len(JOB_ATTEMPT_PREFIX) + 1))


def _owner(value):
    # Current access IDs have 16 hex characters. Test/legacy owner labels remain
    # supported; the authenticated gateway always supplies the real identity.
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', value):
        raise ValueError('Destinataire de notification invalide.')
    return value


def _id(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{32}', value):
        raise ValueError('Identifiant de notification invalide.')
    return value


def _types(owner):
    return ADMIN_TYPES if owner == 'admin' else CLIENT_TYPES


def _target(value, owner):
    if value is None:
        return {'kind': 'notifications'}
    if not isinstance(value, dict) or set(value) - {'kind', 'id', 'project'}:
        raise ValueError('Destination de notification invalide.')
    kind = value.get('kind')
    if kind == 'notifications':
        if set(value) != {'kind'}:
            raise ValueError('Destination de notification invalide.')
    elif kind in ('job', 'document', 'assistant') and owner != 'admin':
        _id(value.get('id'))
        if 'project' in value:
            _id(value['project'])
    else:
        raise ValueError('Destination de notification invalide.')
    return dict(value)


def _preferences(db, owner):
    row = db.execute('SELECT settings,revision FROM notification_preferences WHERE owner=?', (owner,)).fetchone()
    defaults = {'types': {kind: True for kind in _types(owner)}, 'discreet': True}
    if row:
        stored = json.loads(row['settings'])
        defaults['types'].update(stored['types'])
        defaults['discreet'] = stored['discreet']
    return {**defaults, 'revision': row['revision'] if row else 0}


def _subscription(db, owner, device):
    row = db.execute('SELECT enabled,discreet FROM notification_subscriptions WHERE owner=? AND device=?', (owner, device)).fetchone()
    return {'enabled': bool(row['enabled']) if row else True,
            'discreet': bool(row['discreet']) if row else True}


def _prune(db, owner, now):
    db.execute('DELETE FROM notifications WHERE created<?', (now - RETENTION_DAYS * 86400,))
    db.execute('DELETE FROM notifications WHERE owner=? AND seq NOT IN (SELECT seq FROM notifications WHERE owner=? ORDER BY seq DESC LIMIT ?)', (owner, owner, MAX_OWNER))
    db.execute('DELETE FROM notifications WHERE seq NOT IN (SELECT seq FROM notifications ORDER BY seq DESC LIMIT ?)', (MAX_GLOBAL,))


def publish(db, owner, kind, source_key, target=None, now=None):
    """Publish once, inside an existing workspace transaction (server callers)."""
    _owner(owner)
    if kind not in _types(owner):
        raise ValueError('Type de notification interdit pour ce destinataire.')
    if not isinstance(source_key, str) or not 1 <= len(source_key) <= 180 or any(ord(c) < 32 for c in source_key):
        raise ValueError('Clé d’événement invalide.')
    destination = _target(target, owner)
    table = {'job': 'jobs', 'document': 'documents'}.get(destination['kind'])
    if table:
        source = db.execute('SELECT owner,project FROM ' + table + ' WHERE id=?', (destination['id'],)).fetchone()
        if source and (source['owner'] != owner or destination.get('project', source['project']) != source['project']):
            raise ValueError('Destination de notification hors de cet espace.')
    existing = db.execute('SELECT id FROM notifications WHERE owner=? AND source_key=?', (owner, source_key)).fetchone()
    if existing:
        return {'id': existing['id'], 'created': False}
    now = time.time() if now is None else now
    identity = secrets.token_hex(16)
    db.execute('INSERT INTO notifications(id,owner,type,source_key,target,created) VALUES(?,?,?,?,?,?)',
               (identity, owner, kind, source_key, json.dumps(destination, separators=(',', ':')), now))
    _prune(db, owner, now)
    return {'id': identity, 'created': True}


def publish_workspace_event(db, owner, action, identity):
    """Atomic job/index hooks. Generic texts are resolved only during reading."""
    if action in ('job_completed', 'job_failed'):
        job = db.execute('SELECT project FROM jobs WHERE id=? AND owner=?', (identity, owner)).fetchone()
        if job:
            attempt = job_attempt(db, identity)
            source_key = action + ':' + identity + (':attempt:' + str(attempt) if attempt else '')
            return publish(db, owner, action, source_key,
                           {'kind': 'job', 'id': identity, 'project': job['project']})
    if action in ('document_create', 'document_upload', 'document_save'):
        document = db.execute('SELECT project,revision FROM documents WHERE id=? AND owner=?', (identity, owner)).fetchone()
        if document:
            return publish(db, owner, 'document_indexed', 'document_indexed:' + identity + ':' + str(document['revision']),
                           {'kind': 'document', 'id': identity, 'project': document['project']})
    return None


def usage(db, owner=None):
    where = ' WHERE owner=?' if owner is not None else ''
    args = (owner,) if owner is not None else ()
    size = 0
    for table, expression in (
        ('notifications', 'length(CAST(source_key AS BLOB))+length(CAST(target AS BLOB))+120'),
        ('notification_preferences', 'length(CAST(settings AS BLOB))+80'),
        ('notification_subscriptions', '120'),
        ('notification_deliveries', '120'),
    ):
        size += db.execute('SELECT COALESCE(SUM(' + expression + '),0) FROM ' + table + where, args).fetchone()[0]
    attempt_where = ' AND j.owner=?' if owner is not None else ''
    size += db.execute('SELECT COALESCE(SUM(length(CAST(s.key AS BLOB))+length(CAST(s.value AS BLOB))+80),0) '
                       'FROM settings s JOIN jobs j ON j.id=substr(s.key,?) WHERE substr(s.key,1,?)=?' + attempt_where,
                       (len(JOB_ATTEMPT_PREFIX) + 1, len(JOB_ATTEMPT_PREFIX), JOB_ATTEMPT_PREFIX) + args).fetchone()[0]
    return size


def validate(db, owners):
    previous = db.row_factory
    db.row_factory = sqlite3.Row
    try:
        _validate(db, owners)
    except (TypeError, KeyError, json.JSONDecodeError) as error:
        raise ValueError('Notifications sauvegardées invalides.') from error
    finally:
        db.row_factory = previous


def _validate(db, owners):
    """Validate restored data after a separately verified known schema."""
    allowed = set(owners) | {'admin'}
    for row in db.execute('SELECT key FROM settings WHERE substr(key,1,?)=?', (len(JOB_ATTEMPT_PREFIX), JOB_ATTEMPT_PREFIX)):
        identity = _id(row['key'][len(JOB_ATTEMPT_PREFIX):])
        job_attempt(db, identity)
        if not db.execute('SELECT 1 FROM jobs WHERE id=?', (identity,)).fetchone():
            raise ValueError('Tentative sans tâche correspondante.')
    for table in ('notifications', 'notification_preferences', 'notification_subscriptions', 'notification_deliveries'):
        if any(row[0] not in allowed for row in db.execute('SELECT DISTINCT owner FROM ' + table)):
            raise ValueError('Notifications sans accès personnel correspondant.')
    if db.execute('SELECT COUNT(*) FROM notifications').fetchone()[0] > MAX_GLOBAL:
        raise ValueError('Trop de notifications sauvegardées.')
    if db.execute('SELECT owner FROM notifications GROUP BY owner HAVING COUNT(*)>?', (MAX_OWNER,)).fetchone():
        raise ValueError('Trop de notifications pour un destinataire.')
    for row in db.execute('SELECT * FROM notifications'):
        _id(row['id']); _owner(row['owner'])
        if row['type'] not in _types(row['owner']):
            raise ValueError('Type de notification sauvegardée invalide.')
        if not isinstance(row['source_key'], str) or not 1 <= len(row['source_key']) <= 180 or any(ord(c) < 32 for c in row['source_key']):
            raise ValueError('Événement de notification sauvegardé invalide.')
        target = _target(json.loads(row['target']), row['owner'])
        if type(row['seq']) is not int or row['seq'] < 1 or not isinstance(row['created'], (float, int)) or not math.isfinite(row['created']) or row['created'] <= 0:
            raise ValueError('Date de notification sauvegardée invalide.')
        if row['read_at'] is not None and (not isinstance(row['read_at'], (float, int)) or not math.isfinite(row['read_at']) or row['read_at'] < row['created']):
            raise ValueError('Lecture de notification sauvegardée invalide.')
        table = {'job': 'jobs', 'document': 'documents'}.get(target['kind'])
        if table:
            source = db.execute('SELECT owner,project FROM ' + table + ' WHERE id=?', (target['id'],)).fetchone()
            if source and (source['owner'] != row['owner'] or target.get('project', source['project']) != source['project']):
                raise ValueError('Destination de notification dans un autre espace.')
    for row in db.execute('SELECT * FROM notification_preferences'):
        prefs = json.loads(row['settings'])
        if not isinstance(prefs, dict) or set(prefs) != {'types', 'discreet'} or not isinstance(prefs['types'], dict) or set(prefs['types']) - set(_types(row['owner'])) or any(type(value) is not bool for value in prefs['types'].values()) or type(prefs['discreet']) is not bool or type(row['revision']) is not int or row['revision'] < 1:
            raise ValueError('Préférences de notification sauvegardées invalides.')
    for row in db.execute('SELECT * FROM notification_subscriptions'):
        if row['device'] != row['owner'] or row['enabled'] not in (0, 1) or row['discreet'] not in (0, 1):
            raise ValueError('Abonnement de notification sauvegardé invalide.')
    for row in db.execute('SELECT d.*,n.owner AS recipient FROM notification_deliveries d LEFT JOIN notifications n ON n.id=d.notification'):
        if row['device'] != row['owner'] or row['recipient'] != row['owner']:
            raise ValueError('Livraison de notification sauvegardée invalide.')


class Notifications:
    def __init__(self, workspace):
        self.workspace = workspace
        with workspace.db() as db:
            migrate(db)

    def _identity(self, owner, device=None):
        _owner(owner)
        device = owner if device is None else _owner(device)
        if device != owner:
            from workspace import Denied
            raise Denied('Abonnement hors de cet accès personnel.')
        if owner != 'admin' and not self.workspace.valid(owner):
            from workspace import Denied
            raise Denied('Accès aux notifications désactivé.')
        return device

    def _public(self, row, preferences):
        title, body = _types(row['owner'])[row['type']]
        return {'id': row['id'], 'sequence': row['seq'], 'type': row['type'],
                'title': title, 'body': body, 'created': row['created'], 'read_at': row['read_at'],
                'target': json.loads(row['target']), 'enabled': preferences['types'].get(row['type'], True)}

    def snapshot(self, owner, cursor=None, device=None, limit=MAX_PAGE):
        device = self._identity(owner, device)
        if cursor is not None and (type(cursor) is not int or cursor < 0):
            raise ValueError('Curseur de notification invalide.')
        if type(limit) is not int or not 1 <= limit <= MAX_PAGE:
            raise ValueError('Maximum 100 notifications par page.')
        from server_state import generation
        with self.workspace.db() as db:
            self._identity(owner, device)
            if not self.workspace.maintenance:
                _prune(db, owner, time.time())
            preferences = _preferences(db, owner)
            if cursor is None:
                rows = db.execute('SELECT * FROM notifications WHERE owner=? ORDER BY seq DESC LIMIT ?', (owner, limit + 1)).fetchall()
                has_more = len(rows) > limit
                rows = list(reversed(rows[:limit]))
            else:
                rows = db.execute('SELECT * FROM notifications WHERE owner=? AND seq>? ORDER BY seq LIMIT ?', (owner, cursor, limit + 1)).fetchall()
                has_more = len(rows) > limit
                rows = rows[:limit]
            latest = db.execute('SELECT MAX(seq) FROM notifications WHERE owner=?', (owner,)).fetchone()[0] or 0
            marker = generation(self.workspace.home)
            return {'items': [self._public(row, preferences) for row in rows],
                    'cursor': rows[-1]['seq'] if rows else max(cursor or 0, latest), 'has_more': has_more,
                    'unread_count': db.execute('SELECT COUNT(*) FROM notifications WHERE owner=? AND read_at IS NULL', (owner,)).fetchone()[0],
                    'read_ids': [row[0] for row in db.execute('SELECT id FROM notifications WHERE owner=? AND read_at IS NOT NULL ORDER BY seq', (owner,))],
                    'retained_ids': [row[0] for row in db.execute('SELECT id FROM notifications WHERE owner=? ORDER BY seq', (owner,))],
                    'preferences': preferences, 'subscription': _subscription(db, owner, device),
                    'generation': marker['id'], 'restored': marker['restored'],
                    'delivery': {'mode': 'connected', 'push': False},
                    'retention': {'days': RETENTION_DAYS, 'per_owner': MAX_OWNER, 'global': MAX_GLOBAL}}

    def action(self, owner, body, device=None):
        device = self._identity(owner, device)
        if not isinstance(body, dict):
            raise ValueError('Action de notification invalide.')
        action = body.get('action')
        allowed = {'list': {'action', 'after', 'limit'}, 'get': {'action', 'id'},
                   'read': {'action', 'ids'}, 'delivered': {'action', 'ids'},
                   'preferences': {'action', 'revision', 'types', 'discreet'},
                   'subscribe': {'action', 'enabled', 'discreet'}}
        if action not in allowed or set(body) - allowed[action]:
            raise ValueError('Action de notification invalide.')
        if action == 'list':
            return self.snapshot(owner, body.get('after'), device, body.get('limit', MAX_PAGE))
        with self.workspace.db() as db:
            self._identity(owner, device)
            if self.workspace.maintenance:
                from workspace import Denied
                raise Denied('Serveur en maintenance.')
            now = time.time()
            if action == 'get':
                identity = _id(body.get('id'))
                row = db.execute('SELECT * FROM notifications WHERE id=? AND owner=?', (identity, owner)).fetchone()
                if row is None:
                    from workspace import Denied
                    raise Denied('Notification absente ou accès interdit.')
                from server_state import generation
                return {'notification': self._public(row, _preferences(db, owner)), 'generation': generation(self.workspace.home)['id']}
            if action in ('read', 'delivered'):
                identities = body.get('ids')
                if not isinstance(identities, list) or not 1 <= len(identities) <= MAX_PAGE:
                    raise ValueError('Sélection de notifications invalide.')
                identities = list(dict.fromkeys(_id(identity) for identity in identities))
                rows = []
                for identity in identities:
                    row = db.execute('SELECT * FROM notifications WHERE id=? AND owner=?', (identity, owner)).fetchone()
                    if row is None:
                        from workspace import Denied
                        raise Denied('Notification absente ou accès interdit.')
                    rows.append(row)
                # Validate the whole selection before changing any row.
                for row in rows:
                    if action == 'read':
                        db.execute('UPDATE notifications SET read_at=COALESCE(read_at,?) WHERE id=? AND owner=?', (max(now, row['created']), row['id'], owner))
                    elif _subscription(db, owner, device)['enabled'] and _preferences(db, owner)['types'].get(row['type'], True):
                        db.execute('INSERT OR IGNORE INTO notification_deliveries(notification,owner,device,delivered) VALUES(?,?,?,?)', (row['id'], owner, device, now))
                result = {'updated': len(rows)}
            elif action == 'preferences':
                previous = _preferences(db, owner)
                if type(body.get('revision')) is not int or body['revision'] != previous['revision']:
                    from workspace import Conflict
                    raise Conflict('Réglages de notification modifiés ailleurs : rechargez-les.')
                updates = body.get('types', {})
                discreet = body.get('discreet', previous['discreet'])
                if not isinstance(updates, dict) or set(updates) - set(_types(owner)) or any(type(value) is not bool for value in updates.values()) or type(discreet) is not bool:
                    raise ValueError('Réglages de notification invalides.')
                prefs = {'types': {**previous['types'], **updates}, 'discreet': discreet}
                db.execute('INSERT INTO notification_preferences(owner,settings,revision,updated) VALUES(?,?,?,?) ON CONFLICT(owner) DO UPDATE SET settings=excluded.settings,revision=excluded.revision,updated=excluded.updated',
                           (owner, json.dumps(prefs), previous['revision'] + 1, now))
                result = {'saved': True, 'revision': previous['revision'] + 1}
            elif action == 'subscribe':
                enabled = body.get('enabled'); discreet = body.get('discreet', True)
                if type(enabled) is not bool or type(discreet) is not bool:
                    raise ValueError('Abonnement de notification invalide.')
                db.execute('INSERT INTO notification_subscriptions(owner,device,enabled,discreet,updated) VALUES(?,?,?,?,?) ON CONFLICT(owner,device) DO UPDATE SET enabled=excluded.enabled,discreet=excluded.discreet,updated=excluded.updated', (owner, device, int(enabled), int(discreet), now))
                result = {'saved': True}
        return {**result, **self.snapshot(owner, device=device)}

    def publish(self, owner, kind, source_key, target=None):
        with self.workspace.db() as db:
            if self.workspace.maintenance:
                return {'created': False, 'maintenance': True}
            return publish(db, owner, kind, source_key, target)

    def revoke(self, owner, device=None):
        _owner(owner); device = owner if device is None else _owner(device)
        if owner != device:
            raise ValueError('Abonnement hors de cet accès personnel.')
        with self.workspace.db() as db:
            db.execute('DELETE FROM notification_subscriptions WHERE owner=? AND device=?', (owner, device))
            db.execute('DELETE FROM notification_deliveries WHERE owner=? AND device=?', (owner, device))
        return {'removed': True}

    def admin(self):
        return self.snapshot('admin')

    def admin_action(self, body):
        return self.action('admin', body)
