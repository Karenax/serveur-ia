"""Job operations; the caller owns the access and database transaction."""
import base64
import json
import secrets
from pathlib import Path
from workspace_types import Conflict, Denied, identifier, text, MAX_TEXT, HISTORY_RESET_ID
from kiara_shared.attachments import validate_message

def execute(workspace, db, owner, values, now, prepared=None):
    action = values.get("action")
    if action in ('job_create',):
        p = workspace.own(db, 'projects', values.get('project'), owner)
        if p['archived']:
            raise ValueError('Projet archivé.')
        kind = values.get('kind', 'analysis')
        if kind not in ('analysis', 'web'):
            raise ValueError('Type de tâche invalide.')
        prompt = text(values.get('prompt'), 12000, 'Consigne')
        url = text(values.get('url', ''), 2000, 'URL', True)
        title = text(values.get('title', prompt[:100]), 120, 'Nom')
        repeat = values.get('repeat_hours', 0)
        delay = values.get('delay_minutes', 0)
        if type(repeat) is not int or repeat not in (0, 24, 168) or type(delay) is not int or (not 0 <= delay <= 525600):
            raise ValueError('Planification invalide.')
        if kind == 'web':
            workspace.allow_web(db, owner, url)
        if kind == 'web' and (not url) and (len(prompt) > 600 or len(prompt.split()) > 75):
            raise ValueError('Recherche par sujet : maximum 600 caractères et 75 mots.')
        request_key = identifier(values.get('request_key'))
        existing = db.execute('SELECT id FROM jobs WHERE owner=? AND request_key=?', (owner, request_key)).fetchone()
        if existing:
            return ({'id': existing[0]}, False)
        if db.execute("SELECT COUNT(*) FROM jobs WHERE owner=? AND state IN ('queued','running','paused')", (owner,)).fetchone()[0] >= workspace.policy(db, owner)['jobs']:
            raise ValueError('Limite de tâches actives atteinte.')
        workspace.prune(db, owner)
        workspace.quota(db, owner, len(prompt.encode()))
        id = secrets.token_hex(16)
        db.execute('INSERT INTO jobs(id,owner,project,title,prompt,kind,url,state,created,due,repeat_hours,request_key) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', (id, owner, p['id'], title, prompt, kind, url, 'queued', now, now + delay * 60, repeat, request_key))
        result = {'id': id}
    elif action in ('job_get',):
        return (workspace.own(db, 'jobs', values.get('id'), owner), False)
    elif action in ('job_cancel', 'job_pause', 'job_retry'):
        job = workspace.own(db, 'jobs', values.get('id'), owner)
        if action == 'job_retry' and job['state'] not in ('failed', 'cancelled', 'paused'):
            raise ValueError('Cette tâche ne peut pas être relancée.')
        if action == 'job_pause' and job['state'] not in ('queued', 'running'):
            raise ValueError('Tâche déjà terminée.')
        if action == 'job_retry' and db.execute("SELECT COUNT(*) FROM jobs WHERE owner=? AND state IN ('queued','running')", (owner,)).fetchone()[0] >= workspace.policy(db, owner)['jobs']:
            raise ValueError('Limite de tâches atteinte.')
        if action == 'job_retry':
            from notifications import advance_job_attempt
            workspace.quota(db, owner, 160)
            advance_job_attempt(db, job['id'])
        state = {'job_retry': 'queued', 'job_pause': 'paused', 'job_cancel': 'cancelled'}[action]
        db.execute('UPDATE jobs SET state=?,due=?,error=? WHERE id=?', (state, now, '', job['id']))
        result = {'state': state}
        running = workspace.running.get(job['id'])
        if running:
            running.set()
    else:
        raise ValueError('Action inconnue.')
    return result, True
