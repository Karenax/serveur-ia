"""Exercise Hermes' installed catalogue, OpenAI client and desktop name formatter."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'client-qwen'),str(ROOT/'lanceur')]
from test_model_catalogue import ModelCatalogueTests
from hermes_service import installation,child_environment
from app_integrations import hermes_text
from hermes_catalogue import catalogue

case=ModelCatalogueTests();case.setUp()
try:
    url=case.loopback()+'/hermes/v1'
    case.remote.check()
    exposed,mapping=catalogue(case.remote.models_catalogue)
    alias=exposed['data'][0]['id']
    base=Path(case.temp.name);config=base/'config.yaml'
    config.write_text(hermes_text('',url,'fixture-loopback-key',alias,exposed),encoding='utf-8')
    runtime=installation();env=child_environment(base,runtime)
    env['PYTHONPATH']=str(runtime['source'])
    code='''
import json,sys,yaml
from unittest.mock import patch
from hermes_cli.model_switch import list_authenticated_providers,switch_model
from openai import OpenAI
config=yaml.safe_load(open(sys.argv[1],encoding='utf-8'))
entry=config['providers']['serveur-fred']
with patch('agent.models_dev.fetch_models_dev',return_value={}), patch('hermes_cli.providers.HERMES_OVERLAYS',{}):
    providers=list_authenticated_providers(current_provider='serveur-fred',user_providers=config['providers'],custom_providers=[],probe_custom_providers=False,non_blocking_catalogs=True)
row=next(p for p in providers if p['slug']=='serveur-fred')
assert row['models']==list(entry['models']),row
with patch('hermes_cli.models_validate.validate_requested_model',return_value={'accepted':True,'persist':False,'recognized':True,'message':None}):
    switched=switch_model(raw_input=entry['default_model'],current_provider='serveur-fred',current_model='',explicit_provider='serveur-fred',user_providers=config['providers'],custom_providers=[])
assert switched.success and switched.new_model==entry['default_model'],switched
api=OpenAI(base_url=entry['api'],api_key=entry['api_key'])
assert [m.id for m in api.models.list()]==row['models']
answer=api.chat.completions.create(model=entry['default_model'],messages=[{'role':'user','content':'Fixture.'}])
assert answer.choices[0].message.content=='Réponse cloud.'
print(json.dumps({'hermes_catalogue':True,'hermes_model_switch':True,'openai_sdk_round_trip':True,'models':row['models']}))
'''
    result=subprocess.run([str(runtime['python']),'-c',code,str(config)],cwd=runtime['source'],env=env,
                          capture_output=True,text=True,encoding='utf-8',timeout=50)
    assert result.returncode==0,result.stderr[-4000:]
    native=json.loads(result.stdout.strip().splitlines()[-1])
    import os
    desktop=Path(os.environ['LOCALAPPDATA'])/'hermes/hermes-agent/apps/desktop'
    js=r"""
const fs=require('fs'),Module=require('module'),path=require('path');
const desktop=process.argv[1];
const file=path.join(desktop,'src/lib/model-status-label.ts');
const compiled=Module.stripTypeScriptTypes(fs.readFileSync(file,'utf8')).replace(/^export /gm,'');
const m=new Module(file);m._compile(compiled+'\nmodule.exports={displayModelName};',file);
const name=m.exports.displayModelName(process.argv[2]);
if(name!=='Modele Cloud')throw new Error(name);
process.stdout.write(JSON.stringify({desktop_formatter:true,displayed_name:name}));
"""
    formatted=subprocess.run(['node','-e',js,str(desktop),alias],capture_output=True,text=True,timeout=15)
    assert formatted.returncode==0,formatted.stderr
    report={**native,**json.loads(formatted.stdout),'runtime_commit':runtime['commit']}
    Path(__file__).with_name('validation-native.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
finally:
    case.tearDown()
