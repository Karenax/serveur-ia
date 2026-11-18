"""Detect an old Qt WebEngine profile already held by another process.

Only existing lock files are opened read-only; no browser data is altered.
The check is intentionally repeated after the helper closes because old
versions do not participate in the shared Kiara profile lock.
"""
import os
import ctypes
from pathlib import Path
import stat
import sys

if sys.platform.startswith('linux'):
    import fcntl


class QtProfileUnavailable(RuntimeError):
    pass


class QtProfileInUse(QtProfileUnavailable):
    pass


def _directory(path):
    try:state=path.lstat()
    except FileNotFoundError:return False
    except OSError as error:raise QtProfileUnavailable('Le stockage Qt ne peut pas être vérifié.') from error
    if not stat.S_ISDIR(state.st_mode):raise QtProfileUnavailable('Le stockage Qt ne peut pas être vérifié.')
    return True


def _check_lock(path):
    try:
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_CLOEXEC',0)|getattr(os,'O_NOFOLLOW',0))
    except FileNotFoundError:return
    except OSError as error:raise QtProfileUnavailable('Le stockage Qt ne peut pas être vérifié.') from error
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):raise QtProfileUnavailable('Le stockage Qt ne peut pas être vérifié.')
        for operation in (fcntl.lockf,fcntl.flock):
            try:operation(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise QtProfileInUse('Une ancienne version Qt utilise ce stockage. Fermez-la puis réessayez.') from error
            except OSError as error:raise QtProfileUnavailable('Le verrou Qt ne peut pas être vérifié.') from error
            else:operation(fd,fcntl.LOCK_UN)
    finally:os.close(fd)


def _lock_files(storage):
    if not sys.platform.startswith('linux'):raise QtProfileUnavailable('Contrôle Qt indisponible.')
    root=Path(storage)
    if not root.is_absolute() or not _directory(root):raise QtProfileUnavailable('Stockage Qt indisponible.')
    paths=[]
    for parts in (('Local Storage','leveldb'),('Session Storage',)):
        parent=root
        for part in parts:
            parent=parent/part
            if not _directory(parent):break
        else:paths.append(parent/'LOCK')
    indexed=root/'IndexedDB'
    if _directory(indexed):
        try:
            entries=list(os.scandir(indexed))
            if len(entries)>10000:raise QtProfileUnavailable('Le stockage Qt ne peut pas être vérifié.')
            for entry in entries:
                if entry.name.endswith('.indexeddb.leveldb'):
                    directory=indexed/entry.name
                    if _directory(directory):paths.append(directory/'LOCK')
        except OSError as error:raise QtProfileUnavailable('Le stockage Qt ne peut pas être vérifié.') from error
    return paths


def ensure_qt_profile_idle(storage):
    """Fail closed if a legacy process owns an existing Chromium lock."""
    for path in _lock_files(storage):_check_lock(path)


def _descendant(pid,ancestor):
    """Accept only the helper itself or a verifiable child process."""
    visited=set()
    while pid>1 and pid not in visited and len(visited)<64:
        if pid==ancestor:return True
        visited.add(pid)
        try:
            lines=Path(f'/proc/{pid}/status').read_text(encoding='ascii').splitlines()
            parent=next(line for line in lines if line.startswith('PPid:'))
            pid=int(parent.split(':',1)[1].strip())
        except (OSError,UnicodeError,StopIteration,ValueError):return False
    return False


def ensure_qt_profile_owned(storage,helper_pid):
    """During an access, reject any lock owned outside the Qt helper tree."""
    if type(helper_pid) is not int or helper_pid<=1 or sys.maxsize<2**32:
        raise QtProfileUnavailable('Le verrou Qt ne peut pas être vérifié.')
    class Flock(ctypes.Structure):
        _fields_=[('kind',ctypes.c_short),('whence',ctypes.c_short),('start',ctypes.c_longlong),
                  ('length',ctypes.c_longlong),('pid',ctypes.c_int)]
    for path in _lock_files(storage):
        try:fd=os.open(path,os.O_RDONLY|getattr(os,'O_CLOEXEC',0)|getattr(os,'O_NOFOLLOW',0))
        except FileNotFoundError:continue
        except OSError as error:raise QtProfileUnavailable('Le verrou Qt ne peut pas être vérifié.') from error
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):raise QtProfileUnavailable('Le verrou Qt ne peut pas être vérifié.')
            request=Flock(fcntl.F_RDLCK,os.SEEK_SET,0,0,0)
            try:locked=Flock.from_buffer_copy(fcntl.fcntl(fd,fcntl.F_GETLK,bytes(request)))
            except OSError as error:raise QtProfileUnavailable('Le verrou Qt ne peut pas être vérifié.') from error
            if locked.kind!=fcntl.F_UNLCK and not _descendant(locked.pid,helper_pid):
                raise QtProfileInUse('Une ancienne version Qt utilise ce stockage. Fermez-la puis réessayez.')
            # A flock lock cannot be attributed reliably through F_GETLK.
            try:fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
            except BlockingIOError as error:raise QtProfileUnavailable('Le verrou Qt ne peut pas être attribué.') from error
            except OSError as error:raise QtProfileUnavailable('Le verrou Qt ne peut pas être vérifié.') from error
            else:fcntl.flock(fd,fcntl.LOCK_UN)
        finally:os.close(fd)
