"""Device declarations and durable, monotonic revocations.

The security directory is deliberately outside the restoration dataset. A backup
may export its ledger, but restoring it can only add revocations, never remove one.
Device kind/version/transport reported by a client are display hints, not rights.
"""
from __future__ import annotations
import math
from pathlib import Path
import re
import threading
import time
from core import read_json, write_json

KINDS = {'unknown', 'pc', 'phone', 'tablet'}
TRANSPORTS = {'unknown', 'https', 'wireguard'}


def text(value, label, limit=80):
    if not isinstance(value, str) or len(value.strip()) > limit or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(label + ' invalide.')
    return value.strip()


def fields(values, declaration=False):
    if not isinstance(values, dict):
        raise ValueError('Fiche appareil invalide.')
    allowed = {'kind', 'version', 'transport', 'agent_protocol'} if declaration else {'id', 'name', 'owner', 'kind', 'version'}
    if set(values) - allowed:
        raise ValueError('Champ de fiche appareil non admis.')
    result = {}
    if 'agent_protocol' in values:
        if type(values['agent_protocol']) is not int or values['agent_protocol'] not in (3,4):
            raise ValueError('Protocole agent invalide.')
        result['agent_protocol'] = values['agent_protocol']
    if 'kind' in values:
        if not isinstance(values['kind'], str) or values['kind'] not in KINDS:
            raise ValueError('Type attendu : PC, téléphone, tablette ou non renseigné.')
        result['kind'] = values['kind']
    for key in ('name', 'owner', 'version'):
        if key in values:
            result[key] = text(values[key], {'name': 'Nom', 'owner': 'Propriétaire', 'version': 'Version'}[key], 80 if key != 'version' else 48)
            if key == 'name' and not result[key]:
                raise ValueError('Nom de l’appareil obligatoire.')
    if 'transport' in values:
        if not isinstance(values['transport'], str) or values['transport'] not in TRANSPORTS:
            raise ValueError('Transport déclaré invalide.')
        result['transport'] = values['transport']
    return result


class Revocations:
    """Append-only identities. Corruption denies access rather than resetting it."""
    def __init__(self, home):
        self.directory = Path(home) / 'securite'
        self.path = self.directory / 'revocations.json'
        self.lock = threading.RLock()
        self.existed = self.path.exists()
        if not self.existed:
            from wg_crypto import private_directory
            private_directory(self.directory)
            write_json(self.path, {'version': 1, 'revocations': {}})
        self.snapshot()

    @staticmethod
    def validate(value):
        if not isinstance(value, dict) or value.get('version') != 1 or not isinstance(value.get('revocations'), dict):
            raise ValueError('Registre de révocations illisible : accès refusé.')
        if len(value['revocations']) > 100000:
            raise ValueError('Registre de révocations trop volumineux : accès refusé.')
        for identity, record in value['revocations'].items():
            if not re.fullmatch('[0-9a-f]{16}', identity) or not isinstance(record, dict):
                raise ValueError('Registre de révocations invalide : accès refusé.')
            epoch = record.get('epoch')
            if type(epoch) not in (int, float) or not math.isfinite(epoch) or epoch <= 0:
                raise ValueError('Date de révocation invalide : accès refusé.')
            text(record.get('reason', ''), 'Motif', 80)
        return value

    def snapshot(self):
        with self.lock:
            return self.validate(read_json(self.path))

    def contains(self, identity):
        return identity in self.snapshot()['revocations']

    def merge(self, value):
        incoming = self.validate(value)
        # file_lock also covers distinct AccessStore instances and processes.
        import sys
        from core import ROOT
        from kiara_shared.file_lock import locked
        with self.lock, locked(self.path):
            current = self.snapshot()
            for identity, record in incoming['revocations'].items():
                current['revocations'].setdefault(identity, record)
            write_json(self.path, current)
        return self.snapshot()

    def revoke(self, identity, reason='revoke'):
        if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{16}', identity):
            raise ValueError('Identifiant appareil invalide.')
        return self.merge({'version': 1, 'revocations': {identity: {'epoch': time.time(), 'reason': reason}}})
