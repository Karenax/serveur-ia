"""The package version must agree with the Linux Tauri executable."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from maintenance.package_linux_client import validate_linux_requirements, validate_tauri_binary


class LinuxPackageVersionTests(unittest.TestCase):
    def test_binary_version_and_architecture_are_required(self):
        with TemporaryDirectory() as temporary:
            binary = Path(temporary) / 'kiara'
            header = bytearray(20)
            header[:6] = b'\x7fELF\x02\x01'
            header[18:20] = (62).to_bytes(2, 'little')
            for payload in (b'', b'KIARA_TAURI_VERSION=0.1.0\0',
                            b'KIARA_TAURI_VERSION=4.0.10\0KIARA_TAURI_VERSION=4.0.10\0'):
                binary.write_bytes(header + payload)
                with self.assertRaises(ValueError):
                    validate_tauri_binary(binary, 'amd64', '4.0.10')
            binary.write_bytes(header + b'KIARA_TAURI_VERSION=4.0.10\0')
            self.assertEqual(binary, validate_tauri_binary(binary, 'amd64', '4.0.10'))
            with self.assertRaises(ValueError):
                validate_tauri_binary(binary, 'arm64', '4.0.10')

    def test_lock_must_match_direct_requirements(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'requirements.txt').write_text('demo==1.2.3\n', encoding='utf-8')
            lock = root/'requirements.lock'
            lock.write_text('demo==1.2.3 --hash=sha256:' + 'a'*64 + '\n', encoding='utf-8')
            validate_linux_requirements(root)
            for invalid in ('demo==1.2.4 --hash=sha256:'+'a'*64+'\n', 'demo==1.2.3\n', ''):
                lock.write_text(invalid, encoding='utf-8')
                with self.assertRaises(ValueError):
                    validate_linux_requirements(root)


if __name__ == '__main__':
    unittest.main()
