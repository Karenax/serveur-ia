"""Cross-process Windows mutex for one user's persistent file."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
from pathlib import Path

@contextmanager
def locked(path):
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
