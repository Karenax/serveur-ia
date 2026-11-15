"""Pure relative path policy shared by acquisition and offline archives."""
from pathlib import PureWindowsPath
from fastapi import HTTPException


def _relative(value):
    if (not isinstance(value, str) or len(value) > 2048 or PureWindowsPath(value).drive
            or value.startswith(('\\', '/')) or any(ord(char) < 32 for char in value)):
        raise HTTPException(422, 'Chemin relatif au lien du projet requis')
    if value in {'', '.'}:
        return ''
    parts = value.replace('\\', '/').split('/')
    for part in parts:
        if (not part or part in {'.', '..'} or part != part.rstrip(' .')
                or any(char in part for char in ':<>"|?*')
                or part.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                    *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}):
            raise HTTPException(422, 'Chemin documentaire relatif invalide')
    return '/'.join(parts)


