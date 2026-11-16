"""Component boundaries and stale-artifact refusal in deployment evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'maintenance'))
from build_manifest import source_names
from deployment_manifest import generate,REQUIRED_CHECKS,WINDOWS_CHECKS


class DeliveryContractsTests(unittest.TestCase):
    def test_server_package_uses_only_the_integrated_launcher(self):
        with tempfile.TemporaryDirectory() as folder:
            dist = Path(folder)
            assets = dist / 'assets'
            assets.mkdir()
            for name in ('index.html', 'assets/index.js', 'assets/index.css'):
                (dist / name).write_text('fixture', encoding='utf-8')
            server = set(source_names('server', dist))
        self.assertIn('Start-Interface-Qwen.ps1', server)
        self.assertIn('lanceur/agent_service.py', server)
        self.assertIn('agent/scripts/agent_backup.py', server)
        self.assertNotIn('agent/scripts/agent_runtime.py', server)
        self.assertNotIn('agent/backend/app/static/index.html', server)

    def test_component_source_lists_do_not_inherit_server_implementation(self):
        windows=list(source_names('windows'));android=list(source_names('android'))
        self.assertTrue(windows);self.assertTrue(android)
        self.assertFalse(any(name.startswith('lanceur/') for name in windows+android))
        self.assertIn('shared/kiara_shared/version.py',windows)
        self.assertIn('agent/extensions/thunderbird-agent/manifest.json',windows)
        self.assertNotIn('agent/extensions/thunderbird-agent/core.test.cjs',windows)
        self.assertFalse(any(name.startswith('client-qwen/') and name.endswith('.py') for name in android))

    def test_manifest_rejects_replaced_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);binary=directory/'client.exe';binary.write_bytes(b'new')
            manifest=directory/'build-manifest.json'
            manifest.write_text(json.dumps({'version':2,'component':'windows','source_commit':'a'*40,
                'source_files':{},'artifact':{'name':binary.name,'bytes':3,'sha256':hashlib.sha256(b'old').hexdigest()}}))
            validation=directory/'validation.json';validation.write_text(json.dumps({'passed':True,
                'results':[{'check':name,'passed':True} for name in REQUIRED_CHECKS]}))
            with self.assertRaisesRegex(ValueError,'Artifact no longer matches'):generate([manifest],validation)

    def test_windows_deployment_requires_both_components_and_windows_ui_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder)
            manifests=[]
            for component in ('server', 'windows'):
                binary=directory/component
                binary.write_bytes(b'fixture')
                manifest=directory/f'{component}.json'
                manifest.write_text(json.dumps({'version':2,'component':component,'source_commit':'a'*40,
                    'source_files':{},'artifact':{'name':binary.name,'bytes':7,'sha256':hashlib.sha256(b'fixture').hexdigest()}}))
                manifests.append(manifest)
            validation=directory/'validation.json'
            def write_evidence(checks):
                validation.write_text(json.dumps({'passed':True,'results':[{'check':name,'passed':True} for name in checks]}))
            write_evidence(WINDOWS_CHECKS-{'ui-windows'})
            with self.assertRaisesRegex(ValueError,'ui-windows'):
                generate(manifests,validation,scope='windows')
            write_evidence(WINDOWS_CHECKS)
            self.assertEqual(generate(manifests,validation,scope='windows')['scope'],'windows')
            with self.assertRaisesRegex(ValueError,'requires the server and Windows manifests'):
                generate(manifests[1:],validation,scope='windows')
            with self.assertRaisesRegex(ValueError,'android-lint'):
                generate(manifests,validation)


if __name__=='__main__':unittest.main()
