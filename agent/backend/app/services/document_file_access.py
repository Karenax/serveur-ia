"""Project-scoped, read-only acquisition for documents and future notes/visas.

Policy comes from trusted server configuration, never caller paths/JSON. A
project link limits the namespace independently from the configured roots.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat

from fastapi import HTTPException

from ..models import NetworkLink
from .document_package_preview import MAX_SOURCE_BYTES, preview_package
from .document_template_catalogue import document_spec
from .project_identity import _project
from .document_paths import _relative  # re-export compatibility


def _absolute(value):
    if (not isinstance(value, str) or not value or len(value) > 2048
            or any(ord(char) < 32 for char in value) or value.startswith(('\\\\?\\', '\\\\.\\'))
            or not Path(value).is_absolute() or '..' in Path(value).parts):
        raise ValueError('Chemin serveur absolu requis')
    components = Path(value).parts[1:]
    if any(':' in component or any(char in component for char in '<>"|?*')
           or component != component.rstrip(' .') for component in components):
        raise ValueError('Composant de chemin serveur invalide')
    return value


@dataclass(frozen=True)
class FilePolicy:
    roots: tuple[str, ...]
    drive_mappings: tuple[tuple[str, str], ...] = ()
    project_directory: Path | None = None

    def __post_init__(self):
        if not isinstance(self.roots, tuple) or len(self.roots) > 32:
            raise ValueError('Racines documentaires immuables requises')
        for value in self.roots:
            _absolute(value)
        if not isinstance(self.drive_mappings, tuple) or len(self.drive_mappings) > 26:
            raise ValueError('Mappings de lecteurs immuables requis')
        seen = set()
        for entry in self.drive_mappings:
            if (not isinstance(entry, tuple) or len(entry) != 2 or not isinstance(entry[0], str)
                    or not re.fullmatch('[A-Z]:', entry[0]) or entry[0] in seen):
                raise ValueError('Mapping de lecteur invalide ou répété')
            seen.add(entry[0])
            _absolute(entry[1])


def configured_policy(project_id=None, *, write=False):
    """Load the explicit roots and the managed directory for this project."""
    try:
        variable = 'AGENT_DOCUMENT_WRITE_ROOTS' if write else 'AGENT_DOCUMENT_ROOTS'
        roots = json.loads(os.environ.get(variable, '[]'))
        mappings = json.loads(os.environ.get('AGENT_DOCUMENT_DRIVE_MAPPINGS', '{}'))
        if not isinstance(roots, list) or not isinstance(mappings, dict):
            raise ValueError('Listes de configuration requises')
        base = json.loads(os.environ.get('AGENT_DOCUMENT_PROJECT_ROOT', '""'))
        if not isinstance(base, str):
            raise ValueError('Racine des dossiers clients invalide')
        project_directory = None
        if base:
            base = Path(_absolute(base))
            if any(base.is_relative_to(root) or Path(root).is_relative_to(base) for root in roots):
                raise ValueError('Les racines partagées doivent être distinctes des dossiers clients')
            if project_id and re.fullmatch(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}', project_id):
                project_directory = base / project_id
                roots.append(str(project_directory))
        return FilePolicy(tuple(roots), tuple(mappings.items()), project_directory)
    except (ValueError, TypeError) as exc:
        detail = ('Configuration d’écriture documentaire serveur invalide' if write
                  else 'Configuration documentaire serveur invalide')
        raise HTTPException(409, detail) from exc


def resolve_root(path, policy):
    resolved = path.resolve(strict=True)
    if path == policy.project_directory and resolved != path:
        raise HTTPException(403, 'Redirection du dossier client refusée')
    return resolved


def _mapped(value, policy):
    if not isinstance(value, str) or not value:
        raise HTTPException(409, 'Lien projet sans chemin documentaire')
    windows = PureWindowsPath(value)
    mapping = dict(policy.drive_mappings).get(windows.drive.upper())
    if mapping:
        if not windows.is_absolute():
            raise HTTPException(422, 'Chemin de lecteur absolu requis')
        suffix = '/'.join(windows.parts[1:])
        value = str(Path(mapping) / _relative(suffix))
    try:
        return Path(_absolute(value))
    except ValueError as exc:
        raise HTTPException(422, 'Chemin du lien serveur invalide') from exc


def _handle_path(stream):
    """Verify the path of the opened handle, including a Windows junction race."""
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        import msvcrt
        function = ctypes.WinDLL('kernel32', use_last_error=True).GetFinalPathNameByHandleW
        function.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
        function.restype = wintypes.DWORD
        handle = msvcrt.get_osfhandle(stream.fileno())
        size = function(handle, None, 0, 0)
        if not 0 < size < 32768:
            raise OSError('Chemin du fichier ouvert indisponible')
        buffer = ctypes.create_unicode_buffer(size + 1)
        length = function(handle, buffer, len(buffer), 0)
        if not 0 < length < len(buffer):
            raise OSError('Chemin du fichier ouvert indisponible')
        value = buffer.value
        if value.startswith('\\\\?\\UNC\\'):
            value = '\\\\' + value[8:]
        elif value.startswith('\\\\?\\'):
            value = value[4:]
        return Path(value)
    # Linux server qualification uses its actual descriptor, never stream.name.
    return Path(os.readlink(f'/proc/self/fd/{stream.fileno()}'))


def acquire_file(db, project_id, *, link_id, relative_path='', expected_sha256=None, policy=None):
    """Return frozen bytes plus metadata; no file/row creation, commit or opening UI."""
    _project(db, project_id)  # FIRST: no configuration or filesystem probe before scope.
    if not isinstance(link_id, str) or not 1 <= len(link_id) <= 36:
        raise HTTPException(422, 'Identifiant de lien documentaire invalide')
    link = db.query(NetworkLink).filter_by(project_id=project_id, id=link_id).first()
    if link is None:
        raise HTTPException(404, 'Lien documentaire introuvable dans ce projet')
    relative = _relative(relative_path)
    if expected_sha256 is not None and (not isinstance(expected_sha256, str)
                                       or not re.fullmatch('[0-9a-f]{64}', expected_sha256)):
        raise HTTPException(422, 'Empreinte documentaire invalide')
    policy = configured_policy(project_id) if policy is None else policy
    if not isinstance(policy, FilePolicy):
        raise HTTPException(409, 'Politique documentaire serveur requise')
    if not policy.roots:
        raise HTTPException(409, 'Renseigner les racines documentaires autorisées sur le serveur')
    configured = _mapped(link.chemin, policy)
    lexical_roots = [allowed for value in policy.roots if configured == (allowed := Path(value))
                     or configured.is_relative_to(allowed)]
    if not lexical_roots:
        raise HTTPException(403, 'Lien du projet hors des racines documentaires autorisées')
    try:
        roots = [resolve_root(value, policy) for value in lexical_roots]
        root = configured.resolve(strict=True)
        if not any(root == allowed or root.is_relative_to(allowed) for allowed in roots):
            raise HTTPException(403, 'Lien du projet hors des racines documentaires autorisées')
        root_stat = root.stat()
        is_file = stat.S_ISREG(root_stat.st_mode)
        if is_file:
            if relative not in {'', root.name}:
                raise HTTPException(403, 'Ce lien autorise uniquement son fichier')
            candidate = root
        elif stat.S_ISDIR(root_stat.st_mode):
            candidate = (root / relative).resolve(strict=True)
            if not candidate.is_relative_to(root):
                raise HTTPException(403, 'Document hors du lien de ce projet')
        else:
            raise HTTPException(409, 'Lien documentaire vers un fichier ou dossier régulier requis')
        before_path = candidate.stat()
        if not stat.S_ISREG(before_path.st_mode):
            raise HTTPException(409, 'Fichier documentaire régulier requis')
        with candidate.open('rb') as stream:
            before = os.fstat(stream.fileno())
            opened = _handle_path(stream)
            if opened != candidate or (before.st_dev, before.st_ino) != (before_path.st_dev, before_path.st_ino):
                raise HTTPException(409, 'Emplacement documentaire modifié pendant l’ouverture')
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_SOURCE_BYTES:
                raise HTTPException(413, 'Fichier documentaire de 50 Mio maximum requis')
            data = stream.read(MAX_SOURCE_BYTES + 1)
            after = os.fstat(stream.fileno())
        if len(data) > MAX_SOURCE_BYTES:
            raise HTTPException(413, 'Fichier documentaire de 50 Mio maximum requis')
        if not data:
            raise HTTPException(422, 'Document vide')
        after_path = candidate.stat()
        def identity(item):
            return item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns
        if (len(data) != before.st_size or identity(before) != identity(after) or identity(before) != identity(after_path)
                or configured.resolve(strict=True) != root or identity(root.stat()) != identity(root_stat)):
            raise HTTPException(409, 'Document ou lien modifié pendant l’acquisition ; réessayer')
    except FileNotFoundError as exc:
        if not configured.exists():
            raise HTTPException(409, 'Dossier ou fichier du lien réseau indisponible') from exc
        raise HTTPException(404, 'Document absent dans le lien du projet') from exc
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(409, 'Lecture documentaire indisponible') from exc
    sha256 = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and sha256 != expected_sha256:
        raise HTTPException(409, 'Document modifié depuis l’aperçu')
    return data, {'project_id': project_id, 'link_id': link.id, 'relative_path': relative,
                  'filename': candidate.name, 'size_bytes': len(data), 'sha256': sha256,
                  'read_only': True, 'drive_mapped': configured != Path(link.chemin)}


def preview_file(db, project_id, *, link_id, relative_path, document_id, values, policy=None):
    data, source = acquire_file(db, project_id, link_id=link_id, relative_path=relative_path, policy=policy)
    try:
        spec = document_spec(document_id)
        if Path(source['filename']).suffix.lower() != '.' + spec['format'].lower():
            raise HTTPException(422, 'Extension du fichier incompatible avec la trame')
        report = preview_package(data, document_id, values)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {**report, 'source': source}
