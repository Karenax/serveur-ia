import sys,json,subprocess,tempfile
from pathlib import Path
sys.path.insert(0,'lanceur')
from hermes_service import installation,child_environment
runtime=installation();code=r'''
import json,os,contextlib,io
from pathlib import Path
from tests.fakes.fake_llm_provider import FakeLLMServer,Text,write_hermes_home
from tests.e2e.core.history._helpers import OFFLINE_CONFIG,NO_BACKGROUND_REVIEW
from run_agent import AIAgent
with FakeLLMServer([Text('OK')]*10) as srv:
 write_hermes_home(Path(os.environ['HERMES_HOME']),srv.base_url,extra_config=OFFLINE_CONFIG+NO_BACKGROUND_REVIEW)
 reports=[]
 for model in ('fred-123456abcdef/gpt-6-luna','fred-123456abcdef/nvidia-nemotron-3-ultra-550b-a55b-free','fred-123456abcdef/qwen3.8-flash-next-iq4-xs'):
  agent=AIAgent(provider='custom',base_url=srv.base_url,api_key='sk-fixture',model=model,quiet_mode=True,enabled_toolsets=[],skip_memory=True,skip_background_review=True,skip_context_files=True,max_iterations=1,max_tokens=64,reasoning_config={'enabled':True,'effort':'low'})
  try:result=agent.run_conversation('Réponds OK.',conversation_history=[],task_id='test')
  finally:agent.close()
  assert srv.requests, result
  request=srv.requests[-1]['body']
  reports.append({'model':model,'body':request})
 print('FRED_CAPTURE='+json.dumps(reports))
'''
with tempfile.TemporaryDirectory(prefix='fred-hermes-wire-') as d:
 result=subprocess.run([str(runtime['python']),'-c',code],env=child_environment(d,runtime),cwd=runtime['source'],capture_output=True,text=True,encoding='utf-8',timeout=55)
 if result.returncode:print(result.stderr[-4000:]);raise SystemExit(1)
 line=next(line for line in result.stdout.splitlines() if line.startswith('FRED_CAPTURE='))
 rows=json.loads(line.split('=',1)[1]);Path('maintenance/2026-10-21-hermes-cloud/requetes-hermes.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 for row in rows:print(json.dumps({'model':row['model'],'keys':list(row['body']),'controls':{k:v for k,v in row['body'].items() if k not in ('messages','tools')}}))
