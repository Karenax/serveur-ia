"""Explicit export/verification of portable signing keys, separate from server restores.

No function creates a signing key. The CLI receives a private recovery-phrase
file and prints only certificate/public-key fingerprints and encrypted paths.
"""
from __future__ import annotations
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile

from cryptography.fernet import InvalidToken
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, ec
from cryptography.hazmat.primitives.serialization import pkcs12
from core import ROOT
from operations import cipher
from wg_crypto import protect, private_directory

HEADER = b'FREDSIGNKEY1'
MAX_ARCHIVE = 12 * 1024 * 1024
MAX_KEYSTORE = 4 * 1024 * 1024
MAX_SECRET = 128 * 1024
ALIAS = 'fred-client'


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _read(path, limit, message):
    path = Path(path)
    with path.open('rb') as stream:
        if os.fstat(stream.fileno()).st_size > limit: raise ValueError(message)
        raw = stream.read(limit + 1)
    if len(raw) > limit or not raw: raise ValueError(message)
    return raw


def recovery_phrase(path):
    try: phrase = _read(path, 8192, 'Fichier de phrase de récupération invalide.').decode('utf-8-sig').rstrip('\r\n')
    except (OSError, UnicodeError): raise ValueError('Fichier privé de phrase de récupération illisible.') from None
    # Validate through the same portable PBKDF2/Fernet contract as server archives.
    cipher(phrase, b'\x00' * 16)
    return phrase


def android_password(path):
    """PowerShell ConvertFrom-SecureString uses hex DPAPI-protected UTF-16LE."""
    try:
        encoded = _read(path, MAX_SECRET, 'Secret Android invalide.').decode('ascii').strip()
        raw = bytes.fromhex(encoded)
        password = protect(raw, decrypt=True).decode('utf-16-le')
    except (OSError, UnicodeError, ValueError):
        raise ValueError('Le secret de signature Android ne peut pas être ouvert par ce compte Windows.') from None
    if not 1 <= len(password) <= 4096 or '\x00' in password:
        raise ValueError('Mot de passe de signature Android invalide.')
    return password


def _manifest(package):
    parts = {'android.keystore': base64.b64decode(package['android']['keystore'], validate=True),
             'android.password': package['android']['password'].encode('utf-8')}
    if package.get('windows') is not None:
        parts['windows.seed'] = base64.b64decode(package['windows']['seed'], validate=True)
    return {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in sorted(parts.items())}


def _validate(package):
    if (not isinstance(package, dict) or set(package) != {'version', 'kind', 'created_at', 'android', 'windows', 'manifest'}
        or package.get('version') != 1 or package.get('kind') != 'fred-signing-recovery'
        or not isinstance(package.get('created_at'), str)):
        raise ValueError('Contenu de récupération de signatures invalide.')
    android = package.get('android')
    if not isinstance(android, dict) or set(android) != {'keystore', 'password', 'alias'} or android['alias'] != ALIAS:
        raise ValueError('Clé Android sauvegardée invalide.')
    password = android['password']
    if not isinstance(password, str) or not 1 <= len(password) <= 4096 or '\x00' in password:
        raise ValueError('Secret Android sauvegardé invalide.')
    try: raw = base64.b64decode(android['keystore'], validate=True)
    except (ValueError, TypeError): raise ValueError('Clé Android encodée invalide.') from None
    if not 1 <= len(raw) <= MAX_KEYSTORE: raise ValueError('Clé Android trop volumineuse ou vide.')
    try: loaded = pkcs12.load_pkcs12(raw, password.encode('utf-8'))
    except (ValueError, TypeError): raise ValueError('La clé PKCS12 et son secret Android ne correspondent pas.') from None
    if (not isinstance(loaded.key, (rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey)) or loaded.cert is None
        or loaded.cert.friendly_name != ALIAS.encode()):
        raise ValueError('Alias ou paire de signature Android invalide.')
    public_key = loaded.key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    certificate_key = loaded.cert.certificate.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    if public_key != certificate_key: raise ValueError('Certificat et clé Android incompatibles.')
    windows = package.get('windows')
    public_windows = ''
    if windows is not None:
        if not isinstance(windows, dict) or set(windows) != {'seed'}: raise ValueError('Clé Windows sauvegardée invalide.')
        try:
            seed = base64.b64decode(windows['seed'], validate=True)
            if len(seed) != 32: raise ValueError('seed')
            key = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
            public_windows = base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
        except (ValueError, TypeError): raise ValueError('Clé Windows sauvegardée invalide.') from None
    if package['manifest'] != _manifest(package): raise ValueError('Manifeste de récupération endommagé.')
    return {'version': 1, 'verified': True, 'created_at': package['created_at'], 'android_alias': ALIAS,
            'android_keystore_bytes': len(raw),
            'android_certificate_sha256': loaded.cert.certificate.fingerprint(hashes.SHA256()).hex(),
            'windows_included': windows is not None, 'windows_public_key': public_windows,
            'server_restore_compatible': False}


def decode(blob, phrase):
    """Internal recovery API: secret-bearing package must never be printed or catalogued."""
    if len(blob) > MAX_ARCHIVE or not blob.startswith(HEADER) or len(blob) <= len(HEADER) + 16:
        raise ValueError('Format de récupération de signatures invalide ou trop volumineux.')
    position = len(HEADER)
    try: package = json.loads(cipher(phrase, blob[position:position + 16]).decrypt(blob[position + 16:]))
    except (InvalidToken, ValueError, UnicodeError, TypeError):
        raise ValueError('Archive de signatures invalide ou phrase incorrecte.') from None
    summary = _validate(package)
    return package, summary


def verify_archive(file, phrase):
    blob = _read(file, MAX_ARCHIVE, 'Archive de signatures trop volumineuse ou vide.')
    _, summary = decode(blob, phrase)
    return {**summary, 'file': str(Path(file).resolve()), 'size': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}


def export_archive(android_directory, target, phrase, windows_home=None):
    """Export existing keys only, with a verified atomic publication and no overwrite."""
    directory = Path(android_directory)
    keystore = _read(directory / 'fred-client.p12', MAX_KEYSTORE, 'Clé Android trop volumineuse ou vide.')
    password = android_password(directory / 'password.dpapi')
    package = {'version': 1, 'kind': 'fred-signing-recovery',
               'created_at': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
               'android': {'keystore': base64.b64encode(keystore).decode(), 'password': password, 'alias': ALIAS},
               'windows': None, 'manifest': {}}
    if windows_home is not None:
        path = Path(windows_home) / 'wireguard-prive' / 'signature.dpapi'
        try: seed = protect(_read(path, MAX_SECRET, 'Clé Windows invalide.'), decrypt=True)
        except OSError: raise ValueError('Clé de signature Windows absente ou inaccessible à ce compte.') from None
        if len(seed) != 32: raise ValueError('Clé de signature Windows invalide.')
        package['windows'] = {'seed': base64.b64encode(seed).decode()}
    package['manifest'] = _manifest(package)
    _validate(package)
    salt = secrets.token_bytes(16)
    blob = HEADER + salt + cipher(phrase, salt).encrypt(_canonical(package))
    if len(blob) > MAX_ARCHIVE: raise ValueError('Archive de récupération trop volumineuse.')
    target = Path(target)
    if not target.is_absolute() or target.suffix.lower() != '.fredkeys':
        raise ValueError('Choisir un chemin absolu avec l’extension .fredkeys.')
    if target.exists(): raise ValueError('Le paquet de récupération existe déjà ; choisir un nouveau nom.')
    private_directory(target.parent)
    descriptor, temporary = tempfile.mkstemp(prefix='signature-', suffix='.tmp', dir=target.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(blob); stream.flush(); os.fsync(stream.fileno())
        prepared = _read(temporary, MAX_ARCHIVE, 'Archive de récupération invalide.')
        if prepared != blob: raise ValueError('Archive modifiée pendant la vérification.')
        _, summary = decode(prepared, phrase)
        # On Windows rename refuses an existing destination, including a concurrent publication.
        if os.name == 'nt': os.rename(temporary, target)
        else:
            os.link(temporary, target); os.unlink(temporary)
        return {**summary, 'file': str(target.resolve()), 'size': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}
    finally: Path(temporary).unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Récupération chiffrée des clés de signature Android et Windows ; aucun secret affiché.')
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    export.add_argument('--android-dir', type=Path, default=ROOT / 'toolchain' / 'android-signing')
    export.add_argument('--windows-home', type=Path, default=None)
    export.add_argument('--output', type=Path, required=True)
    export.add_argument('--phrase-file', type=Path, required=True)
    verify = commands.add_parser('verify')
    verify.add_argument('--file', type=Path, required=True)
    verify.add_argument('--phrase-file', type=Path, required=True)
    values = parser.parse_args(argv)
    try:
        phrase = recovery_phrase(values.phrase_file)
        result = export_archive(values.android_dir, values.output, phrase, values.windows_home) if values.command == 'export' else verify_archive(values.file, phrase)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception:
        # A library/OS exception may contain key material: only this fixed message reaches the CLI.
        print(json.dumps({'error': 'Opération de récupération de signatures refusée. Vérifier le fichier de phrase, les droits Windows, les clés existantes et le nom de destination.'}, ensure_ascii=False))
        return 1


if __name__ == '__main__': raise SystemExit(main())
