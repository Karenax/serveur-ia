"""Stable updater directories, bounded files and safe legacy handoff cleanup."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import updater


class UpdateLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.target=self.home/'Mon client Kiara.exe';self.target.write_bytes(b'personal-client')
        self.profile={'url':'wireguard://10.77.0.1:8766','token':'fixture-owned-token'}

    def test_preparation_reuses_exact_exe_name_directory_twice(self):
        remote=SimpleNamespace(profile=self.profile)
        release={'available':True}
        def download(remote,release,directory):
            path=directory/'QwenClient.base.exe';path.write_bytes(b'verified');return path
        with patch.object(updater.sys,'frozen',True,create=True),patch.object(updater.sys,'executable',str(self.target)),patch.object(updater,'check',return_value=release),patch.object(updater,'download',side_effect=download),patch.object(updater.subprocess,'Popen'):
            first=updater.prepare(remote,lambda value:value)
            second=updater.prepare(remote,lambda value:value)
        self.assertEqual(first,second);self.assertEqual(first.name,self.target.stem)
        self.assertEqual([path.name for path in self.home.iterdir() if path.is_dir()],[self.target.stem])
        self.assertEqual(json.loads((first/'plan.dpapi').read_bytes())['target'],str(self.target.resolve()))

    def test_failed_preparation_keeps_previous_and_reuses_folder(self):
        folder=updater.work_directory(self.target,self.profile)
        previous=folder/'previous.exe';previous.write_bytes(b'rollback')
        with patch.object(updater.sys,'frozen',True,create=True),patch.object(updater.sys,'executable',str(self.target)),patch.object(updater,'check',return_value={'available':True}),patch.object(updater,'download',side_effect=OSError('download failed')):
            with self.assertRaises(OSError):updater.prepare(SimpleNamespace(profile=self.profile),lambda value:value)
        self.assertEqual(previous.read_bytes(),b'rollback')
        self.assertEqual([path.name for path in self.home.iterdir() if path.is_dir()],[self.target.stem])

    def test_existing_unowned_directory_is_never_changed(self):
        folder=updater.update_directory(self.target);folder.mkdir();document=folder/'notes.txt';document.write_text('Keep this')
        with self.assertRaises(ValueError):updater.work_directory(self.target,self.profile)
        self.assertEqual(document.read_text(),'Keep this');self.assertEqual(list(folder.iterdir()),[document])

    def test_other_profile_cannot_reuse_folder(self):
        updater.work_directory(self.target,self.profile)
        with self.assertRaises(ValueError):updater.work_directory(self.target,{**self.profile,'token':'other'})

    def legacy(self):
        folder=self.home/'qwen-update-fixture';folder.mkdir()
        (folder/'QwenUpdate.exe').write_bytes(b'old-personal-helper')
        ack=folder/'started.json';ack.write_text(json.dumps({'ready':True,'version':'3.5.36'}))
        return folder,ack

    def test_legacy_handoff_retires_only_its_known_directory(self):
        folder,ack=self.legacy();other=self.home/'qwen-update-other';other.mkdir()
        profile={**self.profile,'version':'3.5.36','wireguard':{},'update_public_key':'pinned'}
        result=self.home/'QwenClient-update-result.json';result.write_text(json.dumps({'ok':True,'version':'3.5.36','file':self.target.name}))
        with patch.object(updater,'personal_profile',return_value=profile):
            self.assertTrue(updater.cleanup_legacy_update(ack,self.target,timeout=1))
        self.assertFalse(folder.exists());self.assertTrue(other.exists())
        self.assertTrue((updater.update_directory(self.target)/'update-result.json').exists())
        self.assertFalse(result.exists())

    def test_legacy_unknown_files_or_wrong_owner_are_preserved(self):
        folder,ack=self.legacy();document=folder/'notes.txt';document.write_text('Keep this')
        profile={**self.profile,'version':'3.5.36'}
        with patch.object(updater,'personal_profile',return_value=profile):
            self.assertFalse(updater.cleanup_legacy_update(ack,self.target,timeout=1))
        self.assertEqual(document.read_text(),'Keep this')
        with patch.object(updater,'personal_profile',side_effect=[profile,{**profile,'token':'other'}]):
            self.assertFalse(updater.cleanup_legacy_update(ack,self.target,timeout=1))
        self.assertTrue((folder/'QwenUpdate.exe').exists())


if __name__=='__main__':unittest.main(verbosity=2)
