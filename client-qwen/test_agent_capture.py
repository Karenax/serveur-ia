import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from agent_capture import upload_journal


class CaptureTransferTests(unittest.TestCase):
    def test_journal_requires_exact_receipt_and_keeps_original(self):
        session = '34567890-1234-5678-9abc-def012345678'
        command = '12345678-1234-5678-9abc-def012345678'
        raw = b'OggS audio de recette'
        digest = hashlib.sha256(raw).hexdigest()
        packet = {'kind': 'chunk', 'session_id': session, 'track': 'system', 'sequence': 0,
                  'size_bytes': len(raw), 'start_ms': 0, 'duration_ms': 1000, 'sha256': digest,
                  'command_id': command}
        accepted = {'track': 'system', 'seq': 0, 'size_bytes': len(raw), 'sha256': digest}
        receipt = {'acknowledged': True, 'session_id': session, 'accepted_chunk': accepted}
        remote = Mock()
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            manifest = directory / 'system-00000000.json'
            fragment = manifest.with_suffix('.ogg')
            manifest.write_text(json.dumps(packet), encoding='utf-8')
            fragment.write_bytes(raw)
            remote.open.side_effect = [io.BytesIO(json.dumps({**receipt, 'session_id': 'another'}).encode()),
                                       io.BytesIO(json.dumps(receipt).encode())]
            with self.assertRaisesRegex(ValueError, 'reçu de Kiara'):
                list(upload_journal(remote, directory, session))
            self.assertEqual(list(upload_journal(remote, directory, session)), [receipt])
            self.assertEqual(fragment.read_bytes(), raw)
            self.assertEqual(json.loads(manifest.read_text(encoding='utf-8')), packet)
            for call in remote.open.call_args_list:
                self.assertIn(raw, call.args[1])
                self.assertIn(command.encode(), call.args[1])
                self.assertEqual(call.kwargs['method'], 'PUT')
                self.assertEqual(call.kwargs['content_length'], len(call.args[1]))

            fragment.write_bytes(raw + b'!')
            with self.assertRaisesRegex(ValueError, 'journal'):
                list(upload_journal(remote, directory, session))
            self.assertEqual(remote.open.call_count, 2)
