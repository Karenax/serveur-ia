"""Validate client configuration merges and Windows credential handling."""
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import tomllib
import unittest

HERE = Path(__file__).resolve().parent


@unittest.skipUnless(os.name == 'nt', 'Windows DPAPI and PowerShell setup')
class SetupTests(unittest.TestCase):
    def run_script(self, script, *args, env=None):
        result = subprocess.run([shutil.which('powershell.exe'), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
            '-File', str(HERE/script), *map(str,args)], env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_profile_keeps_main_config_and_has_bounded_qwen_agents(self):
        with tempfile.TemporaryDirectory() as folder:
            main = Path(folder)/'config.toml'; main.write_text('model="original"\n',encoding='utf-8')
            self.run_script('Installer-Codex-Kiara.ps1', '-CodexDirectory',folder)
            self.assertEqual(main.read_text(encoding='utf-8'), 'model="original"\n')
            data=tomllib.loads((Path(folder)/'kiara.config.toml').read_text(encoding='utf-8'))
            self.assertEqual(data['model'],'fred-qwen'); self.assertEqual(data['agents']['default_subagent_model'],'fred-qwen')
            self.assertEqual(data['agents']['max_concurrent_threads_per_session'],3)
            self.assertTrue(Path(data['model_catalog_json']).is_file())
            self.assertEqual(data['model_providers']['kiara']['env_key'],'KIARA_API_KEY')

    def test_application_merge_is_idempotent_and_keeps_unrelated_settings(self):
        original='''model="original"
model_provider="openai"
approval_policy="on-request"
[agents]
enabled=true
default_subagent_model="old-model"
max_threads=12
[mcp_servers.example]
command="example"
args=["keep", "these"]
[model_providers.other]
name="Other"
base_url="https://example.invalid/v1"
'''
        with tempfile.TemporaryDirectory() as folder:
            main=Path(folder)/'config.toml'; main.write_text(original,encoding='utf-8')
            for _ in range(2):
                self.run_script('Installer-Codex-Kiara.ps1','-CodexDirectory',folder,'-Application')
                data=tomllib.loads(main.read_text(encoding='utf-8'))
                self.assertEqual(data['model_provider'],'openai')
                self.assertEqual(data['model'],'original')
                self.assertNotIn('model_catalog_json',data)
                self.assertEqual(data['agents'],tomllib.loads(original)['agents'])
                self.assertEqual(data['mcp_servers'],tomllib.loads(original)['mcp_servers'])
                self.assertEqual(data['model_providers']['other'],tomllib.loads(original)['model_providers']['other'])
                self.assertEqual(data['approval_policy'],'on-request')
                without_kiara=dict(data);without_kiara['model_providers']=dict(data['model_providers'])
                without_kiara['model_providers'].pop('kiara')
                self.assertEqual(without_kiara,tomllib.loads(original))
            self.assertTrue(list(Path(folder).glob('config.toml.before-kiara-*')))

    def test_multiline_user_catalogue_and_authentication_are_preserved(self):
        original='model="gpt-6.1-sol"\nmodel_provider="openai"\nmodel_catalog_json="my-catalog.json"\ncustom_text="""keep\n[agents]\nmodel_provider=\"kiara\"\n"""\n'
        with tempfile.TemporaryDirectory() as folder:
            main=Path(folder)/'config.toml';main.write_text(original,encoding='utf-8')
            auth=Path(folder)/'auth.json';auth.write_bytes(b'original private credentials')
            self.run_script('Installer-Codex-Kiara.ps1','-CodexDirectory',folder,'-Application')
            data=tomllib.loads(main.read_text(encoding='utf-8'))
            for key,value in tomllib.loads(original).items():self.assertEqual(data[key],value)
            self.assertTrue(main.read_text(encoding='utf-8').startswith(original))
            self.assertEqual(auth.read_bytes(),b'original private credentials')

    def test_no_repair_of_an_existing_user_default(self):
        with tempfile.TemporaryDirectory() as folder:
            main=Path(folder)/'config.toml'
            main.write_text('model="fred-qwen"\nmodel_provider="kiara"\n# BEGIN KIARA PROVIDER\n[model_providers.kiara]\nname="Old Kiara"\n# END KIARA PROVIDER\n',encoding='utf-8')
            self.run_script('Installer-Codex-Kiara.ps1','-CodexDirectory',folder,'-Application')
            data=tomllib.loads(main.read_text(encoding='utf-8'))
            self.assertEqual(data['model_provider'],'kiara')
            self.assertEqual(data['model'],'fred-qwen')

    def test_dpapi_helper_does_not_put_plaintext_in_files_or_config(self):
        token='qwen_' + secrets.token_hex(8) + '_' + secrets.token_urlsafe(32)
        with tempfile.TemporaryDirectory() as folder:
            self.run_script('Installer-Codex-Kiara.ps1','-CodexDirectory',folder,'-Application','-EnregistrerCle',env=dict(os.environ,KIARA_API_KEY=token))
            for path in Path(folder).iterdir(): self.assertNotIn(token.encode(),path.read_bytes())
            data=tomllib.loads((Path(folder)/'config.toml').read_text(encoding='utf-8'))
            provider=data['model_providers']['kiara']
            self.assertNotIn('env_key',provider); self.assertNotIn('requires_openai_auth',provider)
            self.assertEqual(provider['auth']['command'],'powershell.exe')
            result=subprocess.run([provider['auth']['command'],*provider['auth']['args']],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(result.stdout.strip(),token)


if __name__ == '__main__': unittest.main()
