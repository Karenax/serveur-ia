"""Installation and launcher boundaries use isolated fictional packages."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('kiara_linux_installer',ROOT/'installer.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
launch_spec=importlib.util.spec_from_file_location('kiara_linux_launch',ROOT/'linux_launch.py')
launcher=importlib.util.module_from_spec(launch_spec);launch_spec.loader.exec_module(launcher)


class PackageIntegrityTests(unittest.TestCase):
    def make_package(self, root):
        names=launcher.REQUIRED_FILES
        files={}
        for name in names:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
            data=('fictif:'+name).encode();path.write_bytes(data);files[name]=hashlib.sha256(data).hexdigest()
        return files

    def test_missing_critical_manifest_entries_are_rejected_without_touching_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);files=self.make_package(root)
            for name in ('kiara','kiara-relay','requirements.lock','client/draft_store.py','client/portal_origin_state.py',
                         'client/voice/conversation-worker/linux_audio.py','client/voice/wakeword/encoder.onnx',
                         'client/vendor/markdown-it.min.js'):
                manifest={'format':1,'component':'linux','shell':'tauri','files':{k:v for k,v in files.items() if k!=name}}
                (root/'build-manifest.json').write_text(json.dumps(manifest),encoding='utf8')
                with self.subTest(name=name),self.assertRaises(ValueError):launcher.verify_files(root)
                self.assertEqual((root/name).read_bytes(),('fictif:'+name).encode())

    def test_valid_package_and_changed_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);files=self.make_package(root)
            (root/'build-manifest.json').write_text(json.dumps({'format':1,'component':'linux','shell':'tauri','files':files}),encoding='utf8')
            launcher.verify_files(root)
            target=root/'client/draft_store.py';target.write_bytes(b'change fictif')
            with self.assertRaises(ValueError):launcher.verify_files(root)
            self.assertEqual(target.read_bytes(),b'change fictif')

    def test_invalid_manifest_and_noncanonical_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);files=self.make_package(root)
            base={'format':1,'component':'linux','shell':'tauri','files':files}
            invalid=[{**base,'format':True},{**base,'shell':'unknown'},
                     {**base,'files':{**files,'client/../client/other.py':'0'*64}},
                     {**base,'files':{**files,'client//other.py':'0'*64}},
                     {**base,'files':{**files,'client/client.py':'invalid'}}]
            for manifest in invalid:
                (root/'build-manifest.json').write_text(json.dumps(manifest),encoding='utf8')
                with self.subTest(manifest=manifest),self.assertRaises(ValueError):launcher.verify_files(root)

    def test_symlinked_parent_is_rejected_even_inside_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);files=self.make_package(root)
            (root/'build-manifest.json').write_text(json.dumps({'format':1,'component':'linux','shell':'tauri','files':files}),encoding='utf8')
            (root/'client').rename(root/'client-original')
            try:(root/'client').symlink_to(root/'client-original',target_is_directory=True)
            except (OSError,NotImplementedError):self.skipTest('Création de lien symbolique indisponible sur ce poste.')
            with self.assertRaisesRegex(ValueError,'Lien inattendu'):launcher.verify_files(root)
            self.assertTrue((root/'client').is_symlink())
            self.assertTrue((root/'client-original/client.py').is_file())


class TauriOnlyTests(unittest.TestCase):
    def test_shortcut_keeps_previous_target_if_replacement_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            shortcut = Path(directory) / 'kiara.desktop'
            shortcut.write_text('Exec=previous', encoding='utf-8')
            with patch.object(Path, 'replace', side_effect=PermissionError('fixture')):
                with self.assertRaises(PermissionError):
                    installer.write_shortcut(shortcut, 'Exec=candidate')
            self.assertEqual(shortcut.read_text(encoding='utf-8'), 'Exec=previous')
            self.assertEqual(list(shortcut.parent.iterdir()), [shortcut])
            installer.write_shortcut(shortcut, 'Exec=candidate')
            self.assertEqual(shortcut.read_text(encoding='utf-8'), 'Exec=candidate')

    def test_incomplete_or_old_package_is_rejected_before_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'build-manifest.json').write_text(json.dumps({'architecture':'amd64'}),encoding='utf8')
            with patch.object(installer,'__file__',str(root/'installer.py')), \
                 patch.object(installer.sys,'platform','linux'),patch.object(installer.sys,'version_info',(3,12)), \
                 patch.object(installer.os,'geteuid',return_value=1000,create=True), \
                 patch.object(installer.shutil,'which',return_value='/fake/parec'), \
                 patch.object(installer.venv.EnvBuilder,'create') as create:
                with self.assertRaisesRegex(SystemExit,'Tauri complet'):installer.main()
                create.assert_not_called()
            self.assertFalse((root/'.venv').exists())

    def test_requirements_have_no_removed_desktop_engine(self):
        lines=(ROOT/'requirements.txt').read_text(encoding='utf8').lower().splitlines()
        self.assertFalse(any('pyside' in line or 'pywebview' in line or 'proxy_tools' in line for line in lines))

    def test_lock_contains_the_exact_direct_dependencies_with_hashes(self):
        requirements = [line.strip().lower() for line in (ROOT/'requirements.txt').read_text(encoding='utf8').splitlines()
                        if line.strip() and not line.lstrip().startswith('#')]
        lock = (ROOT/'requirements.lock').read_text(encoding='utf8').lower().replace('\\\n', ' ')
        entries = [line.strip() for line in lock.splitlines() if line.strip() and not line.lstrip().startswith('#')]
        for requirement in requirements:
            matching = [line for line in entries if line.startswith(requirement+' ')]
            self.assertEqual(len(matching), 1, requirement)
            self.assertRegex(matching[0], r'--hash=sha256:[0-9a-f]{64}')
        for line in entries:
            self.assertRegex(line, r'^[a-z0-9_.-]+==[a-z0-9_.-]+\s+--hash=sha256:[0-9a-f]{64}')

    @unittest.skipUnless(sys.platform.startswith('linux'),'Shell Linux requis')
    def test_start_dispatches_only_to_tauri_or_headless_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);shutil.copyfile(ROOT/'start.sh',root/'start.sh')
            (root/'.venv/bin').mkdir(parents=True)
            (root/'.venv/bin/python').write_text('#!/bin/sh\nprintf "python:%s\\n" "$*"\n',encoding='utf8')
            (root/'start-tauri.sh').write_text('#!/bin/sh\nprintf "tauri:%s\\n" "$*"\n',encoding='utf8')
            for executable in (root/'start.sh',root/'start-tauri.sh',root/'.venv/bin/python'):executable.chmod(0o755)
            def run(*args):return subprocess.check_output([str(root/'start.sh'),*args],text=True).strip()
            self.assertEqual(run('--profile','fiction'),'tauri:--profile fiction')
            self.assertIn('linux_launch.py --self-test',run('--self-test'))
            self.assertIn('linux_launch.py --audio-self-test',run('--audio-self-test'))


if __name__=='__main__':unittest.main()
