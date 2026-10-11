"""A server rollback cannot silently overwrite or republish an offline cache."""
import io
import json
import tempfile
from pathlib import Path
import threading
import unittest
import urllib.error
from test_remote import client
from history_sync import HistorySync
from history_store import HISTORY_RESET_ID, read
from test_history_sync import history


class GenerationRemote:
    def __init__(self):
        self.connected=True;self.reachable=True;self.code='';self.active_requests=0;self.activity_lock=threading.RLock()
        self.value={'history':history('original'),'revision':1,'reset_id':HISTORY_RESET_ID,'generation':'a'*32,'restored':False}
        self.writes=0

    def open(self,path,body=None):
        if body is not None:
            data=json.loads(body)
            if data.get('generation')!=self.value['generation'] or data['revision']!=self.value['revision']:
                raise urllib.error.HTTPError(path,409,'server restored',{},io.BytesIO())
            self.writes+=1
            self.value.update(history=data['history'],revision=self.value['revision']+1)
        return io.BytesIO(json.dumps(self.value).encode())


class RestoreClientTests(unittest.TestCase):
    def test_background_and_startup_keep_cache_until_explicit_ack(self):
        with tempfile.TemporaryDirectory() as tmp:
            remote=GenerationRemote();path=Path(tmp)/'history.dpapi'
            sync=HistorySync(remote,path,client.protect);initial=sync.synchronize()
            self.assertEqual(initial['history'],history('original'))
            original_raw=path.read_bytes()
            remote.value.update(history=history('restored snapshot'),revision=1,generation='b'*32,restored=True)
            changed=history('offline newer text');sync.write(changed,initial['revision']);sync.flush()
            self.assertEqual(remote.writes,0)
            cached_raw=path.read_bytes()
            result=sync.synchronize()
            self.assertTrue(result['requires_restore_ack']);self.assertEqual(result['history'],changed)
            self.assertEqual(path.read_bytes(),cached_raw)
            with self.assertRaises(ValueError):sync.acknowledge_restore(False)
            resumed=sync.acknowledge_restore(True)
            self.assertEqual(resumed['history'],history('restored snapshot'))
            saved=Path(resumed['restore_backup']);self.assertEqual(saved.read_bytes(),cached_raw)
            self.assertEqual(read(saved,client.protect)['history'],changed)
            self.assertNotIn(b'offline newer text',saved.read_bytes())
            self.assertEqual(remote.writes,0)
            sync.write(history('new after acknowledgment'),resumed['revision']);sync.flush()
            self.assertEqual(remote.value['history'],history('new after acknowledgment'))
            reopened=HistorySync(remote,path,client.protect)
            self.assertFalse(reopened.synchronize().get('requires_restore_ack'))

    def test_upgrade_before_any_restore_does_not_force_ack(self):
        with tempfile.TemporaryDirectory() as tmp:
            remote=GenerationRemote();sync=HistorySync(remote,Path(tmp)/'history.dpapi',client.protect)
            sync.synchronize()
            sync.meta.pop('generation',None)
            self.assertFalse(sync.synchronize().get('requires_restore_ack'))


if __name__=='__main__':unittest.main()
