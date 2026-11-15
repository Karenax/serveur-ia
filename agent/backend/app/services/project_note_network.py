"""Explicit bounded note selection inside one project link; read-only acquisition.

No discovery of other projects, database import, source execution or fallback
to a partial selection. This module does not install or register the notes lot.
"""
from contextlib import ExitStack
from dataclasses import dataclass
import os
from pathlib import Path
import stat
import time

from fastapi import HTTPException

from backend.app.models import NetworkLink
from backend.app.project_note_import_schemas import SourceDescriptor
from backend.app.services import document_file_access as access
from backend.app.services.document_discovery import _directory, _reparse
from backend.app.services.project_identity import _project
from backend.app.services.project_note_source_preview import (
    CONTENT_FILES, LEGACY_TEXT, OFFICE, MAX_IMPORT_BYTES, MAX_IMPORT_FILES,
    MAX_IMPORT_VERSIONS, MAX_TEXT_BYTES, _filename, _path, _checked_files,
)


@dataclass(frozen=True)
class ReadLimits:
    entries: int = 256
    directories: int = 128
    seconds: float = 20.0

    def __post_init__(self):
        if (type(self.entries) is not int or not 1 <= self.entries <= 1000
                or type(self.directories) is not int or not 1 <= self.directories <= 128
                or type(self.seconds) not in (int, float) or not 0 < self.seconds <= 120):
            raise ValueError('Bornes de lecture serveur incompatibles')


def _identity(item):
    return item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns


def _read(path, expected, check):
    check()
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or _identity(before) != _identity(expected)
                or access._handle_path(stream) != path):
            raise HTTPException(409, 'Fichier ou emplacement modifié pendant la lecture de la note')
        data = stream.read(expected.st_size + 1)
        after = os.fstat(stream.fileno())
    if len(data) != expected.st_size or _identity(before) != _identity(after):
        raise HTTPException(409, 'Note modifiée pendant la lecture ; reprendre un aperçu complet')
    check()
    return data


class Selection:
    def __init__(self, stack, limits):
        self.stack, self.limits = stack, limits
        self.started = time.monotonic()
        self.entries = 0
        self.directories = {}
        self.files = {}
        self.total_bytes = 0
        self.attachment_count = self.attachment_bytes = 0

    def check(self):
        if time.monotonic() - self.started >= self.limits.seconds:
            raise HTTPException(408, 'Délai de lecture de la note dépassé ; aucun import partiel')

    def hold(self, path):
        self.check()
        if path not in self.directories:
            if len(self.directories) >= self.limits.directories:
                raise HTTPException(413, 'Trop de dossiers dans la sélection de note')
            self.directories[path] = self.stack.enter_context(_directory(path))
        return self.directories[path][0]

    def listing(self, path):
        handle = self.hold(path)
        result = []
        with os.scandir(handle) as entries:
            for entry in entries:
                self.check()
                self.entries += 1
                if self.entries > self.limits.entries:
                    raise HTTPException(413, 'Trop d’entrées dans la note ; aucune sélection partielle')
                _filename(entry.name)
                listed = entry.stat(follow_symlinks=False)
                metadata = (path / entry.name).lstat()
                # Windows DirEntry returns cached enumeration metadata, including
                # incomplete native identity. The fresh lstat is the source
                # observation; held parents, opened files and final lstat checks
                # establish a coherent selection without comparing cache values.
                if _reparse(listed) or _reparse(metadata):
                    raise HTTPException(403, 'Lien symbolique ou jonction dans la sélection de note')
                result.append((entry.name, metadata))
        return sorted(result, key=lambda entry: entry[0])

    def add(self, relative, path, metadata, *, single=False):
        self.check()
        if _reparse(metadata) or not stat.S_ISREG(metadata.st_mode):
            raise HTTPException(403, 'Fichier régulier sans redirection requis')
        if single:
            _filename(relative)
            suffix = path.suffix.casefold()
            if suffix not in LEGACY_TEXT | OFFICE:
                raise HTTPException(422, 'Choisir une note HTML/TXT/MD, un document Office ou un dossier moderne de note')
            kind = 'external' if suffix in OFFICE else 'legacy_text'
        else:
            kind = _path(relative)
        maximum = MAX_IMPORT_BYTES
        if ((kind in {'content', 'version'} and not relative.endswith('content.html'))
                or (kind == 'legacy_text' and path.suffix.casefold() not in {'.html', '.htm'})):
            maximum = MAX_TEXT_BYTES
        if kind == 'attachment':
            maximum = 5 * 1024 * 1024
            self.attachment_count += 1
            self.attachment_bytes += metadata.st_size
            if self.attachment_count > 20 or self.attachment_bytes > 25 * 1024 * 1024:
                raise HTTPException(413, 'Toutes les pièces doivent tenir dans20éléments/25Mio')
        if not 0 <= metadata.st_size <= maximum or (kind in {'attachment', 'external'} and not metadata.st_size):
            raise HTTPException(413, 'Fichier source dépassant les limites de la note')
        if relative.casefold() in {name.casefold() for name in self.files}:
            raise HTTPException(422, 'Noms de note ambigus par la casse')
        self.total_bytes += metadata.st_size
        if len(self.files) >= MAX_IMPORT_FILES or self.total_bytes > MAX_IMPORT_BYTES:
            raise HTTPException(413, 'Note limitée à200fichiers/50Mio, sans omission')
        self.files[relative] = path, metadata

    def note_directory(self, path):
        entries = self.listing(path)
        for name, metadata in entries:
            child = path / name
            if stat.S_ISDIR(metadata.st_mode):
                if name == 'attachments':
                    for filename, filemeta in self.listing(child):
                        self.add('attachments/' + filename, child / filename, filemeta)
                elif name == 'versions':
                    versions = self.listing(child)
                    if len(versions) > MAX_IMPORT_VERSIONS:
                        raise HTTPException(413, 'Historique dépassant50versions')
                    for key, foldermeta in versions:
                        _path('versions/' + key + '/content.txt')
                        if not stat.S_ISDIR(foldermeta.st_mode):
                            raise HTTPException(422, 'Dossier de version source requis')
                        historic = self.listing(child / key)
                        if not historic:
                            raise HTTPException(422, 'Version source vide ; historique incomplet')
                        for filename, filemeta in historic:
                            self.add('versions/' + key + '/' + filename, child / key / filename, filemeta)
                else:
                    raise HTTPException(422, 'Le dossier choisi doit contenir uniquement les éléments de cette note')
            else:
                self.add(name, child, metadata)
        if 'manifest.json' not in self.files or not (CONTENT_FILES & self.files.keys()):
            raise HTTPException(422, 'Choisir le dossier complet d’une seule note, avec manifeste et contenu courant')

    def freeze(self, *, single=False):
        result = {name: _read(path, metadata, self.check) for name, (path, metadata) in sorted(self.files.items())}
        for path, (_, metadata) in self.directories.items():
            current = path.lstat()
            if _reparse(current) or _identity(current) != _identity(metadata):
                raise HTTPException(409, 'Dossier source modifié pendant la sélection complète')
        for path, metadata in self.files.values():
            current = path.lstat()
            if _reparse(current) or _identity(current) != _identity(metadata):
                raise HTTPException(409, 'Un fichier source a changé pendant la sélection complète')
        if single:
            suffix = Path(next(iter(result))).suffix.casefold()
            _checked_files(result, external=suffix in OFFICE, legacy=suffix in LEGACY_TEXT)
        else:
            _checked_files(result)
        self.check()
        return result


def acquire_note(db, project_id, descriptor: SourceDescriptor, *, policy=None, limits=None):
    """Selected file or note directory, no source database or namespace discovery."""
    _project(db, project_id, write=True)  # Before configuration/path probes.
    descriptor = SourceDescriptor.model_validate(descriptor.model_dump(mode='json'))
    if descriptor.kind != 'project_link':
        raise HTTPException(422, 'Lien de ce projet et sélection relative requis')
    relative = access._relative(descriptor.relative_path)
    if len(relative.split('/')) > 16:
        raise HTTPException(422, 'Chemin de note limité à16niveaux sous le lien du projet')
    link = db.query(NetworkLink).filter_by(project_id=project_id, id=descriptor.link_id).first()
    if link is None:
        raise HTTPException(404, 'Lien absent de ce projet')
    policy = access.configured_policy(project_id) if policy is None else policy
    limits = ReadLimits() if limits is None else limits
    if not isinstance(policy, access.FilePolicy) or not isinstance(limits, ReadLimits):
        raise HTTPException(409, 'Politique et bornes de lecture serveur requises')
    if not policy.roots:
        raise HTTPException(409, 'Renseigner les racines documentaires autorisées sur le serveur')
    configured = access._mapped(link.chemin, policy)
    lexical_roots = [Path(value) for value in policy.roots if configured == Path(value) or configured.is_relative_to(Path(value))]
    if not lexical_roots:
        raise HTTPException(403, 'Lien hors des racines documentaires autorisées')
    try:
        root = configured.resolve(strict=True)
        if not any(root.is_relative_to(access.resolve_root(value, policy)) for value in lexical_roots):
            raise HTTPException(403, 'Lien résolu hors des racines documentaires autorisées')
        root_metadata = root.stat()
        with ExitStack() as stack:
            selection = Selection(stack, limits)
            if stat.S_ISREG(root_metadata.st_mode):
                if relative not in {'', root.name}:
                    raise HTTPException(403, 'Ce lien autorise uniquement son fichier')
                selection.add(root.name, root, root_metadata, single=True)
                result = selection.freeze(single=True)
            elif stat.S_ISDIR(root_metadata.st_mode):
                selection.hold(root)
                candidate = root
                for index, part in enumerate(relative.split('/') if relative else []):
                    candidate /= part
                    metadata = candidate.lstat()
                    if _reparse(metadata):
                        raise HTTPException(403, 'Redirection dans le chemin relatif de la note')
                    if index < len(relative.split('/')) - 1:
                        selection.hold(candidate)
                candidate = candidate.resolve(strict=True)
                if not candidate.is_relative_to(root):
                    raise HTTPException(403, 'Note hors du lien de ce projet')
                metadata = candidate.lstat()
                single = stat.S_ISREG(metadata.st_mode)
                if single:
                    selection.add(candidate.name, candidate, metadata, single=True)
                elif stat.S_ISDIR(metadata.st_mode):
                    selection.note_directory(candidate)
                else:
                    raise HTTPException(422, 'Note sous forme de fichier ou dossier régulier requise')
                result = selection.freeze(single=single)
            else:
                raise HTTPException(422, 'Lien vers un fichier ou dossier régulier requis')
            if configured.resolve(strict=True) != root or _identity(root.stat()) != _identity(root_metadata):
                raise HTTPException(409, 'Lien modifié pendant la lecture de la note')
            return result
    except FileNotFoundError as exc:
        code = 409 if not configured.exists() else 404
        raise HTTPException(code, 'Lien réseau indisponible' if code == 409 else 'Note ou élément source absent du lien') from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(409, 'Sélection de note illisible ou non conforme ; conserver les originaux') from exc
