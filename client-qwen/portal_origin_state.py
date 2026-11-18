"""Durable, non-destructive port selection for the Tauri desktop profile.

The relay reads an existing marker. A first marker may be recorded for a
profile with no Tauri directory, settings or migration checkpoint; this does
not inventory data held by other engines or migrate existing Tauri origins.
Invalid state fails closed.
"""
from __future__ import annotations

import json
import errno
import os
from pathlib import Path
import re
import socket
import stat
import tempfile

FIRST_PORT = 17841
LAST_PORT = 17850


class OriginStateError(RuntimeError):
    pass


class OriginPortsBusy(OriginStateError):
    pass


def fresh_tauri_storage_absent(settings, *, linux, include_settings=True):
    """Treat anything present or inaccessible as existing, never as empty.

    The caller must hold the desktop profile lock. This checks only the Tauri
    directory used for this profile; it does not inventory historical origins.
    """
    settings = Path(settings)
    if type(linux) is not bool or type(include_settings) is not bool or not re.fullmatch(r'[0-9a-f]{20}', settings.stem):
        return False
    view = settings.parent / (('tauri-webview-' if linux else 'webview-') + settings.stem)
    paths = [view, settings.with_suffix('.tauri-migration')]
    if include_settings:
        paths.append(settings)
    for path in paths:
        try:
            path.lstat()
            return False
        except FileNotFoundError:
            continue
        except OSError:
            return False
    return True


def reserve_fresh_origin(settings, *, linux, ports=range(FIRST_PORT, LAST_PORT + 1)):
    """Record a free port while it is bound, before initializing local settings.

    The profile lock must remain held. Rebinding the normal relay can still lose
    a race, in which case its pinned-port path fails rather than changing origin.
    """
    settings = Path(settings)
    ports = tuple(ports)
    if not ports or len(set(ports)) != len(ports) or any(not _valid_port(port) for port in ports):
        raise ValueError('Ports locaux invalides.')
    try:
        settings.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise OriginStateError('Le choix du port local ne peut pas être enregistré.') from error
    for port in ports:
        try:
            reservation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except OSError as error:
            raise OriginStateError('Le port local ne peut pas être vérifié.') from error
        with reservation:
            try:
                if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                    reservation.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                reservation.bind(('127.0.0.1', port))
            except OSError as error:
                # Winsock can report access denied for an exclusive binding.
                if error.errno == errno.EADDRINUSE or getattr(error, 'winerror', None) in (10013, 10048):
                    continue
                raise OriginStateError('Le port local ne peut pas être vérifié.') from error
            if not fresh_tauri_storage_absent(settings, linux=linux):
                raise OriginStateError('Les données locales ont changé pendant leur vérification.')
            return record_origin(settings.with_suffix('.tauri-origin.json'), port)
    raise OriginPortsBusy('Les ports locaux sont occupés.')


def _valid_port(port):
    return type(port) is int and FIRST_PORT <= port <= LAST_PORT


def _unique_fields(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate field')
        value[key] = item
    return value


def read_origin(path):
    """Return None only for a missing marker; invalid or inaccessible is unknown."""
    path = Path(path)
    try:
        if path.is_symlink():
            raise OriginStateError('Le choix du port local est illisible.')
        # A FIFO must not block open() before the regular-file check below.
        # O_NONBLOCK has no effect on ordinary files and is absent on Windows.
        flags = (os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
                 | getattr(os, 'O_NONBLOCK', 0))
        fd = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise OriginStateError('Le choix du port local est illisible.') from error
    try:
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise OriginStateError('Le choix du port local est illisible.')
            content = stream.read(1025)
    except OSError as error:
        raise OriginStateError('Le choix du port local est illisible.') from error
    try:
        if len(content) > 1024:
            raise ValueError('oversize')
        value = json.loads(content.decode('utf-8'), object_pairs_hook=_unique_fields)
        if (not isinstance(value, dict) or set(value) != {'format', 'port'}
                or type(value['format']) is not int or value['format'] != 1
                or not _valid_port(value['port'])):
            raise ValueError('invalid')
    except (UnicodeError, ValueError, KeyError, TypeError) as error:
        raise OriginStateError('Le choix du port local est invalide ; les données ont été conservées.') from error
    return value['port']


def record_origin(path, port):
    """Create once with an atomic no-replace link; never overwrite a prior choice."""
    path = Path(path)
    if not _valid_port(port):
        raise ValueError('Port de récupération invalide.')
    existing = read_origin(path)
    if existing is not None:
        if existing != port:
            raise OriginStateError('Un autre port local est déjà enregistré.')
        return existing
    payload = (json.dumps({'format': 1, 'port': port}, separators=(',', ':')) + '\n').encode('ascii')
    name = None
    try:
        fd, name = tempfile.mkstemp(prefix='.kiara-origin-', suffix='.tmp', dir=path.parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            # Linking a fully flushed file is atomic and cannot replace a marker.
            os.link(name, path)
        except FileExistsError:
            existing = read_origin(path)
            if existing != port:
                raise OriginStateError('Un autre port local est déjà enregistré.')
        if os.name != 'nt':
            directory = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except OriginStateError:
        raise
    except OSError as error:
        raise OriginStateError('Le choix du port local ne peut pas être enregistré.') from error
    finally:
        if name is not None:
            try:
                os.unlink(name)  # Only the unique temporary file created above.
            except FileNotFoundError:
                pass
    if read_origin(path) != port:
        raise OriginStateError('Le choix du port local ne peut pas être vérifié.')
    return port
