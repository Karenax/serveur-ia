"""Project operations; the caller owns the access and database transaction."""
import base64
import json
import secrets
from pathlib import Path
from workspace_types import Conflict, Denied, identifier, text, MAX_TEXT, HISTORY_RESET_ID
from kiara_shared.attachments import validate_message

def execute(workspace, db, owner, values, now, prepared=None):
    action = values.get("action")
    if action in ('project_create',):
        title = text(values.get('title'), 120, 'Nom')
        limits = workspace.policy(db, owner)
        if db.execute('SELECT COUNT(*) FROM projects WHERE owner=?', (owner,)).fetchone()[0] >= limits['projects']:
            raise ValueError('Limite de projets atteinte.')
        id = secrets.token_hex(16)
        db.execute('INSERT INTO projects VALUES(?,?,?,?,0,1,?)', (id, owner, title, '', now))
        result = {'id': id}
    elif action in ('project_save',):
        p = workspace.own(db, 'projects', values.get('id'), owner)
        if values.get('revision') != p['revision']:
            raise Conflict('Projet modifié ailleurs : rechargez avant de réessayer.')
        title = text(values.get('title'), 120, 'Nom')
        prompt = text(values.get('instructions', ''), 12000, 'Instructions', True)
        if type(values.get('archived', False)) is not bool:
            raise ValueError('Archivage invalide.')
        workspace.quota(db, owner, max(0, len(prompt.encode()) - len(p['instructions'].encode())))
        db.execute('UPDATE projects SET title=?,instructions=?,archived=?,revision=revision+1,updated=? WHERE id=?', (title, prompt, int(values.get('archived', False)), now, p['id']))
        result = {'revision': p['revision'] + 1}
    else:
        raise ValueError('Action inconnue.')
    return result, True
