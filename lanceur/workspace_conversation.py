"""Conversation operations; the caller owns the access and database transaction."""
import base64
import json
import secrets
from pathlib import Path
from workspace_types import Conflict, Denied, identifier, text, MAX_TEXT, HISTORY_RESET_ID
from kiara_shared.attachments import validate_message

def execute(workspace, db, owner, values, now, prepared=None):
    action = values.get("action")
    if action in ('conversation_save',):
        if values.get('reset_id') != HISTORY_RESET_ID:
            raise Conflict('Historique effacé : mettre à jour le client avant de publier une nouvelle discussion.')
        p = workspace.own(db, 'projects', values.get('project'), owner)
        content = values.get('messages')
        if not isinstance(content, list) or len(content) > 1000:
            raise ValueError('Conversation invalide.')
        for message in content:
            validate_message(message)
        encoded = json.dumps(content, ensure_ascii=False)
        if len(encoded.encode()) > 9 * 1024 * 1024:
            raise ValueError('Conversation limitée à 9 Mo.')
        title = text(values.get('title'), 120, 'Nom')
        id = identifier(values.get('id'))
        r = db.execute('SELECT * FROM conversations WHERE id=?', (id,)).fetchone()
        if r and (r['owner'] != owner or r['project'] != p['id']):
            raise Denied('Conversation hors projet.')
        if (r['revision'] if r else 0) != values.get('revision', 0):
            raise Conflict('Conversation modifiée ailleurs. Rechargez avant de publier.')
        if not r and db.execute('SELECT COUNT(*) FROM conversations WHERE owner=?', (owner,)).fetchone()[0] >= 200:
            raise ValueError('Maximum 200 conversations serveur.')
        workspace.quota(db, owner, max(0, len(encoded.encode()) - (len(r['messages'].encode()) if r else 0)))
        revision = r['revision'] + 1 if r else 1
        archived = values.get('archived', bool(r['archived']) if r else False)
        if type(archived) is not bool:
            raise ValueError('Archivage invalide.')
        db.execute('INSERT OR REPLACE INTO conversations(id,owner,project,title,messages,revision,updated,archived) VALUES(?,?,?,?,?,?,?,?)', (id, owner, p['id'], title, encoded, revision, now, int(archived)))
        result = {'revision': revision}
        db.execute('DELETE FROM knowledge_exclusions WHERE owner=? AND conversation=?', (owner, id))
    elif action in ('conversation_move', 'conversation_archive'):
        r = workspace.own(db, 'conversations', values.get('id'), owner)
        if values.get('revision') != r['revision']:
            raise Conflict('Conversation modifiée ailleurs. Rechargez avant de réessayer.')
        if action == 'conversation_move':
            p = workspace.own(db, 'projects', values.get('project'), owner)
            if p['archived']:
                raise ValueError('Projet archivé : restaurez-le avant de déplacer une discussion.')
            db.execute('UPDATE conversations SET project=?,revision=revision+1,updated=? WHERE id=?', (p['id'], now, r['id']))
        else:
            if type(values.get('archived')) is not bool:
                raise ValueError('Archivage invalide.')
            db.execute('UPDATE conversations SET archived=?,revision=revision+1,updated=? WHERE id=?', (int(values['archived']), now, r['id']))
        result = {'revision': r['revision'] + 1}
    elif action in ('conversation_get',):
        r = workspace.own(db, 'conversations', values.get('id'), owner)
        r['messages'] = json.loads(r['messages'])
        return (r, False)
    elif action in ('conversation_delete',):
        r = workspace.own(db, 'conversations', values.get('id'), owner)
        if values.get('revision') != r['revision']:
            raise Conflict('Conversation modifiée ailleurs.')
        history = db.execute('SELECT history FROM client_histories WHERE owner=?', (owner,)).fetchone()
        if history and any((c['id'] == r['id'] for c in json.loads(history[0])['conversations'])):
            db.execute('INSERT OR IGNORE INTO knowledge_exclusions VALUES(?,?)', (owner, r['id']))
        db.execute('DELETE FROM conversations WHERE id=?', (r['id'],))
        result = {'deleted': True}
    else:
        raise ValueError('Action inconnue.')
    return result, True
