"""Document operations; the caller owns the access and database transaction."""
import base64
import json
import secrets
from pathlib import Path
from workspace_types import Conflict, Denied, identifier, text, MAX_TEXT, HISTORY_RESET_ID
from kiara_shared.attachments import validate_message

def execute(workspace, db, owner, values, now, prepared=None):
    action = values.get("action")
    if action in ('document_create', 'document_upload', 'document_save'):
        p = workspace.own(db, 'projects', values.get('project'), owner)
        if p['archived']:
            raise ValueError('Projet archivé.')
        title = text(values.get('title'), 180, 'Nom du document')
        raw = None
        kind = 'note'
        pdf = False
        previous = None
        if action == 'document_save':
            previous = workspace.own(db, 'documents', values.get('id'), owner)
            if previous['project'] != p['id']:
                raise Denied('Document hors projet.')
            if values.get('revision') != previous['revision']:
                raise Conflict('Document modifié ailleurs. Votre brouillon est conservé ; rechargez pour comparer.')
            id = previous['id']
            kind = previous['kind']
            raw = previous['original']
        else:
            if db.execute('SELECT COUNT(*) FROM documents WHERE owner=?', (owner,)).fetchone()[0] >= 500:
                raise ValueError('Maximum 500 documents par accès.')
            id = secrets.token_hex(16)
        if action == 'document_upload':
            raw, pages = prepared
            kind = Path(title).suffix.lower().lstrip('.')
            pdf = kind == 'pdf'
            content = '\n\n'.join(pages)
        else:
            content = text(values.get('text', ''), MAX_TEXT, 'Texte', True)
            pages = [content]
        old_bytes = 0
        if previous:
            old_bytes = len(previous['text'].encode()) + db.execute('SELECT COALESCE(SUM(length(CAST(text AS BLOB))),0) FROM chunks WHERE document=?', (id,)).fetchone()[0]
        extra = max(0, len(content.encode()) * 3 - old_bytes) + (len(raw or b'') if not previous else 0)
        workspace.quota(db, owner, extra + 600)
        revision = previous['revision'] + 1 if previous else 1
        if previous:
            db.execute('UPDATE documents SET title=?,text=?,revision=?,updated=? WHERE id=?', (title, content, revision, now, id))
        else:
            db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?)', (id, owner, p['id'], title, content, raw, kind, revision, now))
        workspace.index(db, owner, p['id'], id, pages, pdf)
        result = {'id': id, 'revision': revision}
    elif action in ('document_get',):
        d = workspace.own(db, 'documents', values.get('id'), owner)
        d.pop('original')
        status = db.execute('SELECT state,chunks,pages,revision,indexed FROM document_index WHERE document=? AND owner=?', (d['id'], owner)).fetchone()
        d.update({'index_state': status[0] if status else 'unknown', 'chunk_count': status[1] if status else 0, 'page_count': status[2] if status else None, 'indexed_revision': status[3] if status else None, 'indexed_at': status[4] if status else None})
        return (d, False)
    elif action in ('document_download',):
        d = workspace.own(db, 'documents', values.get('id'), owner)
        return ({'title': d['title'], 'data': base64.b64encode(d['original'] or d['text'].encode()).decode(), 'original': d['original'] is not None}, False)
    elif action in ('document_delete',):
        d = workspace.own(db, 'documents', values.get('id'), owner)
        if values.get('revision') != d['revision']:
            raise Conflict('Document modifié ailleurs.')
        db.execute('DELETE FROM documents WHERE id=?', (d['id'],))
        result = {'deleted': True}
    elif action in ('search',):
        p = workspace.own(db, 'projects', values.get('project'), owner)
        selected = values.get('document')
        if selected:
            d = workspace.own(db, 'documents', selected, owner)
            if d['project'] != p['id']:
                raise Denied('Document hors projet.')
        sources = workspace.search(db, owner, p['id'], text(values.get('query'), 2000, 'Question'), [selected] if selected else None)
        return ({'sources': sources, 'empty': not sources, 'message': 'Aucun passage documentaire correspondant.' if not sources else '', 'index': workspace.index_status(db, owner, p['id'])}, False)
    elif action in ('source_get',):
        return (workspace.read_source(db, owner, values.get('source_id')), False)
    elif action in ('index_status',):
        project = values.get('project')
        if project:
            workspace.own(db, 'projects', project, owner)
        return (workspace.index_status(db, owner, project), False)
    else:
        raise ValueError('Action inconnue.')
    return result, True
