"""Lock checks run only on temporary fictional Chromium profiles."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from portal_qt_profile_guard import ensure_qt_profile_idle,ensure_qt_profile_owned,QtProfileInUse,QtProfileUnavailable


@unittest.skipUnless(sys.platform.startswith('linux'),'Le verrou Qt est propre à Linux.')
class QtProfileGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'profile';self.root.mkdir()

    def held(self,relative,api='lockf'):
        path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fictif')
        code=("import fcntl,sys; f=open(sys.argv[1],'rb'); "
              f"fcntl.{api}(f,fcntl.LOCK_SH|fcntl.LOCK_NB); print('ready',flush=True); sys.stdin.buffer.read()")
        # Acquire an exclusive lock using a writable descriptor in the child.
        code=code.replace("open(sys.argv[1],'rb')","open(sys.argv[1],'r+b')").replace('LOCK_SH','LOCK_EX')
        proc=subprocess.Popen([sys.executable,'-u','-c',code,str(path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.addCleanup(lambda:proc.poll() is None and proc.kill())
        self.assertEqual(proc.stdout.readline(),b'ready\n')
        try:
            with self.assertRaises(QtProfileInUse):ensure_qt_profile_idle(self.root)
            if api=='lockf':
                ensure_qt_profile_owned(self.root,proc.pid)
                with self.assertRaises(QtProfileInUse):ensure_qt_profile_owned(self.root,proc.pid+10000000)
            else:
                with self.assertRaises(QtProfileUnavailable):ensure_qt_profile_owned(self.root,proc.pid)
            self.assertEqual(path.read_bytes(),b'fictif')
        finally:
            proc.stdin.close();proc.wait(timeout=5);proc.stdout.close();proc.stderr.close()
        ensure_qt_profile_idle(self.root);self.assertEqual(path.read_bytes(),b'fictif')

    def test_empty_profile_is_not_modified(self):
        ensure_qt_profile_idle(self.root);self.assertEqual(list(self.root.iterdir()),[])

    def test_local_session_and_indexeddb_locks_are_detected(self):
        for path in ('Local Storage/leveldb/LOCK','Session Storage/LOCK','IndexedDB/http_127.0.0.1_17841.indexeddb.leveldb/LOCK'):
            with self.subTest(path=path):self.held(path)

    def test_flock_variant_is_detected(self):self.held('Local Storage/leveldb/LOCK',api='flock')

    def test_symlinked_storage_or_lock_is_never_followed(self):
        target=self.root/'target';target.mkdir();(self.root/'Local Storage').symlink_to(target,target_is_directory=True)
        with self.assertRaises(QtProfileUnavailable):ensure_qt_profile_idle(self.root)
        self.assertEqual(list(target.iterdir()),[])


if __name__=='__main__':unittest.main()
