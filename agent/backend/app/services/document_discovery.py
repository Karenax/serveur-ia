"""Bounded, read-only template discovery inside one authorized project link.

Candidates are observations, never approved documents. Acquisition and the OOXML
preview must run again after a human choice. Search preferences are independent
of the immutable field mappings; this module also accepts trusted saved rules.
"""
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
import unicodedata

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import NetworkLink
from . import document_file_access as files
from .document_package_preview import MAX_SOURCE_BYTES
from .document_search_rules import SearchRule, default_rule, fold, phrase  # re-export compatibility
from .document_template_catalogue import document_spec
from .project_identity import _project


@dataclass(frozen=True)
class ScanLimits:
    entries: int = 5000
    directories: int = 500
    depth: int = 12
    candidates: int = 80
    seconds: float = 20.0

    def __post_init__(self):
        for name, maximum in (('entries', 50000), ('directories', 2000), ('depth', 32), ('candidates', 200)):
            if type(getattr(self, name)) is not int or not 1 <= getattr(self, name) <= maximum:
                raise ValueError('Limite de découverte invalide')
        if type(self.seconds) not in (int, float) or not 0 < self.seconds <= 120:
            raise ValueError('Délai de découverte invalide')


def _identity(item):
    return item.st_dev, item.st_ino, item.st_mtime_ns


def _reparse(item):
    return stat.S_ISLNK(item.st_mode) or bool(getattr(item, 'st_file_attributes', 0)
                                            & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))


@contextmanager
def _directory(path):
    """Hold directories throughout enumeration; Windows handles deny deletion.

    Windows scandir requires a pathname; its opened directory is checked against
    the held handle. Linux enumerates the actual descriptor. Neither follows a
    child reparse point. A blocking SMB call remains subject to the OS timeout.
    """
    before = path.lstat()
    if _reparse(before) or not stat.S_ISDIR(before.st_mode):
        raise HTTPException(409, 'Dossier modifié pendant la découverte')
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                           wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        close = kernel.CloseHandle
        close.argtypes = [wintypes.HANDLE]
        close.restype = wintypes.BOOL
        handle = create(str(path), 0x80000000, 0x3, None, 3, 0x02000000 | 0x00200000, None)
        if handle == wintypes.HANDLE(-1).value:
            raise OSError(ctypes.get_last_error(), 'Ouverture du dossier indisponible')
        try:
            final = kernel.GetFinalPathNameByHandleW
            final.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
            final.restype = wintypes.DWORD
            buffer = ctypes.create_unicode_buffer(32768)
            length = final(handle, buffer, len(buffer), 0)
            if not 0 < length < len(buffer):
                raise HTTPException(409, 'Handle du dossier indisponible')
            value = buffer.value
            if value.startswith('\\\\?\\UNC\\'):
                value = '\\\\' + value[8:]
            elif value.startswith('\\\\?\\'):
                value = value[4:]
            after = path.lstat()
            if Path(value) != path or _identity(after) != _identity(before) or _reparse(after):
                raise HTTPException(409, 'Emplacement du dossier modifié pendant ouverture')
            yield str(path), before
        finally:
            close(handle)
    else:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            opened = os.fstat(descriptor)
            if _identity(opened) != _identity(before):
                raise HTTPException(409, 'Emplacement du dossier modifié pendant ouverture')
            yield descriptor, before
        finally:
            os.close(descriptor)


def _progress(folders, expected):
    index = 0
    for folder in folders:
        if index < len(expected) and phrase(folder, expected[index]):
            index += 1
    return index


def _version(filename):
    name = fold(Path(filename).stem)
    explicit = re.findall(r'\b(?:v|ver|version|rev|revision)\s*(\d{1,3})\b', name)
    # Also recognize common compact V010 / Rev2 before punctuation normalization.
    explicit += re.findall(r'(?:^|[^a-z0-9])(?:v|ver|version|rev|revision)[ ._-]*(\d{1,3})(?!\d)',
                           unicodedata.normalize('NFKD', Path(filename).stem.casefold()))
    numbers = explicit or re.findall(r'\b(\d{1,3})\b', name)
    return (max(map(int, numbers)) if numbers else None,
            'explicit' if explicit else 'name_numbers' if numbers else 'unknown')


def discover(db, project_id, *, link_id, document_id, rule=None, policy=None,
             limits=None, cancelled=None, on_progress=None):
    _project(db, project_id)  # No path, configuration or rule probe before authorization.
    link = db.query(NetworkLink).filter_by(project_id=project_id, id=link_id).first()
    if link is None:
        raise HTTPException(404, 'Lien documentaire introuvable dans ce projet')
    original_link = link.chemin
    rule = default_rule(document_id) if rule is None else rule
    if not isinstance(rule, SearchRule) or rule.document_id != document_id:
        raise HTTPException(422, 'Règle de découverte incompatible avec la trame')
    spec = document_spec(document_id)
    limits = ScanLimits() if limits is None else limits
    if not isinstance(limits, ScanLimits):
        raise HTTPException(422, 'Limites de découverte serveur requises')
    policy = files.configured_policy(project_id) if policy is None else policy
    if not isinstance(policy, files.FilePolicy) or not policy.roots:
        raise HTTPException(409, 'Renseigner les racines documentaires autorisées sur le serveur')
    configured = files._mapped(original_link, policy)
    allowed = [Path(value) for value in policy.roots
               if configured == Path(value) or configured.is_relative_to(Path(value))]
    if not allowed:
        raise HTTPException(403, 'Lien du projet hors des racines documentaires autorisées')
    started = time.monotonic()
    paths = [tuple(files._relative(value).split('/')) if value != '.' else () for value in rule.relative_paths]
    counts = {'entries': 0, 'files': 0, 'directories': 0}
    skips = {key: 0 for key in ('reparse', 'unrelated_directory', 'excluded', 'input_directory',
                              'depth', 'oversized', 'empty', 'unsafe_name', 'wrong_format', 'name_or_folder')}
    candidates, bounds, observations = [], set(), []
    status = 'completed'

    def stop():
        nonlocal status
        if cancelled and cancelled():
            status = 'cancelled'
            return True
        if time.monotonic() - started >= limits.seconds:
            bounds.add('time')
        if bounds & {'time', 'entries', 'candidates'}:
            status = 'limited'
            return True
        return False

    def notify():
        if on_progress:
            on_progress({'phase': 'discovery', 'examined': dict(counts), 'total': None,
                         'candidates': len(candidates), 'elapsed_seconds': round(time.monotonic() - started, 2)})

    def consider(path, metadata, root, *, direct=False):
        relative = '' if direct else path.relative_to(root).as_posix()
        folders = [*configured.parts, *path.relative_to(root).parts[:-1]] if not direct else []
        if metadata.st_size > MAX_SOURCE_BYTES:
            skips['oversized'] += 1
            return
        if not metadata.st_size:
            skips['empty'] += 1
            return
        if path.suffix.casefold() != '.' + spec['format'].casefold():
            skips['wrong_format'] += 1
            return
        searched = path.name if direct else root.name + '/' + relative
        if any(phrase(searched, value) for value in rule.excluded_tokens):
            skips['excluded'] += 1
            return
        matched_paths = [] if direct else [rule.relative_paths[i] for i, expected in enumerate(paths)
                                          if _progress(folders, expected) == len(expected)]
        matched_names = [value for value in rule.filename_patterns if phrase(path.stem, value)]
        if (not direct and not matched_paths) or not matched_names:
            skips['name_or_folder'] += 1
            return
        version, origin = _version(path.name)
        score = (-(abs(version - rule.preferred_version)) if rule.preferred_version is not None and version is not None
                 else version if rule.preferred_version is None and version is not None else -1000)
        candidates.append({'relative_path': relative, 'filename': path.name, 'size_bytes': metadata.st_size,
            'modified_ns': metadata.st_mtime_ns, 'matched_paths': matched_paths, 'matched_patterns': matched_names,
            'version': version, 'version_origin': origin, 'rank': score, 'direct_file_link': direct,
            'requires_preview': True})
        if len(candidates) >= limits.candidates:
            bounds.add('candidates')

    try:
        root = configured.resolve(strict=True)
        if not any(root.is_relative_to(value) for value in (files.resolve_root(p, policy) for p in allowed)):
            raise HTTPException(403, 'Lien du projet hors des racines documentaires autorisées')
        root_before = root.lstat()
        with ExitStack() as stack:
            if stat.S_ISREG(root_before.st_mode):
                counts['entries'] = counts['files'] = 1
                if not stop():
                    consider(root, root_before, root, direct=True)
            elif stat.S_ISDIR(root_before.st_mode):
                pending = [(root, 0)]
                while pending and not stop():
                    directory, depth = pending.pop()
                    handle, observed = stack.enter_context(_directory(directory))
                    names = set()
                    observed_names = None
                    counts['directories'] += 1
                    with os.scandir(handle) as entries:
                        for entry in entries:
                            if stop():
                                break
                            if counts['entries'] >= limits.entries:
                                bounds.add('entries')
                                break
                            counts['entries'] += 1
                            names.add(entry.name)
                            path = directory / entry.name
                            try:
                                files._relative(path.relative_to(root).as_posix())
                            except HTTPException:
                                skips['unsafe_name'] += 1
                                continue
                            observed_entry = entry.stat(follow_symlinks=False)
                            if _reparse(observed_entry):
                                skips['reparse'] += 1
                                continue
                            if stat.S_ISDIR(observed_entry.st_mode):
                                relative = path.relative_to(root)
                                folders = [*configured.parts, *relative.parts]
                                if any(phrase(root.name + '/' + relative.as_posix(), value) for value in rule.excluded_tokens):
                                    skips['excluded'] += 1
                                elif ((any(word.startswith('donnee') for word in fold(entry.name).split())
                                       and any(word.startswith('entree') for word in fold(entry.name).split()))
                                      or phrase(entry.name, 'data input')):
                                    skips['input_directory'] += 1
                                elif not any(not expected or _progress(folders, expected) for expected in paths):
                                    skips['unrelated_directory'] += 1
                                elif depth >= limits.depth:
                                    skips['depth'] += 1
                                    bounds.add('depth')
                                elif counts['directories'] + len(pending) >= limits.directories:
                                    bounds.add('directories')
                                else:
                                    pending.append((path, depth + 1))
                            elif stat.S_ISREG(observed_entry.st_mode):
                                counts['files'] += 1
                                consider(path, observed_entry, root)
                            if counts['entries'] % 100 == 0:
                                notify()
                        else:
                            observed_names = names
                    observations.append((directory, observed, handle, observed_names))
                    if _identity(directory.lstat()) != _identity(observed):
                        raise HTTPException(409, 'Dossier modifié pendant la découverte ; relancer')
            else:
                raise HTTPException(409, 'Lien documentaire vers un fichier ou dossier régulier requis')
            stop()
            notify()
            # Retained directory handles pin Windows names. Verify the namespace
            # once more; no result from a changed or removed link is delivered.
            if configured.resolve(strict=True) != root or _identity(root.lstat()) != _identity(root_before):
                raise HTTPException(409, 'Lien documentaire modifié pendant découverte ; relancer')
            for directory, observed, handle, names in observations:
                if directory.resolve(strict=True) != directory or _identity(directory.lstat()) != _identity(observed):
                    raise HTTPException(409, 'Arborescence modifiée pendant découverte ; relancer')
                # Windows can defer the directory timestamp update. Compare the
                # names too, with a second pass bounded by the original listing.
                if os.name == 'nt' and names is not None and not stop():
                    with os.scandir(handle) as entries:
                        for entry in entries:
                            if stop():
                                break
                            if entry.name not in names:
                                raise HTTPException(409, 'Arborescence modifiée pendant découverte ; relancer')
                            names.remove(entry.name)
                        else:
                            if names:
                                raise HTTPException(409, 'Arborescence modifiée pendant découverte ; relancer')
            bind = db.get_bind()
            with Session(bind=getattr(bind, 'engine', bind)) as fresh:
                _project(fresh, project_id)
                current = fresh.query(NetworkLink).filter_by(project_id=project_id, id=link_id).first()
                if current is None or current.chemin != original_link:
                    raise HTTPException(409, 'Lien du projet modifié pendant découverte ; relancer')
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(409, 'Découverte indisponible : vérifier le lien et relancer') from exc
    if bounds and status != 'cancelled':
        status = 'limited'
    candidates.sort(key=lambda item: (-item['rank'], item['relative_path'].casefold(), item['relative_path']))
    tied = len(candidates) > 1 and candidates[0]['rank'] == candidates[1]['rank']
    rule_data = asdict(rule)
    return {'project_id': project_id, 'link_id': link_id, 'document_id': document_id,
        'rule': rule_data, 'rule_sha256': hashlib.sha256(json.dumps(rule_data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        'status': status, 'examined': counts, 'total': None, 'limits': asdict(limits), 'bounds': sorted(bounds),
        'skipped': skips, 'candidates': candidates, 'ambiguous': tied or status != 'completed',
        'recommended_path': candidates[0]['relative_path'] if candidates and not tied and status == 'completed' else None,
        'elapsed_seconds': round(time.monotonic() - started, 2), 'read_only': True, 'requires_manual_choice': True}
