"""Worker groups available for a staged Agent deployment."""

GROUPS = frozenset({'mail', 'cdc', 'audio', 'documents', 'planning', 'knowledge'})


def validate_groups(value):
    if (not isinstance(value, list) or any(not isinstance(group, str) or group not in GROUPS for group in value)
            or len(value) != len(set(value))):
        raise ValueError('Indiquez une liste de groupes de traitements Agent connus et sans doublons.')
    return value
