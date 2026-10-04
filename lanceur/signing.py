"""Ed25519 release signing; private seed is protected by Windows DPAPI."""
import base64
import json
import threading
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,PublicFormat,NoEncryption
from core import HOME
from wg_crypto import protect,private_directory
lock=threading.RLock()

def private(home=HOME,create=True):
    import sys
    from core import ROOT
    sys.path.insert(0,str(ROOT/'client-qwen'))
    from file_lock import locked
    from history_store import atomic
    directory=home/'wireguard-prive';path=directory/'signature.dpapi'
    with lock,locked(path):
        if path.exists():return Ed25519PrivateKey.from_private_bytes(protect(path.read_bytes(),decrypt=True))
        if not create:raise ValueError('Clé de signature serveur absente.')
        private_directory(directory)
        key=Ed25519PrivateKey.generate()
        atomic(path,protect(key.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption())))
        return key

def public(home=HOME,create=True):return base64.b64encode(private(home,create).public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode()

def canonical(value):
    return json.dumps({k:value[k] for k in ('version','protocol','sha256','bytes')},sort_keys=True,separators=(',',':')).encode()

def sign(value, home=HOME):
    return {**value,'signature':base64.b64encode(private(home).sign(canonical(value))).decode(),'signing_public_key':public(home)}

def verify(value, pinned):
    Ed25519PublicKey.from_public_bytes(base64.b64decode(pinned,validate=True)).verify(base64.b64decode(value['signature'],validate=True),canonical(value))
