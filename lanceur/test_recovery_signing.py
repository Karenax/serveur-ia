"""Synthetic keys only: portable signing export, real DPAPI, corruption and CLI."""
import base64
import datetime as dt
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
import recovery_signing as recovery
from core import PYTHON
from wg_crypto import protect, private_directory

PHRASE = 'phrase de récupération uniquement pour tests de signature'
ANDROID_PASSWORD = 'Android signing fixture password 2026 only'


class SigningRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fred-signing-recovery-')
        self.home = Path(self.tmp.name)
        self.android = self.home / 'android'; private_directory(self.android)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Isolated signing fixture')])
        now = dt.datetime.now(dt.timezone.utc)
        self.certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=30))
            .sign(key, hashes.SHA256()))
        self.keystore = pkcs12.serialize_key_and_certificates(b'fred-client', key, self.certificate, None,
                                                            serialization.BestAvailableEncryption(ANDROID_PASSWORD.encode()))
        (self.android / 'fred-client.p12').write_bytes(self.keystore)
        (self.android / 'password.dpapi').write_text(protect(ANDROID_PASSWORD.encode('utf-16-le')).hex(), encoding='ascii')
        self.windows = self.home / 'server'; private_directory(self.windows / 'wireguard-prive')
        self.seed = ed25519.Ed25519PrivateKey.generate().private_bytes(serialization.Encoding.Raw,
                   serialization.PrivateFormat.Raw, serialization.NoEncryption())
        (self.windows / 'wireguard-prive' / 'signature.dpapi').write_bytes(protect(self.seed))
        self.output = self.home / 'recovery' / 'signatures.fredkeys'
        self.phrase_file = self.home / 'phrase.txt'; self.phrase_file.write_text(PHRASE, encoding='utf-8')

    def tearDown(self): self.tmp.cleanup()

    def export(self, windows=True):
        return recovery.export_archive(self.android, self.output, PHRASE, self.windows if windows else None)

    def test_roundtrip_portable_keystore_password_and_optional_windows_seed(self):
        summary = self.export()
        blob = self.output.read_bytes()
        package, verified = recovery.decode(blob, PHRASE)
        self.assertEqual(base64.b64decode(package['android']['keystore']), self.keystore)
        self.assertEqual(package['android']['password'], ANDROID_PASSWORD)
        self.assertEqual(base64.b64decode(package['windows']['seed']), self.seed)
        self.assertEqual(summary['android_certificate_sha256'], self.certificate.fingerprint(hashes.SHA256()).hex())
        self.assertTrue(verified['windows_included']); self.assertFalse(verified['server_restore_compatible'])
        for secret in (PHRASE, ANDROID_PASSWORD, base64.b64encode(self.seed).decode(), base64.b64encode(self.keystore).decode()):
            self.assertNotIn(secret.encode(), blob)
            self.assertNotIn(secret, json.dumps(summary))
        self.assertFalse(blob.startswith(b'FREDBACKUP2')); self.assertFalse(blob.startswith(b'QWENBACKUP1'))

    def test_android_only_export_does_not_need_a_windows_signing_key(self):
        summary = self.export(windows=False)
        package, _ = recovery.decode(self.output.read_bytes(), PHRASE)
        self.assertIsNone(package['windows']); self.assertFalse(summary['windows_included'])

    def test_bad_phrase_and_bit_corruption_are_refused(self):
        self.export()
        with self.assertRaisesRegex(ValueError, 'phrase incorrecte'):
            recovery.verify_archive(self.output, 'wrong test phrase sufficiently long')
        blob = bytearray(self.output.read_bytes()); blob[-8] ^= 1; self.output.write_bytes(blob)
        with self.assertRaisesRegex(ValueError, 'phrase incorrecte'): recovery.verify_archive(self.output, PHRASE)

    def test_authenticated_manifest_corruption_is_refused(self):
        self.export()
        blob = self.output.read_bytes(); position = len(recovery.HEADER)
        key = recovery.cipher(PHRASE, blob[position:position + 16])
        package = json.loads(key.decrypt(blob[position + 16:])); package['manifest']['android.keystore']['sha256'] = '0' * 64
        self.output.write_bytes(blob[:position + 16] + key.encrypt(recovery._canonical(package)))
        with self.assertRaisesRegex(ValueError, 'Manifeste'): recovery.verify_archive(self.output, PHRASE)

    def test_missing_key_is_not_created_and_existing_archive_is_not_replaced(self):
        self.export(); original = self.output.read_bytes()
        with self.assertRaisesRegex(ValueError, 'existe déjà'): self.export()
        self.assertEqual(self.output.read_bytes(), original)
        (self.android / 'fred-client.p12').unlink()
        with self.assertRaises(OSError): recovery.export_archive(self.android, self.home / 'missing.fredkeys', PHRASE)
        self.assertFalse((self.android / 'fred-client.p12').exists())

    def test_android_password_mismatch_is_refused_without_publication(self):
        (self.android / 'password.dpapi').write_text(protect(b'different password'.decode().encode('utf-16-le')).hex(), encoding='ascii')
        with self.assertRaisesRegex(ValueError, 'ne correspondent pas'): self.export()
        self.assertFalse(self.output.exists())

    def test_archive_and_secret_input_bounds_are_enforced(self):
        self.output.parent.mkdir(parents=True)
        with self.output.open('wb') as stream:
            stream.truncate(recovery.MAX_ARCHIVE + 1)
        with self.assertRaisesRegex(ValueError, 'volumineuse'): recovery.verify_archive(self.output, PHRASE)
        (self.android / 'password.dpapi').write_bytes(b'a' * (recovery.MAX_SECRET + 1))
        with self.assertRaises(ValueError): recovery.android_password(self.android / 'password.dpapi')
        self.phrase_file.write_bytes(b'x' * 8193)
        with self.assertRaises(ValueError): recovery.recovery_phrase(self.phrase_file)

    def test_atomic_publication_failure_keeps_sources_and_has_no_temporary_file(self):
        with patch('recovery_signing.os.rename', side_effect=PermissionError('secret fixture error text')):
            with self.assertRaises(PermissionError): self.export()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.glob('*.tmp')), [])
        self.assertEqual((self.android / 'fred-client.p12').read_bytes(), self.keystore)

    def test_cli_export_verify_output_contains_no_password_or_private_seed(self):
        code = Path(recovery.__file__)
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        command = [str(PYTHON), str(code), 'export', '--phrase-file', str(self.phrase_file),
                   '--output', str(self.output), '--android-dir', str(self.android), '--windows-home', str(self.windows)]
        result = subprocess.run(command, capture_output=True, env=env, creationflags=0x08000000)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        summary = json.loads(result.stdout)
        self.assertTrue(summary['verified'])
        verified = subprocess.run([str(PYTHON), str(code), 'verify', '--phrase-file', str(self.phrase_file), '--file', str(self.output)],
                                  capture_output=True, env=env, creationflags=0x08000000)
        self.assertEqual(verified.returncode, 0, verified.stderr.decode())
        for secret in (ANDROID_PASSWORD, PHRASE, base64.b64encode(self.seed).decode()):
            self.assertNotIn(secret.encode(), result.stdout + result.stderr + verified.stdout + verified.stderr)

    def test_cli_failure_masks_even_library_exception_secret(self):
        captured = io.StringIO()
        with redirect_stdout(captured), patch('recovery_signing.export_archive', side_effect=OSError('sensitive-secret-test-value')):
            status = recovery.main(['export', '--phrase-file', str(self.phrase_file), '--output', str(self.output), '--android-dir', str(self.android)])
        self.assertEqual(status, 1); self.assertNotIn('sensitive-secret', captured.getvalue())
        self.assertNotIn(ANDROID_PASSWORD, captured.getvalue()); self.assertIn('error', json.loads(captured.getvalue()))

    def test_actual_powershell_securestring_file_uses_supported_dpapi_format(self):
        target = self.android / 'powershell-password.dpapi'
        # The fixture password travels over stdin, never in the process arguments.
        script = "$ErrorActionPreference='Stop'; $p='PowerShell synthetic password '+[char]233+'t'+[char]233+' 2026'; $s=ConvertTo-SecureString $p -AsPlainText -Force; [IO.File]::WriteAllText($env:FRED_FIXTURE_PASSWORD_FILE,(ConvertFrom-SecureString $s),[Text.Encoding]::ASCII)\r\n"
        env = dict(os.environ, FRED_FIXTURE_PASSWORD_FILE=str(target))
        env['PSModulePath'] = str(Path(os.environ['SystemRoot']) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'Modules')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', '-'],
                                input=script.encode('ascii'), capture_output=True, env=env, creationflags=0x08000000)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assertEqual(recovery.android_password(target), 'PowerShell synthetic password été 2026')


if __name__ == '__main__': unittest.main(verbosity=2)
