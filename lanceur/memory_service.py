"""Canonical memory operations shared by legacy UI and assistant commands."""
from __future__ import annotations

import json
import re
import secrets
import time
import unicodedata
from assistant_repository import encoded, digest, save
from workspace_types import Conflict, Denied, identifier, text as validate_text


def present_memory(row, project, metadata):
    payload=metadata.get(row['id'],{})
    return {'id':row['id'],'text':row['text'],'updated':row['updated'],
            'revision':digest({'text':row['text'],'updated':row['updated']}),'project':project,
            'category':payload.get('category','information'),
            'origin':payload.get('origin','Souvenir existant'),'global':payload.get('global',False)}


def memories(db, owner, project):

    table = 'memories' if project else 'personal_memories'
    rows = db.execute(
        'SELECT * FROM ' + table + ' WHERE owner=?'
        + (' AND project=?' if project else '') + ' ORDER BY updated DESC',
        (owner, project) if project else (owner,),
    ).fetchall()
    metadata = {
        row['id']: json.loads(row['payload'])
        for row in db.execute(
            "SELECT id,payload FROM assistant_items WHERE owner=? AND kind='memory' AND project IS ?",
            (owner, project),
        )
    }
    return [present_memory(row,project,metadata) for row in rows]


def all_memories(db, owner):
    """Read all scopes in two queries instead of two queries per project."""
    from collections import defaultdict

    metadata={row['id']:json.loads(row['payload']) for row in db.execute(
        "SELECT id,payload FROM assistant_items WHERE owner=? AND kind='memory'",(owner,))}
    rows=db.execute('SELECT id,text,updated,project FROM memories WHERE owner=? UNION ALL '
                    'SELECT id,text,updated,NULL AS project FROM personal_memories WHERE owner=? '
                    'ORDER BY updated DESC',(owner,owner))
    result=defaultdict(list)
    for row in rows:
        result[row['project']].append(present_memory(row,row['project'],metadata))
    return result


def mutate_memory(workspace, db, owner, project, operation, values,
                  *, origin='Gestion Kiara', request_text=None):

    if project:
        record = workspace.own(db, 'projects', project, owner)
        if record['archived']:
            raise Denied('Projet archivé.')
    table = 'memories' if project else 'personal_memories'
    identity = secrets.token_hex(16) if operation == 'memory_add' else identifier(values.get('id'))
    current = memories(db, owner, project)
    old = next((memory for memory in current if memory['id'] == identity), None)
    row = db.execute(
        "SELECT payload FROM assistant_items WHERE id=? AND owner=? AND kind='memory'",
        (identity, owner),
    ).fetchone()
    metadata = json.loads(row[0]) if row else {}
    if operation != 'memory_add':
        if not old:
            raise Denied('Souvenir absent de cet espace.')
        if not values.get('revision'):
            raise Conflict('Mettez à jour le client avant de modifier ce souvenir. Votre brouillon reste disponible.')
        if values.get('revision') != old['revision']:
            raise Conflict('Ce souvenir a changé. Rechargez sa version actuelle ; votre brouillon reste disponible.')
    elif len(current) >= 50:
        raise ValueError('Maximum 50 souvenirs dans cet espace.')

    if operation == 'memory_forget':
        db.execute('DELETE FROM ' + table + ' WHERE id=? AND owner=?', (identity, owner))
        payload = {**suppress_old(metadata, old['text']), 'forgotten': True, 'origin': origin}
        result = {'id': identity, 'message': 'Souvenir oublié. La discussion source reste dans votre historique.'}
    else:
        value = validate_text(values.get('text'),2000,'Texte')
        category = values.get('category', metadata.get('category', 'information'))
        if category not in ('information', 'preference', 'decision'):
            raise ValueError('Catégorie de souvenir inconnue.')
        scope = values.get('scope', 'global' if metadata.get('global') else 'current')
        if scope not in ('current', 'global'):
            raise ValueError('Portée du souvenir inconnue.')
        if scope == 'global' and (project or category != 'preference'):
            raise ValueError('Choisissez l’espace Personnel et le type Préférence pour l’appliquer à tous vos projets.')
        if scope == 'global' and request_text is not None and operation == 'memory_add' and not re.search(
                r'\b(tous|toutes|partout|global\w*|ensemble)\b', request_text, re.I):
            raise ValueError('Précisez si cette préférence doit s’appliquer à tous vos projets.')
        workspace.quota(db, owner, max(0, len(value.encode()) - len(old['text'].encode()) if old else len(value.encode())))
        now = time.time()
        if operation == 'memory_add':
            if project:
                db.execute('INSERT INTO memories VALUES(?,?,?,?,?)', (identity, owner, project, value, now))
            else:
                db.execute('INSERT INTO personal_memories VALUES(?,?,?,?)', (identity, owner, value, now))
        else:
            db.execute('UPDATE ' + table + ' SET text=?,updated=? WHERE id=? AND owner=?',
                       (value, now, identity, owner))
        payload = {
            **(suppress_old(metadata, old['text']) if old and old['text'] != value else metadata),
            'category': category, 'origin': origin, 'forgotten': False, 'global': scope == 'global',
        }
        if request_text:
            tokens = words(request_text)[:2000]
            payload['source_rules'] = [{'length': len(tokens), 'hash': digest(tokens)}]
        result = {
            'id': identity, 'message': 'Souvenir enregistré.', 'text': value,
            'revision': digest({'text': value, 'updated': now}),
        }
    save(db, owner, project, 'memory', identity, payload)
    bump_memory(db, owner)
    return result


def legacy_action(workspace, db, owner, action, values):
    """Translate the old protocol; never infer the revision of an edited draft."""

    project = None
    if not action.startswith('personal_'):
        if action == 'memory_create':
            project = values.get('project')
        else:
            project = workspace.own(db, 'memories', values.get('id'), owner)['project']
    elif not action.endswith('_create'):
        row = db.execute('SELECT id FROM personal_memories WHERE id=? AND owner=?',
                         (identifier(values.get('id')), owner)).fetchone()
        if row is None:
            raise Denied('Souvenir absent ou accès interdit.')
    operation = 'memory_add' if action.endswith('_create') else (
        'memory_update' if action.endswith('_save') else 'memory_forget'
    )
    result = mutate_memory(workspace, db, owner, project, operation, values)
    return {**result, 'saved': True}


def bump_memory(db, owner):
    db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', ('assistant-memory:'+owner, secrets.token_hex(16)))

def epoch(db, owner):
    row = db.execute("SELECT value FROM settings WHERE key=?", ('assistant-memory:'+owner,)).fetchone()
    return row[0] if row else '0'

def global_preferences(db,owner):
    return [m for m in memories(db,owner,None) if m['global'] and m['category']=='preference']

def memory_epoch(workspace, owner):
    with workspace.db() as db:
        return epoch(db, owner)

def model_history(workspace,owner,project,messages):
    with workspace.db() as db:rules=suppression_rules(db,owner,project)
    if not rules:return messages
    result=[];hide_reply=False
    for message in messages:
        content=message.get('content','')
        text=content if isinstance(content,str) else '\n'.join(p.get('text','') for p in content if p.get('type')=='text')
        hidden=message.get('role') in ('user','assistant') and suppressed(text,rules)
        if hidden or hide_reply and message.get('role')=='assistant':
            result.append({'role':message['role'],'content':'[Ancien souvenir oublié ou corrigé. Consulter les souvenirs actuels.]'})
        else:result.append(message)
        if message.get('role')=='user':hide_reply=hidden
    return result

def retire_legacy(db,owner,project,identity,value,forgotten=False):
    row=db.execute("SELECT payload FROM assistant_items WHERE id=? AND owner=? AND kind='memory'",(identity,owner)).fetchone()
    payload=json.loads(row[0]) if row else {}
    save(db,owner,project,'memory',identity,{**suppress_old(payload,value),'forgotten':forgotten,'origin':payload.get('origin','Gestion Kiara')})

def suppress_old(payload,value):
    tokens=words(value)
    rule={'length':len(tokens),'hash':digest(tokens)}
    blocked=list(payload.get('blocked',[]))
    for source in payload.get('source_rules',[]):
        if source not in blocked:blocked.append(source)
    if rule not in blocked:blocked.append(rule)
    return {**payload,'blocked':blocked[-50:]}

def suppressed(value,rules):
    tokens=words(value)
    for length in {r['length'] for r in rules if r['length']>0}:
        hashes={r['hash'] for r in rules if r['length']==length}
        if any(digest(tokens[i:i+length]) in hashes for i in range(len(tokens)-length+1)):
            return True
    return False

def suppression_rules(db,owner,project):
    return [rule for row in db.execute("SELECT payload FROM assistant_items WHERE owner=? AND kind='memory' AND (project IS ? OR (project IS NULL AND json_extract(payload,'$.global')=1))",(owner,project or None))
            for rule in json.loads(row[0]).get('blocked',[])]

def words(value):
    return re.findall(r'\w+',unicodedata.normalize('NFKC',value).casefold())
