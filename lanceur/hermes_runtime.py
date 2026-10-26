"""Resolve Kiara's pinned private runtime before any personal bootstrap."""
import json
import os
from pathlib import Path
import re

POINTER = Path(__file__).resolve().parent.parent/'toolchain/hermes-security-runtime/runtime.json'


def private_installation(manifest_path=None):
    manifest = Path(manifest_path) if manifest_path is not None else POINTER
    if not manifest.is_file():
        return None
    local = Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData/Local'))
    try:
        selected = json.loads(manifest.read_text(encoding='utf-8'))
        source = Path(selected.get('source', '')).resolve()
        python = Path(selected.get('python', '')).resolve()
        locations = [manifest.parent, local/'Fred/runtime-security/hermes-20261021']
        known = any(source == (location/'source').resolve()
                    and python == (location/'venv/Scripts/python.exe').resolve() for location in locations)
        if (selected.get('format') != 1 or selected.get('validated') is not True
                or not known or not python.is_file()
                or not (source/'hermes_cli/main.py').is_file()
                or not re.fullmatch('[a-f0-9]{40}', selected.get('source_commit', ''))):
            raise ValueError('invalid private runtime')
        dependencies = Path(selected.get('dependencies', local/'hermes/installs')).resolve()
        tools = Path(selected.get('tools', local/'hermes/tools')).resolve()
        if not dependencies.is_dir() or not tools.is_dir():
            raise ValueError('missing runtime dependency directories')
        return {'source': source, 'python': python, 'commit': selected['source_commit'],
                'dependencies': dependencies, 'tools': tools, 'private': True}
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ValueError('Le runtime privé Kiara est invalide ; conserver son point de retour.') from error
