"""Stable updater directories, bounded files and safe legacy handoff cleanup."""
import base64
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import updater
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class UpdateLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.target=self.home/'Mon client Kiara.exe';self.target.write_bytes(b'personal-client')
        self.profile={'url':'wireguard://10.77.0.1:8766','token':'fixture-owned-token'}

    def test_desktop_channel_selects_newer_signed_installer_and_rejects_tampering(self):
        signer = Ed25519PrivateKey.generate()
        binary = b'fixture installer'
        release = {'version': '4.0.1', 'protocol': 4, 'bytes': len(binary),
                   'sha256': hashlib.sha256(binary).hexdigest()}
        signature = signer.sign(json.dumps(release, sort_keys=True, separators=(',', ':')).encode())
        release['signature'] = base64.b64encode(signature).decode()
        remote = SimpleNamespace(version='3.5.63', profile={
            'update_public_key': base64.b64encode(signer.public_key().public_bytes_raw()).decode()})
        responses = {updater.DESKTOP_RELEASE: json.dumps(release).encode(), updater.DESKTOP_DOWNLOAD: binary}
        remote.open = lambda path: io.BytesIO(responses[path])

        metadata, installer = updater.prepare_kiara4(remote, self.home)
        self.assertEqual(metadata['version'], '4.0.1')
        self.assertEqual(installer.name, 'Kiara_4.0.1_x64-setup.exe')
        self.assertEqual(installer.read_bytes(), binary)

        remote.version = '4.0.1'
        with self.assertRaisesRegex(ValueError, 'à jour'):
            updater.prepare_kiara4(remote, self.home)
        remote.version = '4.0.0'
        responses[updater.DESKTOP_DOWNLOAD] = binary.lower() + b'!'
        with self.assertRaises(ValueError):
            updater.prepare_kiara4(remote, self.home)
        self.assertFalse(installer.exists())

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
