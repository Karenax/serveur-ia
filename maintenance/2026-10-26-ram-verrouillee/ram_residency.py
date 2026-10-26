"""Reject an unlocked Strata startup before the HTTP server accepts inference."""
import re
import os
from pathlib import Path


_embedding_lock = None


class LockedTensor:
    """Keep read-only GGUF pages shared with the engine physically resident."""
    def __init__(self, path, offset, size):
        import ctypes as c
        from ctypes import wintypes as w
        import numpy as np
        import psutil

        if size <= 0 or size > 2 * 2**30:
            raise ValueError('Taille inattendue de la table des tokens.')
        if psutil.virtual_memory().available < size + 6 * 2**30:
            raise ValueError('RAM insuffisante pour verrouiller la table des tokens.')
        self.key = (str(Path(path).resolve()), offset, size)
        self.mapping = np.memmap(path, dtype=np.uint8, mode='r', offset=offset, shape=(size,))
        address = self.mapping.ctypes.data
        self.base = address & ~4095
        self.length = (address + size - self.base + 4095) & ~4095
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        self.kernel.GetCurrentProcess.restype = w.HANDLE
        self.kernel.GetProcessWorkingSetSizeEx.argtypes = [w.HANDLE, c.POINTER(c.c_size_t), c.POINTER(c.c_size_t), c.POINTER(w.DWORD)]
        self.kernel.SetProcessWorkingSetSizeEx.argtypes = [w.HANDLE, c.c_size_t, c.c_size_t, w.DWORD]
        self.kernel.VirtualLock.argtypes = [c.c_void_p, c.c_size_t]
        self.kernel.VirtualUnlock.argtypes = [c.c_void_p, c.c_size_t]
        self.locked = False
        process = self.kernel.GetCurrentProcess()
        minimum, maximum, flags = c.c_size_t(), c.c_size_t(), w.DWORD()
        try:
            if not self.kernel.GetProcessWorkingSetSizeEx(process, c.byref(minimum), c.byref(maximum), c.byref(flags)):
                raise c.WinError(c.get_last_error())
            minimum = max(minimum.value, self.length + 128 * 2**20)
            if not self.kernel.SetProcessWorkingSetSizeEx(process, minimum, max(maximum.value, minimum + 128 * 2**20), 2 | 8):
                raise c.WinError(c.get_last_error())
            if not self.kernel.VirtualLock(self.base, self.length):
                raise c.WinError(c.get_last_error())
            self.locked = True
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.locked:
            self.kernel.VirtualUnlock(self.base, self.length)
            self.locked = False
        if self.mapping is not None:
            self.mapping._mmap.close()
            self.mapping = None


def lock_token_embeddings(args):
    # The native resident-experts flag does not cover the 322 MiB token table.
    # Keep its file pages locked in the HTTP server for its lifetime, including
    # engine restarts. No tensor copy or model-file change is necessary.
    global _embedding_lock
    if os.name != 'nt' or '--native' not in args:
        return 0
    from tools.gguf_reader import GGUFFile
    flag = '--embd-gguf' if '--embd-gguf' in args else '--native'
    path = args[args.index(flag) + 1]
    gguf = GGUFFile(path)
    tensor = next((t for t in gguf.tensors if t.name == 'token_embd.weight'), None)
    if tensor is None or tensor.expected_bytes() is None:
        raise ValueError('Table des tokens introuvable ; verrouillage RAM impossible.')
    size, offset = tensor.expected_bytes(), gguf.data_start + tensor.offset
    key = (str(Path(path).resolve()), offset, size)
    if _embedding_lock is not None and _embedding_lock.key != key:
        _embedding_lock.close()
        _embedding_lock = None
    if _embedding_lock is None:
        _embedding_lock = LockedTensor(path, offset, size)
    return size


def verify_locked_ram(log_path, offset, args):
    if '--resident-experts' not in args or '--no-prefill-borrow' not in args:
        raise ValueError('Le calcul exige les experts verrouillés en RAM, sans emprunt du cache GPU.')
    if '--ple-io' not in args:
        raise ValueError('Le mode de lecture de la table PLE doit être explicite.')
    ple_mode = args[args.index('--ple-io') + 1]
    if ple_mode == 'direct':
        if '--ple-gguf' not in args:
            raise ValueError('Le fichier PLE sur le SSD C: doit être explicite.')
        ple_path = Path(args[args.index('--ple-gguf') + 1]).resolve(strict=True)
        if ple_path.drive.upper() != 'C:':
            raise ValueError('La table PLE doit rester sur le SSD C:, hors du disque D:.')
    elif ple_mode != 'ram':
        raise ValueError('Mode PLE non pris en charge par la protection du disque D:.')
    # Inspect only this startup, never evidence from an earlier engine process.
    with open(log_path, 'rb') as stream:
        stream.seek(offset)
        text = stream.read().decode('utf-8', errors='replace')
    if ple_mode == 'ram' and 'PLE table locked in RAM (--ple-io ram)' not in text:
        raise ValueError('Le moteur ne confirme pas le verrouillage de la table PLE en RAM.')
    if re.search(r'resident RAM mode does not fit|CPU expert residency failed|RAM budget.*cannot be kept', text):
        raise ValueError('Les experts ne tiennent pas tous en mémoire ; le recours au disque est interdit.')
    matches = re.findall(r'FileExpertSource: .*?cache complement ready: resident ([\d.]+) GiB, '
                         r'pinned ([\d.]+) GiB[^\r\n]*', text)
    if not matches:
        raise ValueError('Le moteur ne confirme pas le chargement complet des experts en RAM.')
    resident, pinned = map(float, matches[-1])
    if resident <= 0:
        raise ValueError('La quantité de mémoire des experts est invalide.')
    line = [line for line in text.splitlines() if 'cache complement ready: resident' in line][-1]
    # GPU pinning and Windows VirtualLock are both resident. The latter reports
    # whole MiB, whereas the arena size is rounded to 0.01 GiB in the native log.
    locks = re.findall(r'locked (\d+) MiB via working-set minimum \+ VirtualLock', line)
    locked = int(locks[-1]) / 1024 if locks else 0
    if 'VirtualLock stopped' in line or pinned + locked < resident - .011:
        raise ValueError('Le verrouillage des experts est incomplet ; calcul sur disque refusé.')
    if not re.search(r'resident RAM mode: [\d.]+ GiB of experts .*\((?:page-locked|locked)\)', text):
        raise ValueError('Les experts restent paginables ; calcul sur disque refusé.')
    embeddings = lock_token_embeddings(args)
    if embeddings:
        with open(log_path, 'a', encoding='utf-8') as stream:
            stream.write(f'[kiara] token embeddings: {embeddings} bytes locked in shared RAM\n')
    return {'experts_gib': resident, 'pinned_gib': pinned, 'windows_locked_gib': locked,
            'ple_locked': ple_mode == 'ram', 'token_embeddings_locked_bytes': embeddings}
