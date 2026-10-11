"""Verify rich drafts use encrypted settings and invalid updates are atomic."""
import importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'client'))
spec=importlib.util.spec_from_file_location('prototype_client',ROOT/'client/client.py')
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)

class PreferencesTests(unittest.TestCase):
    def test_encrypted_roundtrip_and_invalid_updates_preserve_document(self):
        profile={'url':'wireguard://10.77.0.1:8766','token':'isolated-richtext-fixture'}
        document={'version':1,'source_html':'<p style="color:red;font-family:Georgia">Bonjours</p>',
                  'result_html':'<p style="color:red;font-family:Georgia">Bonjour</p>','result_text':'Bonjour'}
        with tempfile.TemporaryDirectory(dir=ROOT) as directory,patch.dict(os.environ,{'LOCALAPPDATA':directory}):
            client.save_preferences(profile,{'corrector_text':'Bonjours','corrector_document':document})
            path=client.settings_path(profile);before=path.read_bytes()
            self.assertNotIn(b'Georgia',before);self.assertNotIn(b'Bonjours',before)
            self.assertEqual(client.client_settings(profile)['preferences']['corrector_document'],document)
            invalid=[None,{'version':True,'source_html':'','result_html':'','result_text':''},
                     {**document,'extra':True},{**document,'source_html':None},
                     {**document,'result_text':'x'*100001},
                     {**document,'source_html':'x'*750001},
                     {**document,'source_html':'x'*600000,'result_html':'x'*600000}]
            for value in invalid:
                with self.subTest(value_type=type(value).__name__):
                    with self.assertRaises(ValueError):client.save_preferences(profile,{'corrector_document':value})
                    self.assertEqual(path.read_bytes(),before)

if __name__=='__main__':unittest.main(verbosity=2)
