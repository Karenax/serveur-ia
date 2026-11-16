"""Portable encrypted Agent snapshots with bounded memory use."""

import os
import secrets
import struct
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZIP_STORED, ZipFile

from cryptography.fernet import InvalidToken
from operations import cipher

HEADER = b'KIARA-AGENT-1\0'
BLOCK = 1024 * 1024
MAX_TOKEN = BLOCK * 2
MAX_BYTES = 1024 ** 4


def write_archive(snapshot, target, password):
    snapshot = Path(snapshot).resolve(strict=True)
    target = Path(target).resolve()
    if target.is_relative_to(snapshot) or target.exists():
        raise ValueError('Choisissez un nouveau fichier en dehors des données Projets.')
    salt = secrets.token_bytes(16)
    key = cipher(password, salt)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with tempfile.TemporaryFile(dir=snapshot.parent) as content:
            with ZipFile(content, 'w', compression=ZIP_STORED) as archive:
                for path in sorted(snapshot.rglob('*')):
                    if path.is_symlink() or path.is_junction():
                        raise ValueError('Lien interdit dans la sauvegarde Agent.')
                    if path.is_file():
                        archive.write(path, path.relative_to(snapshot).as_posix())
            if content.tell() > MAX_BYTES:
                raise ValueError('Sauvegarde Agent trop volumineuse.')
            content.seek(0)
            with temporary.open('wb') as output:
                output.write(HEADER + salt)
                index = 0
                while True:
                    block = content.read(BLOCK)
                    token = key.encrypt(struct.pack('>Q', index) + block)
                    output.write(struct.pack('>I', len(token)))
                    output.write(token)
                    if not block:
                        break
                    index += 1
                output.flush()
                os.fsync(output.fileno())
        # Windows rename is atomic and refuses to replace an existing file.
        temporary.rename(target)
    finally:
        temporary.unlink(missing_ok=True)


def _decrypt(source, output, password):
    if source.read(len(HEADER)) != HEADER:
        raise ValueError('Format de sauvegarde Agent invalide.')
    salt = source.read(16)
    if len(salt) != 16:
        raise ValueError('Sauvegarde Agent tronquée.')
    key = cipher(password, salt)
    index = 0
    while True:
        size = int.from_bytes(source.read(4), 'big')
        if not 1 <= size <= MAX_TOKEN:
            raise ValueError('Sauvegarde Agent tronquée ou invalide.')
        token = source.read(size)
        try:
            data = key.decrypt(token)
        except InvalidToken as error:
            raise ValueError('Sauvegarde Agent invalide ou phrase incorrecte.') from error
        if data[:8] != struct.pack('>Q', index) or len(data) > BLOCK + 8:
            raise ValueError('Ordre des données Projets invalide.')
        if len(data) == 8:
            if source.read(1):
                raise ValueError('Données après la fin de la sauvegarde Agent.')
            return
        if output.tell() + len(data) - 8 > MAX_BYTES:
            raise ValueError('Sauvegarde Agent trop volumineuse.')
        output.write(data[8:])
        index += 1


def extract_archive(source, destination, password):
    destination = Path(destination).resolve(strict=True)
    if any(destination.iterdir()):
        raise ValueError('Le dossier de préparation doit être vide.')
    with Path(source).open('rb') as encrypted, tempfile.TemporaryFile(dir=destination.parent) as content:
        _decrypt(encrypted, content, password)
        with ZipFile(content) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > MAX_BYTES:
                raise ValueError('Sauvegarde Agent trop volumineuse.')
            for entry in archive.infolist():
                name = entry.filename
                relative = PurePosixPath(name)
                root = relative.parts[0] if relative.parts else ''
                if (relative.is_absolute() or relative.as_posix() != name or '..' in relative.parts
                        or any(':' in part or '\\' in part or part.endswith(('.', ' '))
                               or Path(part).is_reserved() for part in relative.parts)
                        or (name != 'backup.json' and (root not in ('brain', 'erp', 'storage', 'dossiers-clients')
                                                      or len(relative.parts) < 2))
                        or entry.is_dir() or entry.compress_type != ZIP_STORED):
                    raise ValueError('Chemin de sauvegarde Agent invalide.')
                target = destination.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as reader, target.open('xb') as output:
                    while block := reader.read(BLOCK):
                        output.write(block)
