"""A restore proof must match a verified paired catalogue entry."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from backups import _project_backup_status
import restore_evidence


class RestoreEvidenceTests(unittest.TestCase):
    def test_project_backup_marker_is_read_separately_without_exposing_its_path(self):
        with tempfile.TemporaryDirectory(prefix='kiara-project-status-') as folder:
            root = Path(folder)
            controller = SimpleNamespace(agent_service=SimpleNamespace(data=root))
            self.assertEqual(_project_backup_status(controller), {'state':'none'})
            (root/'storage').mkdir()
            marker = root/'storage/backup-status.json'
            marker.write_text(json.dumps({'directory':'chemin privé', 'status':'verified',
                'created_at':'2026-01-01T03:00:00+00:00', 'verified_at':'2026-01-01T03:05:00+00:00'}), encoding='utf-8')
            self.assertEqual(_project_backup_status(controller), {'state':'recorded','status':'verified',
                'created_at':'2026-01-01T03:00:00+00:00','verified_at':'2026-01-01T03:05:00+00:00'})
            marker.write_text('{', encoding='utf-8')
            self.assertEqual(_project_backup_status(controller), {'state':'unavailable'})

    def test_only_a_completed_matching_restore_is_published(self):
        with tempfile.TemporaryDirectory(prefix='kiara-proof-') as folder:
            root = Path(folder)
            digest = 'a' * 64
            archive = {'id':'test-pair', 'file':str(root/'test.qwenbackup'), 'verified':True,
                       'created_at':'2026-01-01T03:00:00+00:00', 'agent':{'sha256':digest}}
            (root/'catalogue.json').write_text(json.dumps({'catalog':[archive]}), encoding='utf-8')
            report = {'archive':'test.qwenbackup', 'companion_sha256':digest,
                      'verified_at':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(),
                      'remote_disabled':True, 'isolated_data_removed':True,
                      'verified_originals':{'mails':1,'html':1,'with_attachment':0,'audio':1},
                      'databases':{name:{'integrity':'ok','foreign_key_violations':0}
                                   for name in ('espaces','projets','connaissances')}}
            restore_evidence.record(root, report)
            expected = {'verified_at':report['verified_at'], 'archive_created_at':archive['created_at'], 'scope':'paired'}
            self.assertEqual(restore_evidence.status(root, [archive]), expected)
            proof = (root/restore_evidence.PROOF_NAME).read_bytes()
            with self.assertRaises(ValueError):
                restore_evidence.record(root, {**report, 'companion_sha256':'b' * 64})
            self.assertEqual((root/restore_evidence.PROOF_NAME).read_bytes(), proof)
            self.assertIsNone(restore_evidence.status(root, [{**archive, 'agent':{'sha256':'b' * 64}}]))
            with self.assertRaises(ValueError):
                restore_evidence.record(root, {**report, 'isolated_data_removed':False})


if __name__ == '__main__':
    unittest.main()
