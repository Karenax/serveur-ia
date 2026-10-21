"""Configuration integration tests; never touch installed applications."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'client-qwen'))
import app_integrations as integrations
import yaml

URL='http://127.0.0.1:8087/v1'
KEY='local-test-key-'+'x'*32
MODEL='Qwen/test:latest'
PROVIDER=integrations.PROVIDER


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fred-integrations-test-')
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.apps={name:{'installed':True,'config_path':str(self.home/name/filename)} for name,filename in [('opencode','opencode.jsonc'),('hermes','config.yaml')]}

    def write(self,app,raw):
        path=Path(self.apps[app]['config_path']);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw.encode() if isinstance(raw,str) else raw);return path

    def install(self,app,**kwargs):
        return integrations.install(app,kwargs.get('url',URL),kwargs.get('key',KEY),kwargs.get('model',MODEL),self.apps)

    def test_opencode2_jsonc_preserves_settings_comments_and_exact_backup(self):
        source='''{
  // keep my defaults
  "model": "other/original",
  "providers": {
    "other": {"settings": {"baseURL": "http://example.test//v1"}}, // keep provider
  },
  "theme": "system", /* keep theme */
}
'''
        path=self.write('opencode',source)
        result=self.install('opencode');updated=path.read_text();value,_=integrations.jsonc(updated)
        self.assertEqual(Path(result['backup']).read_bytes(),source.encode())
        self.assertIn('// keep my defaults',updated);self.assertIn('// keep provider',updated);self.assertIn('/* keep theme */',updated)
        self.assertEqual(value['model'],'other/original');self.assertEqual(value['theme'],'system')
        self.assertEqual(value['providers']['other'],{'settings':{'baseURL':'http://example.test//v1'}})
        entry=value['providers'][PROVIDER]
        self.assertEqual(entry['package'],'@opencode/ai/providers/openai-compatible')
        self.assertEqual(entry['settings'],{'baseURL':URL,'apiKey':KEY})
        self.assertTrue(entry['models'][MODEL]['capabilities']['tools'])
        self.assertIs(entry['models'][MODEL]['disabled'],False)
        before=path.read_bytes();again=self.install('opencode')
        self.assertEqual(before,path.read_bytes());self.assertIsNone(again['backup'])
        changed=self.install('opencode',url='http://127.0.0.1:8088/v1',model='Second')
        value,_=integrations.jsonc(path.read_text())
        self.assertEqual(set(value['providers'][PROVIDER]['models']),{MODEL,'Second'})
        self.assertEqual(Path(changed['backup']).read_bytes(),before)

    def test_opencode_v1_and_existing_model_options(self):
        source={'model':'other/original','provider':{PROVIDER:{'models':{MODEL:{'name':'previous','limit':{'context':32768}}},'options':{'timeout':60000}}}}
        path=self.write('opencode',json.dumps(source));self.install('opencode')
        value=json.loads(path.read_text());entry=value['provider'][PROVIDER]
        self.assertNotIn('providers',value);self.assertEqual(value['model'],source['model'])
        self.assertEqual(entry['npm'],'@ai-sdk/openai-compatible')
        self.assertEqual(entry['options']['baseURL'],URL);self.assertEqual(entry['options']['timeout'],60000)
        self.assertEqual(entry['models'][MODEL]['limit'],{'context':32768})

    def test_opencode_readable_names_refresh_existing_models_without_importing_catalogue(self):
        for section in ('providers','provider'):
            with self.subTest(section=section):
                selected='fred-model-'+'a'*24;previous='fred-model-'+'b'*24
                source={section:{PROVIDER:{'models':{
                    selected:{'name':selected,'limit':{'context':64000}},
                    previous:{'name':previous,'disabled':True},
                    'custom':{'name':'Mon modèle'}}},'other':{'name':'Conservé'}},'model':'other/original'}
                path=self.write('opencode',json.dumps(source))
                catalogue={'data':[{'id':selected,'name':'gpt-6-luna','label':'GPT-6 Luna'},
                                   {'id':previous,'name':'gpt-6-astra','label':'GPT-6 Astra'},
                                   {'id':'not-added','name':'Autre modèle'},
                                   {'id':'google/embeddinggemma-2','capabilities':{'embedding':True}}]}
                result=integrations.install('opencode',URL,KEY,selected,self.apps,catalogue=catalogue)
                value=json.loads(path.read_text(encoding='utf-8'));models=value[section][PROVIDER]['models']
                self.assertEqual(set(models),{selected,previous,'custom'})
                self.assertEqual(models[selected]['name'],'GPT-6 Luna')
                self.assertEqual(models[previous]['name'],'GPT-6 Astra');self.assertTrue(models[previous]['disabled'])
                self.assertEqual(models[selected]['limit'],{'context':64000})
                self.assertEqual(models['custom']['name'],'Mon modèle')
                self.assertEqual(value[section]['other'],source[section]['other']);self.assertEqual(value['model'],'other/original')
                self.assertIn('GPT-6 Luna',result['message']);self.assertEqual(result['model'],selected)
                self.assertIsNone(integrations.install('opencode',URL,KEY,selected,self.apps,catalogue=catalogue)['backup'])

    def test_opencode_rejects_embedding_or_unavailable_selection_before_writing(self):
        for row in ({'id':MODEL,'capabilities':{'embedding':True}},{'id':MODEL,'available':False}):
            path=self.write('opencode','{}')
            with self.assertRaises(ValueError):
                integrations.install('opencode',URL,KEY,MODEL,self.apps,catalogue={'data':[row]})
            self.assertEqual(path.read_bytes(),b'{}')

    def test_new_config_and_bom_are_supported(self):
        for app in self.apps:
            result=self.install(app);self.assertIsNone(result['backup'])
            self.assertTrue(Path(result['config_path']).exists())
        path=self.write('opencode',b'\xef\xbb\xbf{}\r\n');self.install('opencode')
        self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbf'))

    def test_hermes_compact_yaml_and_empty_provider_lists(self):
        for source in ('{}\n','model: {default: original}\nproviders: {} # keep note\n',
                       'model: {default: original}\ncustom_providers: []\n',
                       '{model: {default: original}, providers: {other: {api: https://example.test}}}\n'):
            with self.subTest(source=source):
                path=self.write('hermes',source);self.install('hermes')
                original=yaml.safe_load(source);value=yaml.safe_load(path.read_text())
                if 'model' in original:self.assertEqual(value['model'],original['model'])
                if '# keep note' in source:self.assertIn('# keep note',path.read_text())
                self.assertIsNone(self.install('hermes')['backup'])

    def test_hermes_preserves_other_providers_comments_and_model(self):
        source='''# My settings
model:
  provider: openrouter
  default: original/model
providers:
  other: # custom service
    api: https://example.test/v1 # my endpoint
    api_key: other-test-secret
# keep display preferences
display:
  theme: dark
'''
        path=self.write('hermes',source);result=self.install('hermes');updated=path.read_text()
        self.assertEqual(Path(result['backup']).read_bytes(),source.encode())
        self.assertIn(source[:source.index('# keep display')],updated)
        self.assertIn(source[source.index('# keep display'):],updated)
        value=yaml.safe_load(updated);entry=value['providers'][PROVIDER]
        self.assertEqual(value['model'],{'provider':'openrouter','default':'original/model'})
        self.assertEqual(entry['api'],URL);self.assertEqual(entry['api_key'],KEY)
        self.assertEqual(entry['transport'],'chat_completions');self.assertIn(MODEL,entry['models'])
        before=path.read_bytes();self.assertIsNone(self.install('hermes')['backup']);self.assertEqual(before,path.read_bytes())
        self.install('hermes',model='Second');value=yaml.safe_load(path.read_text())
        self.assertEqual(set(value['providers'][PROVIDER]['models']),{MODEL,'Second'})
        self.assertEqual(value['model']['default'],'original/model')
        self.assertIn('other: # custom service',path.read_text())

    def test_legacy_hermes_both_sequence_indentation_styles(self):
        for indent in ('','  '):
            with self.subTest(indent=indent):
                source='model: {default: original}\ncustom_providers:\n'+indent+'- name: other\n'+indent+'  base_url: https://example.test/v1 # keep endpoint\ndisplay: {theme: dark}\n'
                path=self.write('hermes',source);self.install('hermes');updated=path.read_text()
                self.assertIn('base_url: https://example.test/v1 # keep endpoint',updated)
                value=yaml.safe_load(updated);entry=value['custom_providers'][-1]
                self.assertEqual(len(value['custom_providers']),2);self.assertEqual(entry['name'],PROVIDER)
                self.assertEqual(entry['base_url'],URL);self.assertEqual(entry['model'],MODEL)
                self.assertEqual(value['model'],{'default':'original'})
                self.install('hermes',model='Second');value=yaml.safe_load(path.read_text())
                self.assertEqual(len(value['custom_providers']),2);self.assertIn('Second',value['custom_providers'][-1]['models'])

    def test_unreadable_or_ambiguous_config_is_never_written(self):
        for app,sources in {'opencode':['{broken','{"providers":[],"model":"original"}','{"model":"first","model":"second"}'],
                            'hermes':['providers: [','model: first\nmodel: second','providers:\n  serveur-fred: string','providers: &all\n  other: {}\ncopy: *all']}.items():
            for source in sources:
                with self.subTest(app=app,source=source):
                    path=self.write(app,source)
                    with self.assertRaises(ValueError):self.install(app)
                    self.assertEqual(path.read_bytes(),source.encode())
                    self.assertFalse(list(path.parent.glob('*.fred-backup-*')))

    def test_detection_uses_local_installs_and_environment_paths(self):
        empty=integrations.detect(self.home,{},lambda _:None)
        self.assertFalse(any(app['installed'] for app in empty.values()))
        local=self.home/'local';binary=local/'Programs/@opencodedesktop/OpenCode.exe';binary.parent.mkdir(parents=True);binary.touch()
        hermes=local/'hermes/bin/hermes.exe';hermes.parent.mkdir(parents=True);hermes.touch()
        found=integrations.detect(self.home,{'LOCALAPPDATA':str(local)},lambda _:None)
        self.assertTrue(all(app['installed'] for app in found.values()))
        self.assertEqual(found['hermes']['config_path'],str(local/'hermes/config.yaml'))
        custom=self.home/'custom';custom.mkdir();(custom/'config.yaml').write_text('model: {}')
        jsonc=self.home/'.config/opencode/opencode.jsonc';jsonc.parent.mkdir(parents=True);jsonc.write_text('{}')
        found=integrations.detect(self.home,{'HERMES_HOME':str(custom)},lambda _:None)
        self.assertEqual(found['opencode']['config_path'],str(jsonc));self.assertEqual(found['hermes']['config_path'],str(custom/'config.yaml'))
        explicit=self.home/'explicit.json';explicit.write_text('{}')
        found=integrations.detect(self.home,{'OPENCODE_CONFIG':str(explicit)},lambda _:None)
        self.assertEqual(found['opencode']['config_path'],str(explicit))

    def test_validation_or_absent_app_never_creates_configuration(self):
        for arguments in [{'app':'unknown'},{'url':'https://remote.example/v1'},{'url':'http://127.0.0.1:8081/v1?secret=x'},{'model':'bad\nmodel'},{'key':'too-short'}]:
            with self.subTest(arguments=arguments),self.assertRaises(ValueError):
                self.install(arguments.get('app','opencode'),**{k:v for k,v in arguments.items() if k!='app'})
        self.apps['opencode']['installed']=False
        with self.assertRaises(ValueError):self.install('opencode')
        self.assertFalse(Path(self.apps['opencode']['config_path']).exists())

    def test_hermes_readable_catalogue_replaces_old_ids_and_embeddings(self):
        source={'model':{'provider':'other','default':'original'},'providers':{
            PROVIDER:{'models':{'fred-model-old':{},'google/embeddinggemma-2':{}},'timeout':123}}}
        path=self.write('hermes',yaml.safe_dump(source))
        catalogue={'data':[{'id':'fred-model-old','name':'GPT-6 Luna','available':True},
                           {'id':'fred-qwen','name':'Qwen local','available':True},
                           {'id':'gone','name':'Offline','available':False},
                           {'id':'google/embeddinggemma-2','capabilities':{'embedding':True}}]}
        result=integrations.install('hermes',URL,KEY,'fred-model-old',self.apps,catalogue=catalogue)
        value=yaml.safe_load(path.read_text());entry=value['providers'][PROVIDER]
        self.assertEqual(entry['api'],'http://127.0.0.1:8087/hermes/v1')
        self.assertEqual({key.rsplit('/',1)[-1] for key in entry['models']},{'gpt-6-luna','qwen-local'})
        self.assertEqual(entry['default_model'],result['model']);self.assertEqual(entry['timeout'],123)
        self.assertEqual(value['model'],source['model']);self.assertIn('activez l’interrupteur',result['message'])
        self.assertEqual(Path(result['backup']).read_text(),yaml.safe_dump(source))
        self.assertIsNone(integrations.install('hermes',URL,KEY,'fred-model-old',self.apps,catalogue=catalogue)['backup'])

    def test_opencode_jsonc_overrides_json_without_changing_the_lower_priority_file(self):
        directory=self.home/'.config/opencode';directory.mkdir(parents=True)
        lower=directory/'opencode.json';higher=directory/'opencode.jsonc'
        lower.write_text('{"model":"other/original","providers":{"other":{"name":"Keep me"}}}',encoding='utf-8')
        old=integrations.opencode_text('{\n// keep my note\n}', 'http://127.0.0.1:8088/v1','old-key-'+'y'*40,MODEL)
        higher.write_text(old,encoding='utf-8');lower_before=lower.read_bytes();higher_before=higher.read_bytes()
        apps=integrations.detect(self.home,{},lambda _:None)
        self.assertEqual(apps['opencode']['config_path'],str(higher))
        result=integrations.install('opencode',URL,KEY,MODEL,apps)
        self.assertEqual(lower.read_bytes(),lower_before)
        self.assertEqual(Path(result['backup']).read_bytes(),higher_before)
        self.assertIn('// keep my note',higher.read_text())
        value,_=integrations.jsonc(higher.read_text())
        self.assertEqual(value['providers'][PROVIDER]['settings'],{'baseURL':URL,'apiKey':KEY})
        self.assertIsNone(integrations.install('opencode',URL,KEY,MODEL,apps)['backup'])

    def test_opencode_explicit_config_wins_over_jsonc_and_new_config_stays_json(self):
        found=integrations.detect(self.home,{},lambda _:None)
        self.assertEqual(found['opencode']['config_path'],str(self.home/'.config/opencode/opencode.json'))
        directory=self.home/'custom';directory.mkdir()
        (directory/'opencode.json').write_text('{}');(directory/'opencode.jsonc').write_text('{}')
        env={'OPENCODE_CONFIG_DIR':str(directory)}
        self.assertEqual(integrations.detect(self.home,env,lambda _:None)['opencode']['config_path'],str(directory/'opencode.jsonc'))
        explicit=self.home/'explicit.json';explicit.write_text('{}')
        env['OPENCODE_CONFIG']=str(explicit)
        self.assertEqual(integrations.detect(self.home,env,lambda _:None)['opencode']['config_path'],str(explicit))


if __name__=='__main__':unittest.main()
