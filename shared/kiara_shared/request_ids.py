"""Versioned request identities; old opaque identities remain readable."""
import re

REQUEST = re.compile(r'(?:[a-f0-9]{32}|v2_[a-f0-9]{32})\Z')


def validate_request_id(value):
    if not isinstance(value,str) or not REQUEST.fullmatch(value):
        raise ValueError('Identifiant de demande invalide.')
    return value
