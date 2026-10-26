"""Memory operations; the caller owns the access and database transaction."""
import base64
import json
import secrets
from pathlib import Path
from workspace_types import Conflict, Denied, identifier, text, MAX_TEXT, HISTORY_RESET_ID
from kiara_shared.attachments import validate_message

def execute(workspace, db, owner, values, now, prepared=None):
    action = values.get("action")
    if action in ('personal_memory_create', 'personal_memory_save', 'personal_memory_delete', 'memory_create', 'memory_save', 'memory_delete'):
        from memory_service import legacy_action
        result = legacy_action(workspace, db, owner, action, values)
    else:
        raise ValueError('Action inconnue.')
    return result, True
