"""Anchored publication IO: exclusive candidates and promotion without replacement.

This is not a publication command. Its paths must be resolved by a scoped server
service using the explicit write policy. Opening a directory creates no files.
Directory and file identities are retained for durable receipt reconciliation.
"""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import stat
import sys

from fastapi import HTTPException

from .document_file_access import _absolute
from .document_paths import _relative

MAX_BYTES = DOCUMENT_IMPORT_BYTES


def _name(value):
    if not isinstance(value, str) or not value or len(value) > 255 or _relative(value) != value or '/' in value:
        raise HTTPException(422, 'Nom de fichier documentaire simple requis')
    return value


class _Windows:
    """Native relative opens/rename; never reopen a candidate by absolute path."""
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.c = ctypes
        self.w = wintypes
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.nt = ctypes.WinDLL('ntdll')

        class UnicodeString(ctypes.Structure):
            _fields_ = [('Length', wintypes.USHORT), ('MaximumLength', wintypes.USHORT), ('Buffer', wintypes.LPWSTR)]

        class ObjectAttributes(ctypes.Structure):
            _fields_ = [('Length', wintypes.ULONG), ('RootDirectory', wintypes.HANDLE),
                        ('ObjectName', ctypes.POINTER(UnicodeString)), ('Attributes', wintypes.ULONG),
                        ('SecurityDescriptor', wintypes.LPVOID), ('SecurityQualityOfService', wintypes.LPVOID)]

        class IOStatusBlock(ctypes.Structure):
            _fields_ = [('Status', ctypes.c_void_p), ('Information', ctypes.c_size_t)]

        class FileIdInfo(ctypes.Structure):
            _fields_ = [('VolumeSerialNumber', ctypes.c_ulonglong), ('FileId', ctypes.c_ubyte * 16)]

        class TagInfo(ctypes.Structure):
            _fields_ = [('FileAttributes', wintypes.DWORD), ('ReparseTag', wintypes.DWORD)]

        self.UnicodeString, self.ObjectAttributes = UnicodeString, ObjectAttributes
        self.IOStatusBlock, self.FileIdInfo = IOStatusBlock, FileIdInfo
        self.TagInfo = TagInfo
        self.kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self.kernel.CreateFileW.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.CloseHandle.restype = wintypes.BOOL
        self.kernel.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        self.kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
        self.nt.NtCreateFile.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD,
            ctypes.POINTER(ObjectAttributes), ctypes.POINTER(IOStatusBlock), wintypes.LPVOID,
            wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, wintypes.LPVOID, wintypes.ULONG]
        self.nt.NtCreateFile.restype = wintypes.LONG
        self.nt.NtSetInformationFile.argtypes = [wintypes.HANDLE, ctypes.POINTER(IOStatusBlock),
                                               wintypes.LPVOID, wintypes.ULONG, wintypes.ULONG]
        self.nt.NtSetInformationFile.restype = wintypes.LONG
        self.nt.RtlNtStatusToDosError.argtypes = [wintypes.LONG]
        self.nt.RtlNtStatusToDosError.restype = wintypes.ULONG

    def checked(self, status):
        if status < 0:
            raise self.c.WinError(self.nt.RtlNtStatusToDosError(status))

    def directory(self, path):
        # Deny WRITE and DELETE sharing: a held ancestor cannot be replaced,
        # renamed or turned into a junction while the publication uses it.
        handle = self.kernel.CreateFileW(str(path), 0x100081, 1, None, 3, 0x02200000, None)
        if handle == self.c.c_void_p(-1).value:
            raise self.c.WinError(self.c.get_last_error())
        try:
            attributes = self.attributes(handle)
            if not attributes & 0x10 or attributes & 0x400:
                raise OSError('Dossier régulier sans reparse point requis')
            return handle
        except BaseException:
            self.kernel.CloseHandle(handle)
            raise

    def file(self, directory, name, *, create=False, rename=False):
        encoded = name.encode('utf-16-le')
        text = self.c.create_string_buffer(encoded + b'\0\0')
        unicode = self.UnicodeString(len(encoded), len(encoded) + 2,
                                     self.c.cast(text, self.w.LPWSTR))
        attributes = self.ObjectAttributes(self.c.sizeof(self.ObjectAttributes), directory,
                                          self.c.pointer(unicode), 0x40, None, None)
        handle, status = self.w.HANDLE(), self.IOStatusBlock()
        access = 0x80000000 | 0x100000 | (0x40000000 if create else 0) | (0x10000 if rename else 0)
        result = self.nt.NtCreateFile(self.c.byref(handle), access, self.c.byref(attributes), self.c.byref(status),
            None, 0x80, 1, 2 if create else 1, 0x200060, None, 0)
        self.checked(result)
        try:
            if self.attributes(handle) & (0x10 | 0x400):
                raise OSError('Copie régulière sans reparse point requise')
            import msvcrt
            descriptor = msvcrt.open_osfhandle(handle.value, (os.O_RDWR if create else os.O_RDONLY) | os.O_BINARY)
            return os.fdopen(descriptor, 'w+b' if create else 'rb')
        except BaseException:
            self.kernel.CloseHandle(handle)
            raise

    def attributes(self, handle):
        info = self.TagInfo()
        if not self.kernel.GetFileInformationByHandleEx(handle, 9, self.c.byref(info), self.c.sizeof(info)):
            raise self.c.WinError(self.c.get_last_error())
        return info.FileAttributes

    def identity(self, handle):
        info = self.FileIdInfo()
        if not self.kernel.GetFileInformationByHandleEx(handle, 18, self.c.byref(info), self.c.sizeof(info)):
            raise self.c.WinError(self.c.get_last_error())
        file_id = bytes(info.FileId).hex()
        if file_id == '0' * 32:
            raise OSError('Identité persistante du fichier indisponible')
        return f'nt:{info.VolumeSerialNumber}:{file_id}'

    def rename(self, stream, name):
        import msvcrt
        encoded = name.encode('utf-16-le')
        class RenameInfo(self.c.Structure):
            _fields_ = [('ReplaceIfExists', self.w.BOOLEAN), ('RootDirectory', self.w.HANDLE),
                        ('FileNameLength', self.w.ULONG), ('FileName', self.c.c_ubyte * len(encoded))]
        # A simple name and NULL RootDirectory rename within the opened file's
        # current parent. This neither resolves an absolute path nor reopens
        # the guarded parent for write (which would conflict with its lease).
        # Microsoft FILE_RENAME_INFORMATION, same-directory form.
        info = RenameInfo(False, None, len(encoded), (self.c.c_ubyte * len(encoded)).from_buffer_copy(encoded))
        status = self.IOStatusBlock()
        self.checked(self.nt.NtSetInformationFile(msvcrt.get_osfhandle(stream.fileno()), self.c.byref(status),
                                                self.c.byref(info), self.c.sizeof(info), 10))


class AnchoredDirectory:
    """Hold an existing directory within a server-resolved authorized write root."""
    def __init__(self, root, directory):
        self.root, self.path = Path(_absolute(str(root))), Path(_absolute(str(directory)))
        if self.path != self.root and not self.path.is_relative_to(self.root):
            raise HTTPException(403, 'Destination hors de la racine d’écriture autorisée')
        self.stack = ExitStack()
        self.native = _Windows() if os.name == 'nt' else None
        self.handle = None

    def __enter__(self):
        if self.handle is not None:
            raise RuntimeError('Dossier de publication déjà ouvert')
        try:
            if self.native:
                parts = list(reversed([self.path, *self.path.parents]))
                for path in parts:
                    handle = self.native.directory(path)
                    self.stack.callback(self.native.kernel.CloseHandle, handle)
                self.handle = handle
                self.identity = self.native.identity(handle)
            else:
                if sys.platform != 'linux':
                    raise OSError('Publication ancrée disponible sur Windows et Linux uniquement')
                handle = os.open(self.path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                self.stack.callback(os.close, handle)
                for part in self.path.parts[1:]:
                    handle = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=handle)
                    self.stack.callback(os.close, handle)
                self.handle = handle
                value = os.fstat(handle)
                self.identity = f'posix:{value.st_dev}:{value.st_ino}'
            return self
        except (OSError, ValueError) as exc:
            self.stack.close()
            raise HTTPException(409, 'Dossier de publication indisponible, lié ou déjà utilisé') from exc

    def __exit__(self, *args):
        try:
            return self.stack.__exit__(*args)
        finally:
            self.handle = None

    def _open(self, name, *, create=False, rename=False):
        _name(name)
        if self.handle is None:
            raise RuntimeError('Dossier de publication non ouvert')
        if self.native:
            return self.native.file(self.handle, name, create=create, rename=rename)
        flags = os.O_NOFOLLOW | (os.O_RDWR | os.O_CREAT | os.O_EXCL if create else os.O_RDONLY)
        return os.fdopen(os.open(name, flags, 0o600, dir_fd=self.handle), 'w+b' if create else 'rb')

    def _inspect(self, stream):
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= MAX_BYTES:
            raise HTTPException(409, 'Copie de publication régulière et bornée requise')
        if self.native:
            import msvcrt
            identity = self.native.identity(msvcrt.get_osfhandle(stream.fileno()))
        else:
            identity = f'posix:{before.st_dev}:{before.st_ino}'
        stream.seek(0)
        data = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
        if (len(data) != before.st_size or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise HTTPException(409, 'Copie de publication modifiée pendant la vérification')
        return {'identity':identity, 'sha256':hashlib.sha256(data).hexdigest(), 'size_bytes':len(data)}

    def exists(self, name):
        try:
            with self._open(name):
                return True
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise HTTPException(409, 'Destination existante ou indisponible') from exc

    def create_candidate(self, name, content):
        if not isinstance(content, bytes) or not 1 <= len(content) <= MAX_BYTES:
            raise HTTPException(413, 'Copie documentaire bornée à 50 Mio')
        try:
            with self._open(name, create=True) as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
                return self._inspect(stream)
        except OSError as exc:
            # A partial candidate is retained; never unlink caller-visible files.
            raise HTTPException(409, 'Création exclusive de la copie indisponible') from exc

    def verify(self, name, expected):
        try:
            with self._open(name) as stream:
                actual = self._inspect(stream)
                if actual != expected:
                    raise HTTPException(409, 'Identité ou empreinte de publication différente du reçu préparé')
                return actual
        except OSError as exc:
            raise HTTPException(409, 'Copie de publication indisponible') from exc

    def describe(self, name):
        try:
            with self._open(name) as stream:
                return self._inspect(stream)
        except OSError as exc:
            raise HTTPException(409, 'Fichier de remplacement indisponible') from exc

    def promote(self, candidate, filename, expected):
        _name(filename)
        if candidate == filename:
            raise HTTPException(422, 'Candidat et destination doivent être distincts')
        try:
            with self._open(candidate, rename=True) as stream:
                if self._inspect(stream) != expected:
                    raise HTTPException(409, 'Candidat différent du reçu préparé')
                if self.native:
                    self.native.rename(stream, filename)
                else:
                    # Link the opened descriptor, not a replaceable source name.
                    # Retain the candidate on Linux rather than race an unlink.
                    os.link(f'/proc/self/fd/{stream.fileno()}', filename, dst_dir_fd=self.handle, follow_symlinks=True)
                if self._inspect(stream) != expected:
                    raise HTTPException(409, 'Copie modifiée pendant la publication')
            return self.verify(filename, expected)
        except OSError as exc:
            raise HTTPException(409, 'Publication refusée : destination occupée ou opération indisponible') from exc
