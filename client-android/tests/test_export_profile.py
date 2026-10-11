"""Synthetic profile tests: no live account, server, key vault or peer is opened."""
import base64
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'Export-Profile.py'
spec = importlib.util.spec_from_file_location('fred_android_profile_export', SCRIPT)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


def fixture():
    key = base64.b64encode(bytes(range(32))).decode('ascii')
    return {'transport': 'wireguard', 'url': 'wireguard://10.77.0.1:8766',
            'protocol': 3, 'version': '3.5.16', 'client_name': 'Téléphone de test',
            'token': 'qwen_' + '1234567890abcdef' + '_' + 'A' * 43,
            'local_routes': [{'endpoint': '192.168.1.40:51820', 'network': '192.168.1.0/24'}],
            'wireguard': {'private_key': key, 'server_public_key': key,
                          'preshared_key': key, 'address': '10.77.0.2/32',
                          'endpoint': 'vpn.example.org:51820'}}


def pack(profile):
    raw = json.dumps(profile, ensure_ascii=False).encode('utf-8')
    return b'MZ synthetic non-executable fixture\x00' + raw + struct.pack('<I', len(raw)) + exporter.FOOTER_MAGIC


class ExportProfileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        self.source = self.folder / 'personal.exe'
        self.profile = fixture()
        self.source.write_bytes(pack(self.profile))

    def tearDown(self):
        self.temporary.cleanup()

    def test_profile_and_source_are_preserved_and_permissions_precede_write(self):
        original = self.source.read_bytes()
        protection_calls = []
        def protect(directory):
            self.assertEqual(list(directory.iterdir()), [])
            protection_calls.append(directory)
        target = exporter.export_profile(self.source, self.folder / 'new-private', protect_directory=protect)
        self.assertEqual(json.loads(target.read_text(encoding='utf-8')), self.profile)
        self.assertEqual(target.name, 'profil.fred-android')
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(protection_calls, [target.parent])

    def test_existing_directory_is_never_used_or_overwritten(self):
        directory = self.folder / 'existing'
        directory.mkdir()
        marker = directory / 'profil.fred-android'
        marker.write_bytes(b'original')
        with self.assertRaises(exporter.ProfileError):
            exporter.export_profile(self.source, directory, protect_directory=lambda _directory: None)
        self.assertEqual(marker.read_bytes(), b'original')

    def test_acl_failure_leaves_no_plaintext_file(self):
        directory = self.folder / 'denied'
        def denied(_directory):
            raise PermissionError('synthetic ACL failure')
        with self.assertRaises(PermissionError):
            exporter.export_profile(self.source, directory, protect_directory=denied)
        self.assertFalse(directory.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows ACL integration')
    def test_windows_export_acl_limits_access_to_user_system_and_administrators(self):
        target = exporter.export_profile(self.source, self.folder / 'windows-private')
        environment = {**os.environ, 'FRED_ACL_TEST_ROOT': str(target.parent)}
        command = (
            '$acl = [System.IO.Directory]::GetAccessControl($env:FRED_ACL_TEST_ROOT); '
            '$current = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value; '
            '$entries = @($acl.Access | ForEach-Object { '
            '$_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value }); '
            "$unexpected = @($entries | Where-Object { $_ -notin @($current, 'S-1-5-18', 'S-1-5-32-544') }); "
            'if ($acl.AreAccessRulesProtected -and $unexpected.Count -eq 0) { exit 0 } else { exit 1 }'
        )
        checked = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                                 env=environment, capture_output=True, timeout=15,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(checked.returncode, 0, 'The private export directory ACL is not restricted. ' + checked.stderr.decode(errors='replace'))
        self.assertEqual(json.loads(target.read_text(encoding='utf-8')), self.profile)

    def test_invalid_profile_is_rejected_before_output_directory(self):
        for change in ({'token': 'CREDENTIAL_MUST_NOT_APPEAR_IN_ERRORS'}, {'transport': 'https'},
                       {'protocol': True}, {'protocol': 5}, {'wireguard': {}},
                       {'url': 'http://127.0.0.1:8766'}):
            with self.subTest(change=list(change)):
                self.source.write_bytes(pack({**self.profile, **change}))
                output = self.folder / 'invalid-export'
                with self.assertRaises(exporter.ProfileError) as error:
                    exporter.export_profile(self.source, output)
                self.assertFalse(output.exists())
                self.assertNotIn('CREDENTIAL_MUST_NOT_APPEAR_IN_ERRORS', str(error.exception))

    def test_footer_and_size_errors_are_bounded(self):
        malformed = (b'', b'MZ short', b'MZ' + bytes(16),
                     b'MZ' + struct.pack('<I', 0) + exporter.FOOTER_MAGIC,
                     b'MZ' + struct.pack('<I', 65537) + exporter.FOOTER_MAGIC,
                     b'MZ' + struct.pack('<I', 1000) + exporter.FOOTER_MAGIC)
        for data in malformed:
            with self.subTest(length=len(data)):
                self.source.write_bytes(data)
                with self.assertRaises(exporter.ProfileError):
                    exporter.read_exe_profile(self.source)

    def test_invalid_json_utf8_duplicate_fields_and_constants_are_rejected(self):
        for raw in (b'[]', b'{"token":"NEVER_PRINT_THIS_SECRET",}', b'\xff',
                    b'{"token":"a","token":"b"}', b'{"token":NaN}', b'[' * 1500):
            with self.subTest(size=len(raw)):
                self.source.write_bytes(b'MZ' + raw + struct.pack('<I', len(raw)) + exporter.FOOTER_MAGIC)
                with self.assertRaises(exporter.ProfileError) as error:
                    exporter.read_exe_profile(self.source)
                self.assertNotIn('NEVER_PRINT_THIS_SECRET', str(error.exception))

    def test_cli_failure_never_logs_input_credentials(self):
        self.source.write_bytes(pack({**self.profile, 'token': 'DO_NOT_LOG_THIS_CREDENTIAL'}))
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = exporter.main(['--exe', str(self.source), '--output-directory', str(self.folder / 'output')])
        self.assertEqual(result, 1)
        self.assertNotIn('DO_NOT_LOG_THIS_CREDENTIAL', stdout.getvalue() + stderr.getvalue())
        self.assertEqual(stdout.getvalue(), '')

    def test_all_supported_protocol_versions_export(self):
        for protocol in (1, 2, 3, 4):
            self.source.write_bytes(pack({**self.profile, 'protocol': protocol}))
            self.assertEqual(exporter.read_exe_profile(self.source)['protocol'], protocol)


if __name__ == '__main__':
    unittest.main()
