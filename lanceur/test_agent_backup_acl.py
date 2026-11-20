"""Encrypted project backups retain their destination's access policy."""
import ctypes
from ctypes import wintypes
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_archive import extract_archive
from agent_service import AgentService
from wg_crypto import private_directory


def has_inherited_access_rule(path):
    """Check that the current account has an inherited read grant."""
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    advapi.GetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p,
                                       wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.GetFileSecurityW.restype = wintypes.BOOL
    advapi.GetSecurityDescriptorDacl.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL),
                                                ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.BOOL)]
    advapi.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    advapi.GetAce.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
    advapi.GetAce.restype = wintypes.BOOL
    advapi.ConvertStringSidToSidW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
    advapi.ConvertStringSidToSidW.restype = wintypes.BOOL
    advapi.EqualSid.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    advapi.EqualSid.restype = wintypes.BOOL
    required = wintypes.DWORD()
    advapi.GetFileSecurityW(str(path), 4, None, 0, ctypes.byref(required))
    if not required.value:
        raise ctypes.WinError(ctypes.get_last_error())
    descriptor = ctypes.create_string_buffer(required.value)
    if not advapi.GetFileSecurityW(str(path), 4, descriptor, required, ctypes.byref(required)):
        raise ctypes.WinError(ctypes.get_last_error())
    present, defaulted, dacl = wintypes.BOOL(), wintypes.BOOL(), ctypes.c_void_p()
    if not advapi.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not present.value or not dacl.value:
        return False

    class Acl(ctypes.Structure):
        _fields_ = [('revision', ctypes.c_ubyte), ('reserved', ctypes.c_ubyte),
                    ('size', ctypes.c_ushort), ('count', ctypes.c_ushort), ('reserved2', ctypes.c_ushort)]

    class AceHeader(ctypes.Structure):
        _fields_ = [('type', ctypes.c_ubyte), ('flags', ctypes.c_ubyte), ('size', ctypes.c_ushort)]

    user = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'], capture_output=True,
                          text=True, encoding='cp850', check=True, creationflags=0x08000000)
    sid_text = next(csv.reader(io.StringIO(user.stdout)))[1]
    sid = ctypes.c_void_p()
    if not advapi.ConvertStringSidToSidW(sid_text, ctypes.byref(sid)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        for index in range(ctypes.cast(dacl, ctypes.POINTER(Acl)).contents.count):
            ace = ctypes.c_void_p()
            if not advapi.GetAce(dacl, index, ctypes.byref(ace)):
                raise ctypes.WinError(ctypes.get_last_error())
            header = ctypes.cast(ace, ctypes.POINTER(AceHeader)).contents
            mask = ctypes.c_uint32.from_address(ace.value + 4).value
            if (header.type == 0 and header.flags & 0x10 and mask & 0x120089 == 0x120089
                    and advapi.EqualSid(sid, ctypes.c_void_p(ace.value + 8))):
                return True
        return False
    finally:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree(sid)


@unittest.skipUnless(os.name == 'nt', 'ACL Windows requises')
class AgentBackupAclTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kiara-agent-acl-', dir=os.environ.get('KIARA_TEST_TEMP_DIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.data = self.root/'data'
        self.data.mkdir()
        self.destination = self.root/'destination'
        private_directory(self.destination)
        self.target = self.destination/'fictif.kiara-agent'
        self.service = AgentService(None, self.data, self.root/'python.exe')

    @staticmethod
    def fake_tool(script, *paths):
        folder = Path(paths[0])
        if 'create_backup' in script:
            (folder/'brain').mkdir(parents=True)
            (folder/'brain/notice.txt').write_text('Données fictives', encoding='utf-8')
        else:
            assert (folder/'brain/notice.txt').read_text(encoding='utf-8') == 'Données fictives'

    def run_backup(self):
        with patch.object(self.service, 'running', return_value=False), \
             patch.object(self.service, '_archive_tool', side_effect=self.fake_tool):
            return self.service.backup_archive(self.target, 'phrase de recette fictive')

    def test_archive_inherits_destination_and_restores(self):
        self.assertEqual(self.run_backup(), self.target)
        self.assertTrue(has_inherited_access_rule(self.target))
        restored = self.root/'restaure'
        restored.mkdir()
        extract_archive(self.target, restored, 'phrase de recette fictive')
        self.assertEqual((restored/'brain/notice.txt').read_text(encoding='utf-8'), 'Données fictives')
        self.assertEqual(list(self.destination.glob('.agent-verification-*.tmp')), [])

    def test_collision_does_not_remove_an_existing_file(self):
        unrelated = self.destination/('.agent-verification-' + 'a'*32 + '.tmp')
        unrelated.write_bytes(b'fichier fictif preexistant')
        with patch('agent_service.secrets.token_hex', return_value='a'*32):
            with self.assertRaises(ValueError):
                self.run_backup()
        self.assertEqual(unrelated.read_bytes(), b'fichier fictif preexistant')
        self.assertFalse(self.target.exists())

    def test_reused_temporary_name_is_not_deleted_after_publication(self):
        original_rename = Path.rename
        reused = self.destination/('.agent-verification-' + 'b'*32 + '.tmp')

        def rename_and_reuse(source, destination):
            result = original_rename(source, destination)
            if source == reused:
                source.write_bytes(b'fichier cree ensuite')
            return result

        with patch('agent_service.secrets.token_hex', return_value='b'*32), \
             patch.object(Path, 'rename', rename_and_reuse):
            self.run_backup()
        self.assertEqual(reused.read_bytes(), b'fichier cree ensuite')
        self.assertTrue(self.target.is_file())

    def test_failed_verification_removes_only_the_new_temporary_archive(self):
        unrelated = self.destination/'autre-fichier'
        unrelated.write_bytes(b'conserve')

        def failing_tool(script, *paths):
            if 'verify_backup' in script:
                raise ValueError('Échec fictif de vérification')
            self.fake_tool(script, *paths)

        with patch.object(self.service, 'running', return_value=False), \
             patch.object(self.service, '_archive_tool', side_effect=failing_tool):
            with self.assertRaisesRegex(ValueError, 'Échec fictif'):
                self.service.backup_archive(self.target, 'phrase de recette fictive')
        self.assertEqual(unrelated.read_bytes(), b'conserve')
        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.destination.glob('.agent-verification-*.tmp')), [])

    def test_process_interruption_keeps_existing_data_and_unpublished_encrypted_archive(self):
        import agent_service
        import kiara_shared

        previous = self.destination/'precedente.kiara-agent'
        previous.write_bytes(b'archive anterieure fictive')
        child = self.root/'interruption.py'
        child.write_text('''from pathlib import Path\nimport os, sys\nfrom agent_service import AgentService\n'''
                         '''data, target = map(Path, sys.argv[1:])\n'''
                         '''service = AgentService(None, data, data.parent/'python.exe')\n'''
                         '''service.running = lambda: False\n'''
                         '''def tool(script, *paths):\n'''
                         '''    if 'verify_backup' in script: os._exit(67)\n'''
                         '''    folder = Path(paths[0])/'brain'\n'''
                         '''    folder.mkdir(parents=True)\n'''
                         '''    (folder/'notice.txt').write_text('Données fictives',encoding='utf-8')\n'''
                         '''service._archive_tool = tool\n'''
                         '''service.backup_archive(target, 'phrase de recette fictive')\n''', encoding='utf-8')
        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join((str(Path(agent_service.__file__).parent),
                                             str(Path(kiara_shared.__file__).parent.parent)))
        process = subprocess.run([sys.executable, str(child), str(self.data), str(self.target)],
                                 cwd=self.root, env=env, capture_output=True, timeout=45)
        self.assertEqual(process.returncode, 67, process.stderr)
        self.assertEqual(previous.read_bytes(), b'archive anterieure fictive')
        self.assertFalse(self.target.exists())
        pending = list(self.destination.glob('.agent-verification-*.tmp'))
        self.assertEqual(len(pending), 1)
        with pending[0].open('rb') as stream:
            self.assertEqual(stream.read(14), b'KIARA-AGENT-1\0')
        restored = self.root/'restaure-interruption'
        restored.mkdir()
        extract_archive(pending[0], restored, 'phrase de recette fictive')
        self.assertEqual((restored/'brain/notice.txt').read_text(encoding='utf-8'), 'Données fictives')

    def test_backup_manager_preserves_the_verified_pair_and_secondary_copy(self):
        from test_backups import BackupsTests, PHRASE

        fixture = BackupsTests('test_complete_encrypted_snapshot_and_public_catalogue')
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        (fixture.home/'appareils-activite.json').write_text(json.dumps({
            fixture.owner: {'platform': 'windows', 'version': '4.0.0'}
        }), encoding='utf-8')
        project_data = fixture.home/'project-data'
        project_data.mkdir()
        service = AgentService(None, project_data, fixture.home/'python.exe')
        fixture.c.agent_service = service
        secondary = fixture.home/'secondary'
        fixture.b.configure({'secondary_destination': str(secondary)})
        with patch.object(service, 'running', return_value=False), \
             patch.object(service, '_archive_tool', side_effect=self.fake_tool):
            record = fixture.backup()
        archive = Path(record['agent']['file'])
        self.assertTrue(has_inherited_access_rule(archive))
        self.assertEqual(record['secondary']['status'], 'copied')
        self.assertEqual(hashlib.sha256((secondary/archive.name).read_bytes()).hexdigest(), record['agent']['sha256'])
        restored = fixture.home/'restaure-test'
        restored.mkdir()
        extract_archive(secondary/archive.name, restored, PHRASE)
        self.assertEqual((restored/'brain/notice.txt').read_text(encoding='utf-8'), 'Données fictives')


if __name__ == '__main__':
    unittest.main()
