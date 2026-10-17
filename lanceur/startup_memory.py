"""Reclaim a cold loader's temporary working set without stopping inference."""
import ctypes
import os
from pathlib import Path

import psutil


def _empty_working_set(pid):
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    api = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    api.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
    api.EmptyWorkingSet.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x0100 | 0x0400, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not api.EmptyWorkingSet(handle):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)


def reclaim_loader(cfg, server_identity):
    """Only the configured engine owned by this live server is eligible.

    Windows virtualenv Python may insert a redirector before the actual server.

    The caller limits this to one attempt during a low-memory cold startup.
    Allocations and mappings stay valid; the normal RAM guard remains active.
    """
    if os.name != 'nt' or '--resident-cpu-experts' not in cfg.get('args', []):
        return {'status': 'skipped'}
    try:
        server = psutil.Process(server_identity['pid'])
        if abs(server.create_time() - server_identity['created']) >= .01:
            return {'status': 'skipped', 'reason': 'server_identity_changed'}
        expected = Path(cfg['exe']).resolve()
        def owned(process):
            if process.ppid() == server.pid:
                return True
            return any(parent.pid == server.pid and
                       abs(parent.create_time() - server_identity['created']) < .01
                       for parent in process.parents())
        for child in server.children(recursive=True):
            if Path(child.exe()).resolve() != expected:
                continue
            created = child.create_time()
            if not owned(child) or created < server.create_time():
                continue
            # Recheck immediately before requesting a handle for this PID.
            current = psutil.Process(child.pid)
            if abs(current.create_time() - created) >= .01 or not owned(current):
                continue
            _empty_working_set(child.pid)
            return {'status': 'reclaimed', 'pid': child.pid, 'method': 'EmptyWorkingSet'}
        return {'status': 'skipped', 'reason': 'owned_engine_not_found'}
    except (OSError, psutil.Error) as error:
        return {'status': 'failed', 'error': str(error)}
