import json,sys,urllib.error,subprocess,tempfile,threading,secrets
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=['lanceur','client-qwen']
from releases import profile
from client import Remote,serve_local
import client
from connection_settings import HTTPS_ENDPOINT
from hermes_service import installation,child_environment
from hermes_catalogue import catalogue
from app_integrations import hermes_text
home=Path('lanceur');records=json.loads((home/'acces-distants.json').read_text())['clients']
p=next(home/'clients'/(r['id']+'.exe') for r in records if not r['revoked'] and (home/'clients'/(r['id']+'.exe')).is_file())
remote=Remote(profile(p),endpoint=HTTPS_ENDPOINT);runtime=installation()
reports=[]
try:
 assert remote.check()['connected']
 exposed,mapping=catalogue(remote.models_catalogue)
 with tempfile.TemporaryDirectory(prefix='fred-real-hermes-') as scratch:
  key=secrets.token_urlsafe(32)
  with patch.object(client,'settings_path',return_value=Path(scratch)/'settings.dpapi'):server=serve_local(remote,key,0)
  threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   url=f'http://127.0.0.1:{server.server_port}/hermes/v1'
   code=r'''
import json,sys,contextlib,io
from run_agent import AIAgent
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
 agent=AIAgent(provider='custom',base_url=sys.argv[1],api_key=sys.argv[2],model=sys.argv[3],quiet_mode=True,enabled_toolsets=[],skip_memory=True,skip_background_review=True,skip_context_files=True,max_iterations=1,max_tokens=64,reasoning_config={'enabled':True,'effort':sys.argv[4]})
 try:result=agent.run_conversation('Réponds uniquement OK.',conversation_history=[],task_id='fixture')
 finally:agent.close()
print(json.dumps({'completed':result.get('completed'),'failed':result.get('failed'),'final_response':str(result.get('final_response'))[:500]}))
'''
   for row in exposed['data']:
    if not mapping[row['id']].startswith('fred-model-'):continue
    with tempfile.TemporaryDirectory(prefix='fred-native-profile-') as child:
     Path(child,'config.yaml').write_text(hermes_text('',url,key,row['id'],exposed)+'\nupdates: {check: false}\nmodels_dev: {url: http://127.0.0.1:9/api.json}\n',encoding='utf-8')
     effort='medium' if 'nemotron' in row['id'] else 'low'
     result=subprocess.run([str(runtime['python']),'-c',code,url,key,row['id'],effort],env=child_environment(child,runtime),cwd=runtime['source'],capture_output=True,text=True,encoding='utf-8',timeout=120)
     if result.returncode:report={'model':row.get('name'),'error':result.stderr[-1000:]}
     else:report={'model':row.get('name'),**json.loads(result.stdout)}
     reports.append(report);print(json.dumps(report),flush=True)
  finally:server.shutdown();server.server_close()
finally:remote.close()
Path('maintenance/2026-10-21-hermes-cloud/natif-reel.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
