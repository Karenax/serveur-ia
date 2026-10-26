"""Bounded command receipts; timestamped nonces fail closed after compaction."""
from __future__ import annotations

import json
import re
import secrets
import time

MAX_RECEIPTS = 5000
KEEP_RECEIPTS = 2500
RETENTION_MS = 30 * 86400 * 1000
RECOVERY = frozenset({'memory_forget', 'reminder_cancel', 'task_cancel', 'task_pause'})
PATTERN = re.compile(r'v2_([a-f0-9]{12})[a-f0-9]{20}\Z')
EXPIRED = 'Cette demande a expiré. Relancez l’action ; aucune nouvelle modification n’a été enregistrée.'


def request_key(*, seed=None, issued_at=None):
    stamp = int((time.time() if issued_at is None else issued_at) * 1000)
    nonce = secrets.token_hex(10) if seed is None else seed[:20]
    key = f'v2_{stamp:012x}{nonce}'
    validate_key(key)
    return key


def validate_key(key):
    from workspace_types import identifier

    if isinstance(key, str) and PATTERN.fullmatch(key):
        return int(key[3:15], 16)
    identifier(key)
    return None


def derived_key(request,seed=None):
    """Keep retries stable across contexts; never date an old request as new."""
    if seed is not None and not (isinstance(request,str) and request.startswith('v2_')):
        return seed[:32]
    issued=validate_key(request)
    if issued is None:
        return seed[:32] if seed is not None else request
    return request_key(seed=seed or request[-20:],issued_at=issued/1000)


def prepare(db, owner, key, fingerprint, *, now=None):
    """Runs in the same transaction as the mutation and its receipt."""
    from workspace_types import Conflict

    now_ms = int((time.time() if now is None else now) * 1000)
    issued = validate_key(key)
    setting = 'command-journal-floor:' + owner
    row = db.execute('SELECT value FROM settings WHERE key=?', (setting,)).fetchone()
    floor = max(now_ms - RETENTION_MS, int(row[0]) if row else 0)
    if issued is not None and (issued <= floor or issued > now_ms + 300000):
        raise Conflict(EXPIRED)
    previous = db.execute('SELECT fingerprint,result FROM assistant_commands WHERE owner=? AND request_key=?',
                          (owner, key)).fetchone()
    if previous:
        if previous['fingerprint'] != fingerprint:
            raise Conflict('Cette demande a déjà été utilisée pour une autre commande.')
        return json.loads(previous['result'])

    if issued is None:
        # Opaque legacy keys cannot be aged safely. Preserve their receipts and
        # require an upgraded client once this bounded compatibility pool fills.
        count = db.execute("SELECT COUNT(*) FROM assistant_commands WHERE owner=? AND substr(request_key,1,3)!='v2_'",
                           (owner,)).fetchone()[0]
        if count >= MAX_RECEIPTS:
            raise Conflict('Mettez à jour le client pour continuer ces commandes et annuler vos rappels.')
        return None

    db.execute("DELETE FROM assistant_commands WHERE owner=? AND substr(request_key,1,3)='v2_' AND request_key<?",
               (owner, f'v2_{floor + 1:012x}'))
    count = db.execute("SELECT COUNT(*) FROM assistant_commands WHERE owner=? AND substr(request_key,1,3)='v2_'",
                       (owner,)).fetchone()[0]
    if count >= MAX_RECEIPTS:
        oldest = db.execute("SELECT request_key FROM assistant_commands WHERE owner=? AND substr(request_key,1,3)='v2_' ORDER BY request_key LIMIT ?",
                            (owner, count - KEEP_RECEIPTS + 1)).fetchall()
        floor = max(floor, int(oldest[-1][0][3:15], 16))
        if issued <= floor:
            raise Conflict(EXPIRED)
        db.execute("DELETE FROM assistant_commands WHERE owner=? AND substr(request_key,1,3)='v2_' AND request_key<?",
                   (owner, f'v2_{floor + 1:012x}'))
    db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (setting, str(floor)))
    return None


def record(db, owner, key, fingerprint, result, now):
    from assistant_repository import encoded

    db.execute('INSERT INTO assistant_commands VALUES(?,?,?,?,?)',
               (owner, key, fingerprint, encoded(result), now))
