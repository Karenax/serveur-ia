"""Installer streaming stops when the authenticated access is revoked."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from gateway_desktop_downloads import handle
from kiara_shared.releases import DESKTOP_DOWNLOAD
from releases import DESKTOP_INSTALLER


class DesktopDownloadTests(TestCase):
    def test_revocation_between_chunks_stops_transfer(self):
        with TemporaryDirectory() as temporary:
            home = Path(temporary)
            folder = home / 'installateurs'
            folder.mkdir()
            first = b'a' * (256 * 1024)
            (folder / DESKTOP_INSTALLER).write_bytes(first + b'private tail')
            handler = SimpleNamespace(path=DESKTOP_DOWNLOAD, authorized=Mock(return_value=True),
                access_valid=Mock(side_effect=[True, False]), wfile=BytesIO(), send_response=Mock(),
                send_header=Mock(), end_headers=Mock(), respond=Mock())
            with patch('releases.windows_installer', return_value=({'bytes': len(first) + len(b'private tail')}, None)):
                handle(handler, SimpleNamespace(home=home))
            self.assertEqual(handler.wfile.getvalue(), first)
            self.assertEqual(handler.access_valid.call_count, 2)
            handler.send_response.assert_called_once_with(200)
