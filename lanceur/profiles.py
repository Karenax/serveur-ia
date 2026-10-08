"""Check device tokens and WireGuard identities before distributing/restoring EXEs."""
import base64
import hashlib
import hmac
import ipaddress
import math
import re
import sys
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from core import ROOT
sys.path.insert(0,str(ROOT/'client-qwen'))
from wg_bridge import validate_profile

def public_key(private):
    raw=base64.b64decode(private,validate=True)
    key=X25519PrivateKey.from_private_bytes(raw).public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    return base64.b64encode(key).decode()

def validate_access(data):
    if not isinstance(data,dict) or type(data.get('enabled')) is not bool or not isinstance(data.get('clients'),list) or len(data['clients'])>100:
        raise ValueError('Registre des accès invalide.')
    from remote import secure_url
    secure_url(data.get('url',''))
    deleted=data.get('deleted_clients',[])
    if not isinstance(deleted,list) or len(deleted)>10000 or any(not isinstance(c,dict) or c.get('revoked') is not True for c in deleted):
        raise ValueError('Archive des clients supprimés invalide.')
    deleted_ids={c.get('id') for c in deleted if isinstance(c.get('id'),str)}
    ids=set();addresses=set()
    for record in data['clients']+deleted:
        identity=record.get('id') if isinstance(record,dict) else None
        if not isinstance(identity,str) or not re.fullmatch(r'[0-9a-f]{16}',identity) or identity in ids:
            raise ValueError('Identifiant client invalide ou dupliqué.')
        ids.add(identity)
        if type(record.get('revoked')) is not bool or not isinstance(record.get('hash'),str) or not re.fullmatch(r'[0-9a-f]{64}',record['hash']):
            raise ValueError('Empreinte ou révocation client invalide.')
        if type(record.get('suspended',False)) is not bool:
            raise ValueError('Politique client invalide.')
        expiry=record.get('expires_epoch')
        if expiry is not None and (type(expiry) not in (int,float) or not math.isfinite(expiry) or expiry<=0):raise ValueError('Expiration client invalide.')
        if 'address' in record:
            address=ipaddress.ip_interface(record['address'])
            if address.network.prefixlen!=32 or address.ip not in ipaddress.ip_network('10.77.0.0/24') or int(str(address.ip).split('.')[-1]) not in range(2,255):raise ValueError('Adresse client invalide.')
            if len(base64.b64decode(record.get('wireguard_public_key',''),validate=True))!=32:raise ValueError('Clé publique client invalide.')
            if identity not in deleted_ids:
                if record['address'] in addresses:raise ValueError('Adresse WireGuard client dupliquée.')
                addresses.add(record['address'])
    return data

def match(record,profile,server_key=None,psk=None):
    validate_profile(profile)
    identity=record.get('id','')
    if not re.fullmatch(r'[0-9a-f]{16}',identity) or profile['token'].split('_')[1]!=identity:
        raise ValueError('Le profil ne correspond pas au destinataire.')
    if not hmac.compare_digest(hashlib.sha256(profile['token'].encode()).hexdigest(),record.get('hash','')):
        raise ValueError('La clé d’accès du profil ne correspond pas au registre serveur.')
    wg=profile['wireguard']
    if wg['address']!=record.get('address') or public_key(wg['private_key'])!=record.get('wireguard_public_key'):
        raise ValueError('L’identité WireGuard du profil ne correspond pas au client.')
    if server_key is not None and wg['server_public_key']!=server_key:
        raise ValueError('Le profil utilise une autre clé serveur WireGuard.')
    if psk is not None and not hmac.compare_digest(wg['preshared_key'],psk):
        raise ValueError('La clé partagée du profil ne correspond pas au tunnel serveur.')
    return profile
