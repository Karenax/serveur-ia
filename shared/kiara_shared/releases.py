"""Shared signed release validation and public client filenames."""
import base64
import json
import re
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

def client_filename(number,name):
    version(number)
    label=re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]','-',str(name)).strip(' .')[:80] or 'Client'
    return f'Accès serveur Fred {number} - {label}.exe'

def verify(release, pinned):
    if not isinstance(release,dict) or type(release.get('bytes')) is not int or not 1<=release['bytes']<=256*1024*1024:
        raise ValueError('Taille de mise à jour invalide.')
    if type(release.get('protocol')) is not int or release['protocol'] not in (3,4):raise ValueError('Version incompatible.')
    version(release.get('version'))
    if not isinstance(release.get('sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',release['sha256']):raise ValueError('Empreinte de mise à jour invalide.')
    canonical=json.dumps({k:release[k] for k in ('version','protocol','sha256','bytes')},sort_keys=True,separators=(',',':')).encode()
    try:Ed25519PublicKey.from_public_bytes(base64.b64decode(pinned,validate=True)).verify(base64.b64decode(release['signature'],validate=True),canonical)
    except Exception as error:raise ValueError('Signature de mise à jour invalide.') from error
    return release

def version(value):
    try:
        if not isinstance(value,str) or not re.fullmatch(r'(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})',value):raise ValueError()
        parts=value.split('.')
        return tuple(int(x) for x in parts)
    except (ValueError,AttributeError):raise ValueError('Numéro de version invalide.')
