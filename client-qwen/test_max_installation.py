"""Consent, signed executable distribution, bounded extraction and independent caches."""
import base64
import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from max_installation import MaxInstallation, canonical, relative_path, verify_catalogue


class MaxInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key = Ed25519PrivateKey.generate()
        self.pinned = base64.b64encode(self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
        self.calls = []
        parent = self
        class Remote:
            profile = {'update_public_key': parent.pinned}
            def open(self, path):
                parent.calls.append(path)
                return io.BytesIO(json.dumps(parent.catalogue).encode() if path.endswith('/package') else parent.archive)
        class Runtime:
            testing = False
            maintenance = False
            def status(self):return {'busy': False, 'available': True, 'message': 'Mode Max prêt'}
            def unload(self):pass
            def test(self):return self.status()
            def begin_maintenance(self):
                if self.testing or self.status().get('busy'):raise ValueError('Max est en cours d’utilisation.')
                self.maintenance=True
            def end_maintenance(self,removed=False):self.maintenance=False
        self.archive, entries = self.make_archive({'max-worker.exe': b'MZ reviewed worker', 'native/qwen.dll': b'MZ reviewed native'})
        self.model = b'public pinned model'
        self.catalogue = {'format': 2, 'revision': 'fixture-v2', 'engine': 'Parakeet + Qwen3-TTS',
            'runtime': {'name': 'runtime.zip', 'bytes': len(self.archive), 'sha256': hashlib.sha256(self.archive).hexdigest(), 'files': entries},
            'models': [{'name': 'asr/encoder.int8.onnx', 'bytes': len(self.model), 'sha256': hashlib.sha256(self.model).hexdigest(),
                        'url': 'https://huggingface.co/org/model/resolve/'+'a'*40+'/encoder.int8.onnx'}]}
        self.sign()
        with patch('max_installation.hardware', return_value={'checked': True, 'eligible': True, 'cards': [{'vendor': 'amd', 'name': 'AMD fixture'}]}):
            self.install = MaxInstallation(self.root/'max', Remote(), Runtime(), self.root/'low')
            self.install.detect()
        self.addCleanup(self.install.close)

    def sign(self):
        self.catalogue['signature'] = base64.b64encode(self.key.sign(canonical(self.catalogue))).decode()

    @staticmethod
    def make_archive(files):
        output = io.BytesIO(); entries = []
        with zipfile.ZipFile(output, 'w') as archive:
            for name, data in files.items():
                archive.writestr(name, data)
                entries.append({'name': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        return output.getvalue(), entries

    def cached_model(self):
        self.install.shared_asr.mkdir()
        (self.install.shared_asr/'encoder.int8.onnx').write_bytes(self.model)

    def test_startup_downloads_nothing_and_install_requires_the_displayed_plan(self):
        self.assertEqual(self.calls, [])
        with self.assertRaises(ValueError):self.install.install('arbitrary')
        self.assertEqual(self.calls, [])
        plan = self.install.plan()
        self.assertEqual(self.calls, ['/v1/voice/max/package'])
        self.assertEqual(plan['download_bytes'], len(self.archive)+len(self.model))
        with self.assertRaises(ValueError):self.install.install('stale plan')

    def test_signature_size_and_source_changes_are_rejected(self):
        self.assertIs(verify_catalogue(self.catalogue, self.pinned), self.catalogue)
        self.catalogue['runtime']['bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'signature'):verify_catalogue(self.catalogue, self.pinned)
        self.catalogue['models'][0]['url'] = 'https://example.test/worker.exe'; self.sign()
        with self.assertRaisesRegex(ValueError, 'Source'):verify_catalogue(self.catalogue, self.pinned)

    def test_complete_install_reuses_low_models_without_changing_them(self):
        self.cached_model()
        plan = self.install.plan()
        self.assertEqual(plan['download_bytes'], len(self.archive))
        self.assertEqual(plan['reused_bytes'], len(self.model))
        self.install.install(plan['plan']); self.install.thread.join(5)
        self.assertFalse(self.install.thread.is_alive())
        self.assertEqual(self.install.status()['phase'], 'ready', self.install.status())
        self.assertEqual((self.install.shared_asr/'encoder.int8.onnx').read_bytes(), self.model)
        configuration = json.loads((self.install.home/'runtime.json').read_text())
        self.assertEqual(configuration['format'], 2)
        self.assertEqual((Path(configuration['root'])/'asr/encoder.int8.onnx').read_bytes(), self.model)
        self.assertEqual(self.calls, ['/v1/voice/max/package', '/v1/voice/max/package/download'])

    def test_new_french_model_is_counted_in_download_and_never_reuses_the_old_chinese_preset(self):
        old=self.install.home/'models/tts/talker.gguf';old.parent.mkdir(parents=True);old.write_bytes(b'old CustomVoice')
        self.catalogue['models'][0].update(name='tts/talker.gguf',url='https://huggingface.co/org/model/resolve/'+'b'*40+'/base.gguf')
        self.sign();plan=self.install.plan()
        self.assertEqual(plan['download_bytes'],len(self.archive)+len(self.model))
        self.assertEqual(plan['reused_bytes'],0)
        self.assertEqual(old.read_bytes(),b'old CustomVoice')

    def test_corrupt_or_cancelled_download_cannot_replace_a_working_runtime(self):
        self.cached_model(); self.install.home.mkdir()
        pointer = self.install.home/'runtime.json'; pointer.write_text('old working runtime')
        plan = self.install.plan(); self.archive = self.archive[:-1]+b'!'
        self.install.install(plan['plan']); self.install.thread.join(5)
        self.assertEqual(self.install.status()['phase'], 'error')
        self.assertEqual(pointer.read_text(), 'old working runtime')
        self.assertFalse((self.install.home/'packs/fixture-v2/max-worker.exe').exists())

    def test_zip_traversal_symlinks_duplicates_and_unexpected_files_are_rejected(self):
        for name in ('../outside.exe', '/outside.exe', 'C:/outside.exe', 'native\\outside.dll', 'native/CON.dll', 'native/../outside.dll'):
            with self.subTest(name=name), self.assertRaises(ValueError):relative_path(name)
        for files in ({'../outside.exe': b'bad'}, {'extra.exe': b'bad'}):
            archive, entries = self.make_archive(files)
            path = self.root/'bad.zip'; path.write_bytes(archive)
            with self.assertRaises(ValueError):self.install._extract(path, self.root/'unpacked', self.catalogue['runtime']['files'])
        path = self.root/'link.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for entry in self.catalogue['runtime']['files']:
                info = zipfile.ZipInfo(entry['name']); info.external_attr = (stat.S_IFLNK|0o777)<<16
                archive.writestr(info, b'x'*entry['bytes'])
        with self.assertRaises(ValueError):self.install._extract(path, self.root/'unpacked', self.catalogue['runtime']['files'])

    def test_intel_is_not_offered_and_active_inference_cannot_be_replaced(self):
        self.install.device = {'checked': True, 'eligible': False, 'cards': []}
        with self.assertRaises(ValueError):self.install.plan()
        self.assertEqual(self.calls, [])
        self.install.device['eligible'] = True
        plan = self.install.plan()
        with patch.object(self.install.runtime, 'status', return_value={'busy': True}):
            with self.assertRaises(ValueError):self.install.install(plan['plan'])

    def test_runtime_updates_reuse_previously_downloaded_max_weights(self):
        cache=self.install.home/'models/asr/encoder.int8.onnx';cache.parent.mkdir(parents=True);cache.write_bytes(self.model)
        plan=self.install.plan()
        self.assertEqual(plan['download_bytes'],len(self.archive))
        self.assertEqual(plan['reused_bytes'],len(self.model))

    def test_remove_all_max_files_preserves_low_and_allows_reinstallation(self):
        self.cached_model()
        root=self.install.home
        for name in ('models/weights.bin','packs/old/native/runtime.dll','downloads/runtime.zip.part','legacy/python.exe','benchmark.json'):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
        # Removing a hard link must leave the Low model intact.
        (root/'linked-model').hardlink_to(self.install.shared_asr/'encoder.int8.onnx')
        storage=self.install.storage()
        self.assertEqual(storage['path'],str(root.absolute()))
        self.assertTrue(storage['exists']);self.assertGreater(storage['bytes'],0)
        with patch.object(self.install.runtime,'unload') as unload:
            result=self.install.remove();unload.assert_called_once()
        self.assertFalse(root.exists());self.assertFalse(result['storage']['exists'])
        self.assertFalse(self.install.runtime.maintenance);self.assertEqual(self.calls,[])
        self.assertEqual((self.install.shared_asr/'encoder.int8.onnx').read_bytes(),self.model)
        plan=self.install.plan();self.install.install(plan['plan']);self.install.thread.join(5)
        self.assertEqual(self.install.status()['phase'],'ready')

    def test_remove_refuses_active_call_test_and_download(self):
        root=self.install.home;root.mkdir();(root/'keep').write_text('safe')
        with patch.object(self.install.runtime,'status',return_value={'busy':True}):
            with self.assertRaises(ValueError):self.install.remove()
        self.install.runtime.testing=True
        with self.assertRaises(ValueError):self.install.remove()
        self.install.runtime.testing=False
        with patch.object(self.install,'thread') as thread:
            thread.is_alive.return_value=True
            with self.assertRaises(ValueError):self.install.remove()
        self.assertEqual((root/'keep').read_text(),'safe')

    def test_remove_rejects_shared_directory_and_external_junction_before_deleting(self):
        self.cached_model()
        root=self.install.home;root.mkdir();(root/'keep').write_text('safe')
        with patch.object(self.install,'home',self.install.shared_asr):
            with self.assertRaises(ValueError):self.install.remove()
        # Model the Windows reparse-point check without requiring symlink privileges.
        (root/'external').mkdir()
        original=Path.is_junction
        with patch.object(Path,'is_junction',lambda path:path==root/'external' or original(path)):
            with self.assertRaisesRegex(ValueError,'lien'):self.install.remove()
        self.assertEqual((root/'keep').read_text(),'safe')
        self.assertFalse(self.install.runtime.maintenance)
        self.assertEqual((self.install.shared_asr/'encoder.int8.onnx').read_bytes(),self.model)

    def test_open_folder_uses_only_the_owned_directory(self):
        with patch('max_installation.os.startfile') as start:
            with self.assertRaises(ValueError):self.install.open_folder()
            start.assert_not_called()
            self.install.home.mkdir();self.install.open_folder()
            start.assert_called_once_with(str(self.install.home.absolute()))

    def test_cancelled_stream_never_activates_a_partial_install_and_retry_succeeds(self):
        self.cached_model();plan=self.install.plan()
        original=self.install.remote.open
        parent=self
        class Interrupted(io.BytesIO):
            def read(self,size=-1):
                parent.install.cancel()
                return super().read(size)
        with patch.object(self.install.remote,'open',side_effect=lambda path:Interrupted(self.archive) if path.endswith('/download') else original(path)):
            self.install.install(plan['plan']);self.install.thread.join(5)
        self.assertEqual(self.install.status()['phase'],'cancelled')
        self.assertFalse((self.install.home/'runtime.json').exists())
        self.install.install(plan['plan']);self.install.thread.join(5)
        self.assertEqual(self.install.status()['phase'],'ready',self.install.status())


if __name__ == '__main__':unittest.main(verbosity=2)
