"""Fictional marker files; no real client profile is opened."""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from portal_origin_state import OriginStateError, read_origin, record_origin


class OriginStateTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / 'fictif.origin.json'

    def test_choice_is_durable_idempotent_and_cannot_be_replaced(self):
        self.assertIsNone(read_origin(self.path))
        self.assertEqual(record_origin(self.path, 17843), 17843)
        before = self.path.read_bytes()
        self.assertEqual(record_origin(self.path, 17843), 17843)
        with self.assertRaises(OriginStateError): record_origin(self.path, 17841)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(read_origin(self.path), 17843)
        self.assertEqual(list(self.root.glob('*.tmp')), [])

    def test_unknown_or_truncated_file_is_not_treated_as_missing(self):
        for data in (b'', b'{', b'{"format":2,"port":17841}', b'{"format":1,"port":true}',
                     b'{"format":1,"port":17841,"extra":0}', b'{"format":1,"port":17841,"port":17842}', b'x' * 1025, b'\xff'):
            self.path.write_bytes(data)
            with self.assertRaises(OriginStateError): read_origin(self.path)
            with self.assertRaises(OriginStateError): record_origin(self.path, 17841)
            self.assertEqual(self.path.read_bytes(), data)

    def test_failing_write_keeps_marker_absent_and_removes_only_own_temporary(self):
        sentinel = self.root / 'sentinel.tmp'
        sentinel.write_bytes(b'conserver')
        with patch('portal_origin_state.os.fsync', side_effect=OSError('failed')):
            with self.assertRaises(OriginStateError): record_origin(self.path, 17841)
        self.assertFalse(self.path.exists())
        self.assertEqual(sentinel.read_bytes(), b'conserver')
        self.assertEqual(record_origin(self.path, 17841), 17841)

    def test_failure_to_link_does_not_create_a_marker(self):
        with patch('portal_origin_state.os.link', side_effect=OSError('not supported')):
            with self.assertRaises(OriginStateError): record_origin(self.path, 17841)
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_racing_choices_never_replace_the_winner(self):
        def attempt(port):
            try: return record_origin(self.path, port)
            except OriginStateError: return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, [17841,17842] * 10))
        winner = read_origin(self.path)
        self.assertIn(winner, (17841,17842))
        self.assertTrue(all(value in (None, winner) for value in results))
        self.assertEqual(set(self.root.iterdir()), {self.path})
        self.assertEqual(json.loads(self.path.read_bytes())['port'], winner)

    def test_symlink_is_never_followed_or_replaced(self):
        target = self.root / 'other.txt'
        target.write_bytes(b'sentinel')
        try:
            self.path.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('Création de lien symbolique indisponible sur ce poste.')
        with self.assertRaises(OriginStateError): read_origin(self.path)
        with self.assertRaises(OriginStateError): record_origin(self.path, 17841)
        self.assertEqual(target.read_bytes(), b'sentinel')
        self.assertTrue(self.path.is_symlink())

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'Tubes nommés indisponibles sur ce système.')
    def test_named_pipe_is_rejected_without_waiting_for_a_writer(self):
        os.mkfifo(self.path)
        program = (
            'import sys\n'
            'from portal_origin_state import OriginStateError, read_origin\n'
            'try:\n'
            '    read_origin(sys.argv[1])\n'
            'except OriginStateError:\n'
            '    sys.exit(0)\n'
            'sys.exit(1)\n'
        )
        result = subprocess.run([sys.executable, '-B', '-c', program, str(self.path)],
                                capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.path.exists())

    def test_invalid_port_is_never_recorded(self):
        for port in (None, True, 17840, 17851, '17841'):
            with self.assertRaises(ValueError): record_origin(self.path, port)
        self.assertFalse(self.path.exists())

if __name__ == '__main__': unittest.main()
