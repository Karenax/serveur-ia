"""Server startup imports and data locations cannot depend on a client source path."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ColdServerTests(unittest.TestCase):
    def test_imports_with_only_server_and_installed_shared_package(self):
        with tempfile.TemporaryDirectory() as folder:
            env={**os.environ,'PYTHONPATH':str(ROOT/'lanceur'),'KIARA_DATA_DIR':str(Path(folder)/'data')}
            code='import app, remote, releases, voice_max_package, core; print(core.HOME)'
            result=subprocess.run([sys.executable,'-c',code],cwd=folder,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(Path(result.stdout.strip()),Path(folder)/'data')
            self.assertFalse((Path(folder)/'data').exists())


if __name__=='__main__':unittest.main()
