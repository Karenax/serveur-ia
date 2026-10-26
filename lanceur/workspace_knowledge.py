"""Knowledge operations; the caller owns the access and database transaction."""
import base64
import json
import secrets
from pathlib import Path
from workspace_types import Conflict, Denied, identifier, text, MAX_TEXT, HISTORY_RESET_ID
from kiara_shared.attachments import validate_message

def execute(workspace, db, owner, values, now, prepared=None):
    action = values.get("action")
    if action in ('knowledge_search',):
        project = values.get('project')
        if project:
            p = workspace.own(db, 'projects', project, owner)
            if p['archived']:
                raise ValueError('Projet archivé.')
        query = text(values.get('query'), 2000, 'Question')
        rows = workspace.knowledge.retrieve(db, owner, project or '', query) if workspace.knowledge else []
        return ({'sources': [workspace.knowledge.reference(r) for r in rows], 'empty': not rows}, False)
    else:
        raise ValueError('Action inconnue.')
    return result, True
