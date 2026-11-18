"""A Windows path limit must offer a safe recovery instead of an opaque error."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_archive import extract_archive, write_archive


class AgentArchiveLongPathsTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Limite des chemins Windows')
    def test_long_extraction_path_suggests_short_destination_and_keeps_archive(self):
        with tempfile.TemporaryDirectory(prefix='kiara-path-test-') as folder:
            root = Path(folder)
            snapshot = root / 'snapshot'
            original = snapshot / 'storage' / ('a' * 70) / ('b' * 70) / ('c' * 35)
            original.parent.mkdir(parents=True)
            original.write_bytes(b'contenu fictif')
            archive = root / 'backup.kiara-agent'
            phrase = 'Phrase de test temporaire 2026'
            write_archive(snapshot, archive, phrase)
            before = archive.read_bytes()
            destination = root / ('d' * 65)
            destination.mkdir()
            real_open = Path.open

            def fail_long_write(path, mode='r', *args, **kwargs):
                if mode == 'xb' and len(str(path)) >= 248:
                    raise FileNotFoundError(2, 'Chemin fictif introuvable')
                return real_open(path, mode, *args, **kwargs)

            with patch.object(Path, 'open', fail_long_write):
                with self.assertRaisesRegex(ValueError, 'dossier plus proche de la racine'):
                    extract_archive(archive, destination, phrase)
            self.assertEqual(archive.read_bytes(), before)
            short_destination = root / 'ok'
            short_destination.mkdir()
            extract_archive(archive, short_destination, phrase)
            self.assertEqual((short_destination / original.relative_to(snapshot)).read_bytes(), b'contenu fictif')


if __name__ == '__main__':
    unittest.main()
