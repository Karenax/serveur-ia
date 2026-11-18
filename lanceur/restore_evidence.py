"""Persist a minimal, catalogue-bound record of an isolated paired restore."""
from datetime import datetime, timezone
import json
from pathlib import Path

from core import write_json

PROOF_NAME = 'restauration-verifiee.json'


def _time(value):
    if not isinstance(value, str):
        raise ValueError('Date de restauration invalide.')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('Date de restauration invalide.') from None
    if result.tzinfo is None or result > datetime.now(timezone.utc):
        raise ValueError('Date de restauration invalide.')
    return result


def _match(report, records):
    if not isinstance(report, dict) or report.get('remote_disabled') is not True or report.get('isolated_data_removed') is not True:
        raise ValueError('La restauration isolée n’est pas attestée.')
    _time(report.get('verified_at'))
    databases = report.get('databases')
    if not isinstance(databases, dict) or any(not isinstance(databases.get(name), dict)
        or databases[name].get('integrity') != 'ok' or databases[name].get('foreign_key_violations') != 0
        for name in ('espaces', 'projets', 'connaissances')):
        raise ValueError('Les contrôles des bases restaurées sont incomplets.')
    originals = report.get('verified_originals')
    if not isinstance(originals, dict) or any(type(originals.get(name)) is not int or originals[name] < 0
        for name in ('mails', 'html', 'with_attachment', 'audio')):
        raise ValueError('Les contrôles des originaux sont incomplets.')
    archive, digest = report.get('archive'), report.get('companion_sha256')
    if not isinstance(archive, str) or Path(archive).name != archive or not isinstance(digest, str):
        raise ValueError('Paire de sauvegardes invalide.')
    matches = [record for record in records if isinstance(record, dict) and record.get('verified') is True
               and isinstance(record.get('file'), str) and Path(record['file']).name == archive and isinstance(record.get('agent'), dict)
               and record['agent'].get('sha256') == digest]
    if len(matches) != 1:
        raise ValueError('La paire restaurée ne correspond pas à une archive vérifiée du catalogue.')
    return matches[0]


def record(directory, report):
    """Call only with a report produced by the completed isolated restore tool."""
    directory = Path(directory)
    catalogue = json.loads((directory / 'catalogue.json').read_text(encoding='utf-8-sig'))
    record = _match(report, catalogue.get('catalog', []))
    proof = {'version': 1, 'verified_at': report['verified_at'], 'archive_id': record['id'],
             'companion_sha256': report['companion_sha256']}
    write_json(directory / PROOF_NAME, proof)
    return proof


def status(directory, records):
    """Report only a dated proof still bound to the paired catalogue entry."""
    try:
        proof = json.loads((Path(directory) / PROOF_NAME).read_text(encoding='utf-8-sig'))
        if not isinstance(proof, dict) or proof.get('version') != 1:
            return None
        _time(proof.get('verified_at'))
        matches = [record for record in records if isinstance(record, dict) and record.get('id') == proof.get('archive_id')
                   and record.get('verified') is True and isinstance(record.get('agent'), dict)
                   and record['agent'].get('sha256') == proof.get('companion_sha256')]
        if len(matches) != 1:
            return None
        return {'verified_at': proof['verified_at'], 'archive_created_at': matches[0].get('created_at'),
                'scope': 'paired'}
    except (OSError, ValueError, TypeError, KeyError):
        return None
