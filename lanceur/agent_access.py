"""Per-device Agent permissions, stored in the existing Workspace database."""

import json
import re

_UNSET = object()
ACCESS_PREFIX = 'agent-access:'


def valid_actor(value):
    return (isinstance(value, str) and bool(re.fullmatch(r'[A-Za-z0-9_.:@-]{1,120}', value))
            and value not in ('kiara-service', 'kiara-thunderbird', 'kiara-thunderbird-reply'))


def valid_grant(value):
    if not isinstance(value, dict) or set(value) not in (
            {'role', 'project_ids', 'person_id'}, {'role', 'project_ids', 'person_id', 'agent_operator_id'}):
        return False
    ids, person, actor = value['project_ids'], value['person_id'], value.get('agent_operator_id')
    return (value['role'] in ('owner', 'editor', 'reader')
            and (ids is None or (isinstance(ids, list) and len(ids) <= 1000
                 and all(isinstance(item, str) and 1 <= len(item) <= 128 for item in ids)))
            and (person is None or (isinstance(person, str) and 1 <= len(person) <= 36))
            and (actor is None or valid_actor(actor)))


def validate_backup(db, owners):
    for key, raw in db.execute("SELECT key,value FROM settings WHERE key GLOB 'agent-access:*'"):
        try:
            if key[len(ACCESS_PREFIX):] in owners and valid_grant(json.loads(raw)):
                continue
        except (TypeError, ValueError):
            pass
        raise ValueError('Habilitation Agent sauvegardée invalide ou sans accès Kiara correspondant.')


class AgentAccess:
    def __init__(self, store):
        self.store = store

    def operator_for(self, owner):
        if not isinstance(owner, str) or not owner or not self.store.valid_owner(owner):
            return None
        with self.store.workspace.db() as db:
            row = db.execute('SELECT value FROM settings WHERE key=?', (ACCESS_PREFIX + owner,)).fetchone()
        if row is None:
            return None
        try:
            value = json.loads(row[0])
            if not valid_grant(value):
                return None
            ids = value['project_ids']
            return {'id': value.get('agent_operator_id') or owner, 'role': value['role'],
                    'project_ids': ids, 'person_id': value['person_id']}
        except (TypeError, ValueError):
            return None

    def set_operator(self, owner, *, role, project_ids, person_id=None, agent_operator_id=None, expected=_UNSET):
        if not isinstance(owner, str) or not owner:
            raise ValueError('Accès Kiara introuvable')
        value = {'role': role, 'project_ids': project_ids, 'person_id': person_id,
                 'agent_operator_id': agent_operator_id}
        if not valid_grant(value):
            raise ValueError('Droits Agent invalides')
        with self.store.lock:
            if not self.store.valid_owner(owner):
                raise ValueError('Accès Kiara introuvable')
            if expected is not _UNSET and self.operator_for(owner) != expected:
                raise ValueError('Les droits ont changé. Rechargez-les avant de les enregistrer.')
            with self.store.workspace.db(owner) as db:
                db.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)',
                           (ACCESS_PREFIX + owner, json.dumps(value, ensure_ascii=False)))

    def revoke(self, owner, *, expected=_UNSET):
        if not isinstance(owner, str) or not owner:
            raise ValueError('Accès Kiara invalide')
        with self.store.lock:
            if expected is not _UNSET and self.operator_for(owner) != expected:
                raise ValueError('Les droits ont changé. Rechargez-les avant de les retirer.')
            with self.store.workspace.db(owner) as db:
                db.execute('DELETE FROM settings WHERE key=?', (ACCESS_PREFIX + owner,))
