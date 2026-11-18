"""Cross-process ownership of one Windows desktop profile."""
import ctypes
from ctypes import wintypes
import hashlib
from pathlib import Path


class ProfileLockError(RuntimeError):
    pass


class ProfileAlreadyOpen(ProfileLockError):
    pass


class _Guard:
    def __init__(self, kernel, handle):
        self._kernel = kernel
        self._handle = handle

    def close(self):
        if self._handle:
            handle, self._handle = self._handle, None
            try:
                self._kernel.ReleaseMutex(handle)
            finally:
                self._kernel.CloseHandle(handle)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def _check_webview_closed(settings, kernel):
    """Detect an already-running older WebView2 using this profile, read-only."""
    path = Path(settings).parent/('webview-'+Path(settings).stem)/'EBWebView'/'lockfile'
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    # OPEN_EXISTING and exclusive sharing never create or modify the lockfile.
    handle = kernel.CreateFileW(str(path), 0x80000000, 0, None, 3, 0x00200080, None)
    if handle == ctypes.c_void_p(-1).value:
        error = ctypes.get_last_error()
        if error in (2, 3):  # A profile with no WebView data yet.
            return
        if error in (32, 33):
            raise ProfileAlreadyOpen('Kiara est déjà ouvert avec cet accès. Fermez la première fenêtre avant d’en ouvrir une autre.')
        raise ProfileLockError('Impossible de vérifier les données locales. Fermez les autres versions de Kiara puis réessayez.')
    kernel.CloseHandle(handle)


def lock_desktop_profile(settings):
    """Acquire a nonblocking named mutex before loading profile state.

    The owning thread must close the guard; Windows releases an abandoned mutex
    automatically if the process terminates. The name contains only a hash.
    """
    target = str(Path(settings).resolve()).casefold().encode('utf-8')
    name = 'Global\\KiaraProfile-' + hashlib.sha256(target).hexdigest()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel.ReleaseMutex.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateMutexW(None, False, name)
    if not handle:
        raise ProfileLockError('Impossible de protéger les données locales. Réessayez après avoir vérifié votre session Windows.')
    result = kernel.WaitForSingleObject(handle, 0)
    if result in (0, 0x80):
        guard = _Guard(kernel, handle)
        try:
            _check_webview_closed(settings, kernel)
        except BaseException:
            guard.close()
            raise
        return guard
    kernel.CloseHandle(handle)
    if result == 0x102:
        raise ProfileAlreadyOpen('Kiara est déjà ouvert avec cet accès. Fermez la première fenêtre avant d’en ouvrir une autre.')
    raise ProfileLockError('Impossible de protéger les données locales. Réessayez après avoir vérifié votre session Windows.')
