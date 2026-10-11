"""Explicitly transfer an existing personal EXE profile; never execute the EXE."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'client-qwen'))
from wg_bridge import validate_profile

FOOTER_MAGIC = b'QWENPROFILE1'
FOOTER_SIZE = 16
MAX_PROFILE_BYTES = 65536


class ProfileError(ValueError):
    """Safe, fixed error text that cannot contain a credential from the input."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProfileError('Le profil contient des champs en double.')
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ProfileError('Le profil contient une valeur JSON invalide.')


def read_exe_profile(executable: Path) -> dict:
    """Bound all reads and validate syntax/schema without touching server state."""
    try:
        with Path(executable).open('rb') as source:
            length = source.seek(0, os.SEEK_END)
            if length <= FOOTER_SIZE:
                raise ProfileError('Cet EXE ne contient pas de profil personnel.')
            source.seek(-FOOTER_SIZE, os.SEEK_END)
            footer = source.read(FOOTER_SIZE)
            if len(footer) != FOOTER_SIZE or footer[4:] != FOOTER_MAGIC:
                raise ProfileError('Cet EXE ne contient pas de profil personnel.')
            size = struct.unpack('<I', footer[:4])[0]
            if not 1 <= size <= MAX_PROFILE_BYTES or size > length - FOOTER_SIZE:
                raise ProfileError('La taille du profil personnel est invalide.')
            source.seek(-FOOTER_SIZE - size, os.SEEK_END)
            encoded = source.read(size)
            if len(encoded) != size:
                raise ProfileError('Le profil personnel est incomplet.')
        profile = json.loads(encoded.decode('utf-8'), object_pairs_hook=_unique_object,
                             parse_constant=_invalid_constant)
        if not isinstance(profile, dict) or type(profile.get('protocol', 1)) is not int:
            raise ProfileError('Le profil personnel est invalide.')
        validate_profile(profile)
    except ProfileError:
        raise
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        # Never echo a JSON exception or any untrusted profile field.
        raise ProfileError('Le profil personnel est invalide.') from None
    except OSError:
        raise ProfileError('Lecture de l’EXE personnel impossible.') from None
    return profile


def private_directory(directory: Path) -> None:
    if os.name == 'nt':
        # Same Windows ACL workflow as the server: current user, SYSTEM, admins.
        # This import defines helpers only; it neither opens nor creates a vault.
        sys.path.insert(0, str(ROOT / 'lanceur'))
        from wg_crypto import private_directory as protect_directory
        protect_directory(directory)
    else:
        directory.chmod(0o700)


def export_profile(executable: Path, directory: Path, *, protect_directory=private_directory) -> Path:
    profile = read_exe_profile(executable)
    directory = Path(directory).resolve()
    if directory.exists():
        raise ProfileError('Choisir un nouveau dossier de sortie privé, encore inexistant.')
    # A new directory has no pre-existing explicit grants to unrelated users.
    directory.mkdir(parents=True, exist_ok=False)
    target = directory / 'profil.fred-android'
    created = False
    try:
        protect_directory(directory)  # Must succeed before the first secret byte.
        encoded = (json.dumps(profile, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
        if len(encoded) > MAX_PROFILE_BYTES:
            raise ProfileError('Le profil exporté dépasse la taille autorisée.')
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(descriptor, 'wb') as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        if created:
            target.unlink(missing_ok=True)
        directory.rmdir()
        raise
    return target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Exporter un profil EXE personnel vers Android, sans modifier les accès serveur.')
    parser.add_argument('--exe', required=True, type=Path, help='EXE personnel à lire, jamais exécuté')
    parser.add_argument('--output-directory', required=True, type=Path, help='Nouveau dossier privé à créer')
    arguments = parser.parse_args(argv)
    try:
        output = export_profile(arguments.exe, arguments.output_directory)
    except ProfileError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        print('Export impossible : vérifier Python, les permissions et le dossier de sortie.', file=sys.stderr)
        return 1
    print(f'Profil Android créé : {output}')
    print('Ce fichier contient un accès personnel en clair. Le transmettre uniquement au destinataire.')
    print('Cet export conserve l’identité existante : utiliser un accès distinct pour chaque appareil.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
