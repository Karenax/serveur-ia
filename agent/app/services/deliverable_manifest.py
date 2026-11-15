"""Published L3 evidence format shared by offline recovery and typed archives.

The original v1 publication stays verbatim in a v2 source_publication. Importing
again retains that original instead of building an unbounded nested lineage.
No runtime settings, database or ORM imports are allowed in this module.
"""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re

FIELDS = frozenset({'format', 'version', 'project_id', 'deliverable_id', 'number', 'filename', 'sha256',
                    'size_bytes', 'reference', 'comment', 'source_delivery_id', 'generated',
                    'type_version_id', 'checklist', 'actor_id'})
CHECK_FIELDS = frozenset({'id', 'code', 'scope_key', 'milestone_id', 'label', 'position', 'is_gate', 'transverse',
                          'contributes', 'active', 'completed', 'completed_version_id', 'completed_by',
                          'comment', 'proof', 'completed_at'})
CHECK_IDS = frozenset({'id', 'milestone_id', 'completed_version_id'})
MANIFEST_IDS = frozenset({'project_id', 'deliverable_id', 'source_delivery_id', 'type_version_id'})
BOOL_CHECK_FIELDS = frozenset({'is_gate', 'transverse', 'contributes', 'active', 'completed'})


def freeze(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return payload, hashlib.sha256(payload.encode('utf-8')).hexdigest()


def identity(value, *, optional=False):
    if value is None and optional:
        return
    if not isinstance(value, str) or not 1 <= len(value) <= 36:
        raise ValueError('Identifiant de publication invalide')


def check_snapshot(value):
    if not isinstance(value, dict) or set(value) != CHECK_FIELDS:
        raise ValueError('Champs de checklist publiée invalides')
    for field in CHECK_IDS:
        identity(value[field], optional=field != 'id')
    if (not isinstance(value['code'], str) or re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', value['code']) is None
            or type(value['position']) is not int or value['position'] < 0
            or any(type(value[key]) is not bool for key in BOOL_CHECK_FIELDS)):
        raise ValueError('Code, ordre ou indicateur de checklist invalide')
    for field, minimum, maximum in (('label', 1, 500), ('scope_key', 0, 64), ('comment', 0, 20000), ('proof', 0, 20000)):
        if not isinstance(value[field], str) or not minimum <= len(value[field]) <= maximum:
            raise ValueError('Texte de checklist publiée invalide')
    if value['completed']:
        if not isinstance(value['completed_by'], str) or not 1 <= len(value['completed_by']) <= 120:
            raise ValueError('Auteur de contrôle absent')
        try:
            datetime.fromisoformat(value['completed_at'])
        except (TypeError, ValueError) as exc:
            raise ValueError('Date de contrôle absente ou invalide') from exc
        if value['is_gate'] and (not value['active'] or not value['completed_version_id'] or not value['proof'].strip()):
            raise ValueError('Visa publié sans version, activité ou preuve humaine')
    elif any(value[key] is not None for key in ('completed_by', 'completed_at', 'completed_version_id')):
        raise ValueError('Contrôle non terminé avec des attributs de visa')
    return value


def decode(payload, sha256):
    try:
        if not isinstance(payload, str) or hashlib.sha256(payload.encode('utf-8')).hexdigest() != sha256:
            raise ValueError('Empreinte de manifeste incohérente')
        value = json.loads(payload)
        if (not isinstance(value, dict) or value.get('format') != 'agent-deliverable-version'
                or type(value.get('version')) is not int or value['version'] not in (1, 2)):
            raise ValueError('Format de publication invalide')
        expected = FIELDS | ({'source_publication'} if value['version'] == 2 else set())
        if set(value) != expected or freeze(value)[0] != payload:
            raise ValueError('Champs ou encodage de publication non canoniques')
        for field in MANIFEST_IDS:
            identity(value[field], optional=field not in {'project_id', 'deliverable_id'})
        if (type(value['number']) is not int or value['number'] < 1 or type(value['size_bytes']) is not int
                or not 0 <= value['size_bytes'] <= DOCUMENT_IMPORT_BYTES or type(value['generated']) is not bool
                or not isinstance(value['sha256'], str) or re.fullmatch(r'[a-f0-9]{64}', value['sha256']) is None):
            raise ValueError('Numéro, empreinte ou taille de publication invalide')
        if value['source_delivery_id'] is not None and not value['generated']:
            raise ValueError('Une livraison CDC doit conserver son origine générée')
        for key, minimum, maximum in (('filename', 1, 255), ('reference', 1, 120), ('comment', 0, 20000), ('actor_id', 1, 120)):
            if not isinstance(value[key], str) or not minimum <= len(value[key]) <= maximum:
                raise ValueError('Texte de publication invalide')
        if not isinstance(value['checklist'], list) or len(value['checklist']) > 100000:
            raise ValueError('Liste de contrôles publiés invalide')
        seen = set()
        for check in value['checklist']:
            check_snapshot(check)
            if check['id'] in seen:
                raise ValueError('Contrôle publié dupliqué')
            seen.add(check['id'])
        if value['version'] == 2:
            source = value['source_publication']
            if not isinstance(source, dict) or set(source) != {'version_id', 'manifest', 'manifest_sha256'}:
                raise ValueError('Provenance de publication invalide')
            identity(source['version_id'])
            # Only a v1 leaf is accepted, before decoding: no recursive v2 chain.
            if not isinstance(source['manifest'], str) or json.loads(source['manifest']).get('version') != 1:
                raise ValueError('La provenance doit conserver la publication originale v1')
            original = decode(source['manifest'], source['manifest_sha256'])
            preserved = {'number', 'filename', 'sha256', 'size_bytes', 'reference', 'comment', 'generated', 'actor_id'}
            if any(value[key] != original[key] for key in preserved):
                raise ValueError('Contenu publié différent de sa provenance')
        return value
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ValueError('Manifeste de livrable invalide : ' + str(exc)) from exc


def check_row(row):
    value = decode(row['manifest'], row['manifest_sha256'])
    fields = {'project_id', 'deliverable_id', 'number', 'filename', 'sha256', 'size_bytes',
              'source_delivery_id', 'generated', 'actor_id'}
    if any(value[key] != row[key] for key in fields):
        raise ValueError('Manifeste différent de sa version de fichier')
    return value


def remap(payload, sha256, mapping, *, version_id):
    original = decode(payload, sha256)
    value = deepcopy(original)
    for field in MANIFEST_IDS:
        if value[field] is not None:
            value[field] = mapping[value[field]]
    for check in value['checklist']:
        for field in CHECK_IDS:
            if check[field] is not None:
                check[field] = mapping[check[field]]
    if original['version'] == 1:
        value['source_publication'] = {'version_id': version_id, 'manifest': payload, 'manifest_sha256': sha256}
    value['version'] = 2
    result, digest = freeze(value)
    decode(result, digest)
    return result, digest
