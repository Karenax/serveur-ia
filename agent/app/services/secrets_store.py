"""User-scoped Windows DPAPI protection, without an extra credential service."""
import base64
import os


def _crypt(data: bytes, decrypt=False) -> bytes:
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), buffer)
    output = Blob()
    function = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise OSError("Le secret Windows ne peut pas être lu ou protégé pour cet utilisateur")
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree(output.data)


def protect(value: str) -> str:
    if not value or value.startswith("dpapi:"):
        return value
    if os.name != "nt":
        # On other hosts, keys come from the environment rather than plaintext SQL.
        raise ValueError("Utiliser PB_API_KEY sur un hôte non Windows")
    return "dpapi:" + base64.b64encode(_crypt(value.encode())).decode("ascii")


def reveal(value: str) -> str:
    if value.startswith("dpapi:"):
        return _crypt(base64.b64decode(value[6:]), decrypt=True).decode()
    return value
