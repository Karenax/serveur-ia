"""Serialization and storage primitives for assistant domain records."""
import hashlib
import json
import time

def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()

def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def save(db, owner, project, kind, identity, payload, revision=1):
    db.execute('INSERT INTO assistant_items VALUES(?,?,?,?,?,?,?) '
               'ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision,updated=excluded.updated',
               (identity, owner, project, kind, encoded(payload), revision, time.time()))
