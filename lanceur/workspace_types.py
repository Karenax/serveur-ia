"""Shared Workspace validation and domain errors, independent of transport."""
import re
from kiara_shared.history_store import HISTORY_RESET_ID
MAX_TEXT = 500000

class Conflict(ValueError):
    pass

class Denied(ValueError):
    pass

def text(value, maximum, label, empty=False):
    if not isinstance(value, str) or len(value) > maximum or (not empty and (not value.strip())) or ('\x00' in value):
        raise ValueError(label + ' invalide.')
    return value if empty else value.strip()

def identifier(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{32}', value):
        raise ValueError('Identifiant invalide.')
    return value
