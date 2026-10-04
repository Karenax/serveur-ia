"""WireGuard key pairs and Windows protection for the server's private vault."""
import base64
import csv
import ctypes
from ctypes import wintypes
import io
import subprocess
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,PublicFormat,NoEncryption

def keypair():
    private=X25519PrivateKey.generate()
    return (base64.b64encode(private.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption())).decode(),
            base64.b64encode(private.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode())

class Blob(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]

def protect(raw,decrypt=False):
    buffer=ctypes.create_string_buffer(raw)
    source=Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));destination=Blob()
    dll=ctypes.WinDLL('crypt32',use_last_error=True)
    fn=dll.CryptUnprotectData if decrypt else dll.CryptProtectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    fn.restype=wintypes.BOOL
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(destination)):raise ctypes.WinError(ctypes.get_last_error())
    try:return ctypes.string_at(destination.data,destination.size)
    finally:
        free=ctypes.WinDLL('kernel32').LocalFree
        free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_void_p;free(destination.data)

def private_directory(path):
    path.mkdir(parents=True,exist_ok=True)
    result=subprocess.run(['whoami','/user','/fo','csv','/nh'],capture_output=True,text=True,creationflags=0x08000000,check=True)
    sid=next(csv.reader(io.StringIO(result.stdout)))[1]
    # New private directories: inheritance removed before any secret is written.
    result=subprocess.run(['icacls',str(path),'/inheritance:r','/grant:r',
                           f'*{sid}:(OI)(CI)F','*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F'],
                          capture_output=True,creationflags=0x08000000)
    if result.returncode:raise ValueError('Windows refuse de protéger le dossier des accès privés.')
