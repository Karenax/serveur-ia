"""Cross-process Windows mutex for one user's persistent file."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path

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
        result=kernel.WaitForSingleObject(handle,10000)
        if result not in (0,0x80):raise OSError('Le fichier est occupé. Réessayer dans quelques secondes.')
        acquired=True
        yield
    finally:
        if acquired:kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


# flock is process-safe; the RLock and depth also make nested history reads safe
# and serialize threads in the same process, with the same timeout as Windows.
import threading
import time
_registry_guard = threading.Lock()
_registry = {}


@contextmanager
def locked(path):
    if os.name == 'nt':
        with _windows_locked(path):
            yield
        return
    import fcntl
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with _registry_guard:
        mutex, state = _registry.setdefault(str(target), (threading.RLock(), threading.local()))
    if not mutex.acquire(timeout=10):
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
            deadline = time.monotonic()+10
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX|fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise OSError('Le fichier est occupé. Réessayer dans quelques secondes.')
                    time.sleep(.05)
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
