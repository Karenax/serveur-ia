"""A missing marker must never silently erase a valid protected cache."""
import json
from pathlib import Path
import tempfile
import unittest

import history_store
from history_sync import HistorySync


class HistoryMigrationTests(unittest.TestCase):
    def test_missing_marker_keeps_valid_cache_and_unreadable_archives(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'history.dpapi'
            history={'currentId':'one','conversations':[{'id':'one','title':'À garder','messages':[]}]}
            original=json.dumps(history).encode();path.write_bytes(original)
            archive=path.with_name('history.unreadable-before.dpapi');archive.write_bytes(b'old-private-bytes')
            HistorySync(None,path,lambda raw,**kwargs:raw)
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(archive.read_bytes(),b'old-private-bytes')
            self.assertEqual(history_store.read(path,lambda raw,**kwargs:raw)['history'],history)

    def test_unknown_cache_is_kept_as_a_protected_recovery_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'history.dpapi';path.write_bytes(b'unreadable-encrypted-original')
            sync=HistorySync(None,path,lambda raw,**kwargs:raw)
            recovery=list(Path(folder).glob('history.recovery-*.dpapi'))
            self.assertEqual(len(recovery),1)
            self.assertEqual(recovery[0].read_bytes(),b'unreadable-encrypted-original')
            self.assertIn('récupération',sync.status()['message'])


if __name__=='__main__':unittest.main()
