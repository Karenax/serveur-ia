"""Windows firewall identity survives PyInstaller's changing extraction path."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'client-qwen'))
from wg_bridge import bridge_executable

class StableBridgeTests(unittest.TestCase):
    def test_two_extractions_reuse_verified_binary_and_repair_corruption(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            first=root/'_MEI1'; second=root/'_MEI2'
            for folder in (first,second):
                folder.mkdir();(folder/'wireguard-bridge.exe').write_bytes(b'bridge-test')
            with patch.dict(os.environ,LOCALAPPDATA=str(root/'local')),patch.object(sys,'frozen',True,create=True):
                with patch.object(sys,'_MEIPASS',str(first),create=True):target=bridge_executable()
                before=target.stat().st_mtime_ns
                with patch.object(sys,'_MEIPASS',str(second),create=True):
                    self.assertEqual(bridge_executable(),target)
                    self.assertEqual(target.stat().st_mtime_ns,before)
                    target.write_bytes(b'corrupt')
                    self.assertEqual(bridge_executable(),target)
                    self.assertEqual(target.read_bytes(),b'bridge-test')
                    (second/'wireguard-bridge.exe').write_bytes(b'new-version')
                    self.assertNotEqual(bridge_executable(),target)
            self.assertEqual(target.parent.name,hashlib.sha256(b'bridge-test').hexdigest())

if __name__=='__main__':unittest.main()
