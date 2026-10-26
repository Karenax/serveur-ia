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
from deployment_manifest import generate,REQUIRED_CHECKS


class DeliveryContractsTests(unittest.TestCase):
    def test_component_source_lists_do_not_inherit_server_implementation(self):
        windows=list(source_names('windows'));android=list(source_names('android'))
        self.assertTrue(windows);self.assertTrue(android)
        self.assertFalse(any(name.startswith('lanceur/') for name in windows+android))
        self.assertIn('shared/kiara_shared/version.py',windows)
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


if __name__=='__main__':unittest.main()
