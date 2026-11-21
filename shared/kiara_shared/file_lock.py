"""Reentrant, cross-process locking for a user's persistent files."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import threading
import time
from weakref import WeakValueDictionary

LOCK_TIMEOUT = 10

@contextmanager
def _windows_locked(path):
    name='Local\\FredFile-'+hashlib.sha256(str(Path(path).resolve()).casefold().encode()).hexdigest()
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
    kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.WaitForSingleObject.restype=wintypes.DWORD
    kernel.ReleaseMutex.argtypes=[wintypes.HANDLE]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateMutexW(None,False,name)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    acquired=False
    try:
        result=kernel.WaitForSingleObject(handle,LOCK_TIMEOUT * 1000)
        if result not in (0,0x80):raise OSError('Le fichier est occupé. Réessayer dans quelques secondes.')
        acquired=True
        yield
    finally:
        if acquired:kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


# flock is process-safe; the RLock and depth also make nested history reads safe
# and serialize threads in the same process, with the same timeout as Windows.
_registry_guard = threading.Lock()
_registry = WeakValueDictionary()


class _ThreadLock:
    def __init__(self):
        self.mutex = threading.RLock()
        self.state = threading.local()


@contextmanager
def locked(path):
    if os.name == 'nt':
        with _windows_locked(path):
            yield
        return
    import fcntl
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + LOCK_TIMEOUT
    identity = str(target)
    with _registry_guard:
        entry = _registry.get(identity)
        if entry is None:
            entry = _ThreadLock()
            _registry[identity] = entry
    mutex, state = entry.mutex, entry.state
    if not mutex.acquire(timeout=max(0, deadline - time.monotonic())):
        raise OSError('Le fichier est occupé. Réessayer dans quelques secondes.')
    try:
        if getattr(state, 'depth', 0):
            state.depth += 1
            try:
                yield
            finally:
                state.depth -= 1
            return
        descriptor = os.open(str(target)+'.lock', os.O_CREAT|os.O_RDWR, 0o600)
        try:
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX|fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise OSError('Le fichier est occupé. Réessayer dans quelques secondes.')
                    time.sleep(min(.05, remaining))
            state.depth = 1
            try:
                yield
            finally:
                state.depth = 0
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
    finally:
        mutex.release()
