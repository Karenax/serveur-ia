"""Rebuildable, bounded semantic index. Canonical sources always authorize retrieval."""
from array import array
import hashlib
import http.client
import json
import math
import re
import sqlite3
import threading
import time
import unicodedata

PERSONAL_SCHEMA = '''
CREATE TABLE IF NOT EXISTS personal_memories(id TEXT PRIMARY KEY, owner TEXT NOT NULL, text TEXT NOT NULL, updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS personal_memory_owner ON personal_memories(owner);
CREATE TABLE IF NOT EXISTS knowledge_exclusions(owner TEXT NOT NULL, conversation TEXT NOT NULL, PRIMARY KEY(owner,conversation));
'''
MAX_ROWS = 16000
MAX_OWNER_ROWS = 4000
MAX_CACHE_BYTES = 64 * 1024 * 1024
MODEL_VERSION = 'embeddinggemma-2-text-f32-768-search-v1'
MIN_SCORE = .72


def passages(value):
    for start in range(0, len(value), 1600):
        part = value[start:start + 1800]
        if part.strip(): yield start // 1600, part


def record(owner, scope, kind, identity, title, value, revision, ordinal=0, page=None, role=None):
    digest = hashlib.sha256(json.dumps([owner, scope, kind, identity, title, value,
        ordinal, page, role], ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    return {'id': digest, 'owner': owner, 'scope': scope, 'kind': kind, 'object': identity,
        'title': title, 'text': value, 'revision': revision, 'ordinal': ordinal, 'page': page, 'role': role}


def conversation_records(owner, scope, identity, title, messages, revision):
    for index, message in enumerate(messages):
        # Internal reasoning, binary attachments and partial responses are never memories.
        if message.get('interrupted') or message.get('role') not in ('user', 'assistant'): continue
        value = message.get('content', '')
        if not isinstance(value, str): continue
        for part, content in passages(value):
            yield record(owner, scope, 'conversation', identity, title, content, revision,
                index * 100000 + part, role=message['role'])


class Knowledge:
    def __init__(self, workspace, engine):
        self.workspace = workspace; self.engine = engine
        self.path = workspace.path.with_name('connaissances-cache.sqlite3')
        self.lock = threading.RLock(); self.halt = threading.Event(); self.thread = None
        self.error = ''; self.limited = False; self.last_sync = None; self.pending = 0
        self.next_sync = 0; self.dirty = threading.Event(); self.dirty.set()
        self.restart_requested=False
        self.indexed_revision = None
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS entries(id TEXT PRIMARY KEY, owner TEXT NOT NULL,
                    scope TEXT NOT NULL, kind TEXT NOT NULL, object TEXT NOT NULL,
                    data TEXT NOT NULL, version TEXT NOT NULL, vector BLOB);
                CREATE INDEX IF NOT EXISTS entries_scope ON entries(owner,scope);
            ''')

    def db(self):
        # Independent cache connections never acquire the canonical workspace lock.
        from contextlib import contextmanager
        @contextmanager
        def connection():
            with self.lock:
                db = sqlite3.connect(self.path, timeout=5); db.row_factory = sqlite3.Row
                try:
                    with db: yield db
                finally: db.close()
        return connection()

    def changed(self): self.dirty.set()

    def start(self):
        if self.thread and self.thread.is_alive():
            if self.halt.is_set():self.restart_requested=True
            return
        self.restart_requested=False
        self.halt.clear()
        self.thread = threading.Thread(target=self.run, daemon=True, name='fred-eg2-knowledge')
        self.thread.start()

    def close(self):
        self.restart_requested=False
        self.halt.set()
        self.engine.stop()
        if self.thread:self.thread.join(timeout=2)

    def reset(self):
        with self.db() as db: db.execute('DELETE FROM entries')
        self.indexed_revision = None
        self.changed()

    def source_records(self):
        # Row bounds and byte bounds apply before any expensive model work.
        found = []; counts = {}; used = 0; limited = False
        def append(item):
            nonlocal used, limited
            owner = item['owner']; cost = len(json.dumps(item, ensure_ascii=False).encode()) + 3072
            if len(found) >= MAX_ROWS or counts.get(owner, 0) >= MAX_OWNER_ROWS or used + cost > MAX_CACHE_BYTES:
                limited = True; return
            counts[owner] = counts.get(owner, 0) + 1; used += cost; found.append(item)
        with self.workspace.db() as db:
            # Preferences first; then current documents; newest discussions last.
            for m in db.execute('SELECT m.* FROM memories m JOIN projects p ON p.id=m.project AND p.owner=m.owner WHERE p.archived=0 ORDER BY m.updated DESC'):
                append(record(m['owner'], m['project'], 'memory', m['id'], 'Souvenir confirmé', m['text'], str(m['updated'])))
            for m in db.execute('SELECT * FROM personal_memories ORDER BY updated DESC'):
                append(record(m['owner'], '', 'personal_memory', m['id'], 'Souvenir personnel confirmé', m['text'], str(m['updated'])))
            for c in db.execute('SELECT c.*,d.title,d.revision FROM chunks c JOIN documents d ON d.id=c.document AND d.owner=c.owner AND d.project=c.project JOIN projects p ON p.id=c.project AND p.owner=c.owner WHERE p.archived=0 ORDER BY d.updated DESC,c.id'):
                append(record(c['owner'], c['project'], 'document', c['document'], c['title'], c['text'], c['revision'], c['id'], c['page']))
            saved = {r['id']: dict(r) for r in db.execute('SELECT * FROM conversations')}
            for c in sorted(saved.values(), key=lambda c: c['updated'], reverse=True):
                p = db.execute('SELECT archived FROM projects WHERE id=? AND owner=?', (c['project'], c['owner'])).fetchone()
                if c['archived'] or not p or p[0]: continue
                for item in conversation_records(c['owner'], c['project'], c['id'], c['title'], json.loads(c['messages']), c['revision']): append(item)
            for h in db.execute('SELECT * FROM client_histories ORDER BY updated DESC'):
                history = json.loads(h['history'])
                exclusions={r[0] for r in db.execute('SELECT conversation FROM knowledge_exclusions WHERE owner=?',(h['owner'],))}
                for c in history['conversations']:
                    if c.get('archived') or c['id'] in saved or c['id'] in exclusions: continue
                    scope = c.get('project_id') or ''
                    if scope:
                        p = db.execute('SELECT archived FROM projects WHERE id=? AND owner=?', (scope, h['owner'])).fetchone()
                        # An orphan project never becomes a personal conversation.
                        if not p or p[0]: continue
                    revision = h['revision']
                    for item in conversation_records(h['owner'], scope, c['id'], c['title'], c['messages'], revision): append(item)
        self.limited = limited
        return found

    def synchronize(self, encode=True):
        if self.workspace.maintenance: return 0
        revision = self.workspace.source_revision
        current = {item['id']: item for item in self.source_records()} if revision != self.indexed_revision else None
        if self.halt.is_set():return 0
        with self.db() as db:
            if current is not None:
                old = {r[0] for r in db.execute('SELECT id FROM entries')}
                db.executemany('DELETE FROM entries WHERE id=?', [(id,) for id in old - current.keys()])
                for id,item in current.items():
                    db.execute('INSERT INTO entries VALUES(?,?,?,?,?,?,?,NULL) ON CONFLICT(id) DO UPDATE SET data=excluded.data WHERE data!=excluded.data',
                        (id, item['owner'], item['scope'], item['kind'], item['object'], json.dumps(item, ensure_ascii=False), MODEL_VERSION))
                self.indexed_revision = revision
            db.execute('UPDATE entries SET vector=NULL,version=? WHERE version!=?', (MODEL_VERSION, MODEL_VERSION))
            rows = db.execute('SELECT id,data FROM entries WHERE vector IS NULL LIMIT 4').fetchall()
            self.pending = db.execute('SELECT COUNT(*) FROM entries WHERE vector IS NULL').fetchone()[0]
        completed = 0
        if encode and rows:
            items = [json.loads(r['data']) for r in rows]
            vectors = self.engine.encode(['title: ' + i['title'] + ' | text: ' +
                (('Utilisateur : ' if i['role'] == 'user' else 'Réponse de l’assistant : ') if i['kind'] == 'conversation' else '') + i['text'] for i in items], timeout=20)
            with self.db() as db:
                for row, vector in zip(rows, vectors):
                    db.execute('UPDATE entries SET vector=? WHERE id=? AND version=?',
                        (array('f', vector).tobytes(), row['id'], MODEL_VERSION)); completed += 1
            self.pending -= completed
        self.last_sync = time.time(); self.error = ''
        return completed

    def run(self):
        while not self.halt.wait(.5):
            try:
                if self.workspace.maintenance: continue
                self.engine.tick()
                if self.dirty.is_set() or time.monotonic() >= self.next_sync or (self.pending and self.engine.state=='pret'):
                    self.dirty.clear(); self.next_sync = time.monotonic() + 15
                    self.synchronize(encode=self.engine.state == 'pret' and self.engine.enabled())
            except (OSError, ValueError, sqlite3.Error, http.client.HTTPException):
                self.error = 'Indexation EG2 en attente ; recherche par mots-clés disponible.'
                self.halt.wait(2)
        if self.restart_requested:
            self.thread=None;self.start()

    def resolve(self, db, item, memo=None):
        """Re-read the source under Kiara's transaction; never trust cached text or scope."""
        owner = item['owner']; scope = item['scope']; kind = item['kind']
        if self.workspace.maintenance: return None
        if scope:
            p = db.execute('SELECT archived FROM projects WHERE id=? AND owner=?', (scope, owner)).fetchone()
            if not p or p[0]: return None
        if kind == 'document':
            c = db.execute('SELECT c.*,d.title,d.revision FROM chunks c JOIN documents d ON d.id=c.document WHERE c.id=? AND c.document=? AND c.owner=? AND c.project=? AND d.owner=? AND d.project=?',
                (item['ordinal'], item['object'], owner, scope, owner, scope)).fetchone()
            if not c: return None
            fresh = record(owner, scope, kind, c['document'], c['title'], c['text'], c['revision'], c['id'], c['page'])
        elif kind in ('memory', 'personal_memory'):
            table = 'memories' if kind == 'memory' else 'personal_memories'
            m = db.execute('SELECT * FROM ' + table + ' WHERE id=? AND owner=?', (item['object'], owner)).fetchone()
            if not m or (kind == 'memory' and m['project'] != scope): return None
            fresh = record(owner, scope, kind, m['id'], item['title'], m['text'], str(m['updated']))
        elif kind == 'conversation':
            if db.execute('SELECT 1 FROM knowledge_exclusions WHERE owner=? AND conversation=?',(owner,item['object'])).fetchone():return None
            key=(owner,scope,item['object'])
            if memo is not None and key in memo:
                fresh=memo[key].get(item['ordinal'])
                return fresh if fresh and fresh['id']==item['id'] else None
            c = db.execute('SELECT * FROM conversations WHERE id=?', (item['object'],)).fetchone()
            if c:
                if c['owner'] != owner or c['project'] != scope or c['archived']: return None
                matches = conversation_records(owner, scope, c['id'], c['title'], json.loads(c['messages']), c['revision'])
            else:
                h = db.execute('SELECT history,revision FROM client_histories WHERE owner=?', (owner,)).fetchone()
                if not h: return None
                c = next((c for c in json.loads(h[0])['conversations'] if c['id'] == item['object']), None)
                if not c or c.get('archived') or (c.get('project_id') or '') != scope: return None
                revision = h['revision']
                matches = conversation_records(owner, scope, c['id'], c['title'], c['messages'], revision)
            mapping={i['ordinal']:i for i in matches}
            if memo is not None:memo[key]=mapping
            fresh = mapping.get(item['ordinal'])
            if not fresh: return None
        else: return None
        return fresh if fresh['id'] == item['id'] else None

    def retrieve(self, db, owner, scope, query, document=None, kinds=None, limit=6,exclude_conversation=None):
        if self.workspace.maintenance: return []
        with self.db() as cache:
            rows = cache.execute('SELECT data,vector FROM entries WHERE owner=? AND scope=?', (owner, scope or '')).fetchall()
        if exclude_conversation:
            canonical=exclude_conversation.replace('-','')
            rows=[row for row in rows if not ((item:=json.loads(row['data']))['kind']=='conversation' and item['object'].replace('-','')==canonical)]
        if not rows:return []
        vector = None
        if self.engine.state == 'pret':
            try: vector = self.engine.encode([query[:2000]], mode='query')[0]
            except (OSError, ValueError, http.client.HTTPException): pass
        from workspace import search_words
        from assistant_commands import suppression_rules,suppressed
        forgotten=suppression_rules(db,owner,scope)
        words = search_words(query); lexical = []; dense = []; eligible = {};memo={}
        for row in rows:
            item = json.loads(row['data'])
            if document and (item['kind'] != 'document' or item['object'] != document): continue
            if kinds and item['kind'] not in kinds: continue
            # Filter scope and authorization before ranking, not after a global top-k.
            fresh = self.resolve(db, item,memo)
            if not fresh: continue
            if fresh['kind']=='conversation' and suppressed(fresh['text'],forgotten):continue
            eligible[item['id']] = fresh
            normalized = ''.join(c for c in unicodedata.normalize('NFD', (item['title'] + ' ' + item['text']).casefold()) if unicodedata.category(c) != 'Mn')
            coverage = sum(bool(re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', normalized)) for w in words)
            if coverage: lexical.append((coverage, item['id']))
            if vector is not None and row['vector']:
                values = array('f'); values.frombytes(row['vector'])
                if len(values) != len(vector) or any(not math.isfinite(v) for v in values): continue
                score = sum(a * b for a, b in zip(vector, values))
                if score >= MIN_SCORE: dense.append((score, item['id']))
        ranks = {}
        for ranking in (sorted(lexical, reverse=True), sorted(dense, reverse=True)):
            for index, (_, id) in enumerate(ranking[:80]): ranks[id] = ranks.get(id, 0) + 1 / (60 + index + 1)
        return [eligible[id] for id in sorted(ranks, key=lambda id: (-ranks[id], id))[:limit]]

    def reference(self, item):
        return {'source_id': item['id'], 'kind': item['kind'], 'project': item['scope'] or None,
            'document': item['object'] if item['kind'] == 'document' else None,
            'conversation': item['object'] if item['kind'] == 'conversation' else None,
            'title': item['title'], 'text': item['text'], 'passage': item['text'],
            'role': item['role'], 'page': item['page'], 'revision': item['revision'],
            'version': item['revision'], 'status': 'current', 'message': 'Passage de la source actuelle.'}

    def read_reference(self, db, owner, identity):
        with self.db() as cache:
            row = cache.execute('SELECT data FROM entries WHERE id=? AND owner=?', (identity, owner)).fetchone()
        if not row: return None
        fresh = self.resolve(db, json.loads(row[0]))
        return self.reference(fresh) if fresh else None

    def status(self):
        with self.db() as db:
            counts = dict(db.execute('SELECT CASE WHEN scope=\'\' THEN \'personal\' ELSE \'project\' END,COUNT(*) FROM entries GROUP BY 1'))
            indexed = db.execute('SELECT COUNT(*) FROM entries WHERE vector IS NOT NULL').fetchone()[0]
        return {'indexed': indexed, 'pending': self.pending, 'entries': sum(counts.values()),
            'personal': counts.get('personal', 0), 'project': counts.get('project', 0),
            'limited': self.limited, 'max_entries': MAX_ROWS, 'max_owner_entries': MAX_OWNER_ROWS,
            'last_sync': self.last_sync, 'error': self.error, 'reconstructible': True}
