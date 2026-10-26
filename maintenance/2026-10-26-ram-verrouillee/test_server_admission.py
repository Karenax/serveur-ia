"""A fake native process proves unlocked READY cannot accept an inference."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dependances/strata-0.1.43.1/source'))
from serve import server

import test_ram_residency as samples


class AdmissionTests(unittest.TestCase):
    def launch(self, text, strict=True):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / 'engine.py'
            script.write_text(
                'import sys\n'
                f'print({text!r}, file=sys.stderr, flush=True)\n'
                'print("READY 4096 stop", flush=True)\n'
                'for line in sys.stdin:\n'
                '    if line.strip() == "QUIT": break\n', encoding='utf-8')
            popen = server.subprocess.Popen
            processes = []

            def fake(command, **kwargs):
                child = popen([sys.executable, str(script)], **kwargs)
                processes.append(child)
                return child

            env = dict(os.environ, KIARA_REQUIRE_LOCKED_RAM='1' if strict else '0')
            engine = None
            try:
                with patch.object(server.subprocess, 'Popen', fake), patch.object(server, 'narrate_start'):
                    engine = server.StrataEngine('synthetic', samples.ResidencyTests.args,
                                                log=str(root / 'engine.log'), env=env)
                self.assertTrue(engine.alive())
            finally:
                if engine:
                    engine.close()
                # Admission failure must already have killed the child, with no
                # live pump or opportunity to receive a GEN command.
                for child in processes:
                    self.assertIsNotNone(child.poll())

    def test_locked_ready_is_accepted(self):
        self.launch(samples.ResidencyTests.ple + samples.ResidencyTests.pinned)

    def test_unlocked_ready_is_killed(self):
        with self.assertRaisesRegex(server.EngineDied, 'RAM'):
            self.launch('ordinary pageable memory')

    def test_other_profiles_are_unchanged(self):
        self.launch('ordinary pageable memory', strict=False)


if __name__ == '__main__':
    unittest.main()
