"""Pure readiness and version-specific human validation rules."""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
import hashlib
import json
from pathlib import Path

from fastapi import HTTPException

from ..project_deliverable_schemas import TypeDefinition

TRANSITIONS = {
    'draft': {'to_verify', 'archived'},
    'to_verify': {'validated', 'to_revise', 'archived'},
    'validated': {'to_revise', 'archived'},
    'to_revise': {'to_verify', 'archived'},
    'archived': {'to_revise'},
}
MAX_FILE_BYTES = DOCUMENT_IMPORT_BYTES


def frozen_json(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return payload, hashlib.sha256(payload.encode('utf-8')).hexdigest()


def standard_catalogue():
    """Read-only suggestions; never installs references or changes a project."""
    value = json.loads((Path(__file__).parent.parent / 'data' / 'deliverable_catalogue.json').read_text(encoding='utf-8'))
    for item in value['types']:
        TypeDefinition.model_validate(item['definition'])
    return value


def file_digest(path):
    """Bounded streaming read. Reject an in-place modification during the read."""
    try:
        with Path(path).open('rb') as stream:
            import os
            before = os.fstat(stream.fileno())
            import stat
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
                raise HTTPException(422, 'Fichier régulier de 50 Mio maximum requis')
            digest = hashlib.sha256()
            size = 0
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise HTTPException(422, 'Fichier trop volumineux')
                digest.update(chunk)
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                raise HTTPException(409, 'Fichier modifié pendant la lecture : réessayer')
            return {'sha256': digest.hexdigest(), 'size_bytes': size}
    except OSError as exc:
        raise HTTPException(409, 'Fichier indisponible : conserver la version et rétablir son accès') from exc


def progress(items, *, transverse=False):
    selected = [item for item in items if item['active'] and item['contributes'] and item['transverse'] == transverse]
    completed = sum(bool(item['completed']) for item in selected)
    return {'completed': completed, 'total': len(selected),
            'percentage': round(100 * completed / len(selected)) if selected else 0,
            'state': 'complete' if selected and completed == len(selected) else 'pending' if selected else 'not_applicable'}


def validation_blockers(items, version_id):
    return [{'id': item['id'], 'label': item['label'], 'reason': 'Visa humain requis pour cette version'}
            for item in items if item['active'] and item['is_gate']
            and (not item['completed'] or item['completed_version_id'] != version_id or not item.get('proof', '').strip())]


def validate_transition(previous, target):
    if target not in TRANSITIONS[previous]:
        raise HTTPException(409, f'Transition documentaire impossible : {previous} → {target}')
