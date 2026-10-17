"""One model call for external OpenAI clients; never execute their tools on Fred.

Cloud transports reuse the installed Hermes adapters in an isolated interpreter.
Keys travel over stdin and remain on the server. Cloud SSE is buffered per call;
the gateway sends queue keepalives until the complete tool/text response arrives.
"""
import json
import subprocess
import threading
import time
import tempfile
from core import HIDDEN
from hermes_codex_compat import PATCH_SOURCE

WORKER = PATCH_SOURCE + r'''
import contextlib, io, json, logging, sys
logging.disable(logging.CRITICAL)
payload=json.load(sys.stdin)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
 from openai import OpenAI
 _fred_install_codex_headers()
 mode=payload['mode'];key=payload['key'];url=payload['url'];data=payload['data']
 model=data['model']
 if mode=='anthropic_messages':
  from agent.anthropic_adapter import build_anthropic_client
  from agent.auxiliary_client import AnthropicAuxiliaryClient
  native=build_anthropic_client(key,base_url=url,timeout=900)
  client=AnthropicAuxiliaryClient(native,model,key,url,is_oauth=key.startswith('sk-ant-oat'))
 else:
  client=OpenAI(api_key=key,base_url=url,timeout=900,max_retries=0)
  if mode=='codex_responses':
   from agent.auxiliary_client import CodexAuxiliaryClient
   client=CodexAuxiliaryClient(client,model)
 data['stream']=False
 data.pop('stream_options',None);data.pop('strata_mcp',None)
 if data.get('max_tokens')==-1:data.pop('max_tokens')
 extra={k:data.pop(k) for k in ('top_k','min_p','repetition_penalty','chat_template_kwargs') if k in data}
 if mode!='chat_completions':extra={}
 if mode!='chat_completions' and 'reasoning_effort' in data:
  effort=data.pop('reasoning_effort');extra['reasoning']={'enabled':effort!='none','effort':effort}
 if extra:data['extra_body']=extra
 try:
  result=client.chat.completions.create(**data)
  def field(obj,name,default=None):return obj.get(name,default) if isinstance(obj,dict) else getattr(obj,name,default)
  choices=[]
  for choice in result.choices:
   message=choice.message
   out={'role':'assistant','content':field(message,'content')}
   reason=field(message,'reasoning_content') or field(message,'reasoning')
   if reason:out['reasoning_content']=reason
   calls=field(message,'tool_calls')
   if calls:
    out['tool_calls']=[{'id':field(c,'id'),'type':'function','function':{'name':field(field(c,'function'),'name'),'arguments':field(field(c,'function'),'arguments')}} for c in calls]
   choices.append({'index':field(choice,'index',0),'message':out,'finish_reason':field(choice,'finish_reason') or ('tool_calls' if calls else 'stop')})
  usage=field(result,'usage')
  response={'object':'chat.completion','model':model,'choices':choices}
  if usage:response['usage']={k:field(usage,k,0) for k in ('prompt_tokens','completion_tokens','total_tokens')}
 finally:client.close()
print(json.dumps(response,ensure_ascii=False))
'''


def complete(models, owner, selection, data, valid, heartbeat=lambda: None):
    from hermes_service import installation, child_environment
    if not valid():raise ValueError('Demande annulée ou accès désactivé.')
    credential=models.credential(owner,selection)['access_token']
    runtime=getattr(models.source,'runtime',None) or installation()
    if not valid():raise ValueError('Demande annulée ou accès désactivé.')
    request=dict(data,model=selection['native_model'])
    payload={'mode':selection['api_mode'],'key':credential,'url':selection['base_url'],'data':request}
    temporary=tempfile.TemporaryDirectory(prefix='fred-external-api-')
    try:
        process=subprocess.Popen([str(runtime['python']),'-c',WORKER],cwd=runtime['source'],
            env=child_environment(temporary.name,runtime),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,creationflags=HIDDEN)
    except BaseException:
        temporary.cleanup();raise
    result={};done=threading.Event()
    def communicate():
        try:result['output']=process.communicate(json.dumps(payload).encode(),timeout=900)[0]
        except (OSError,subprocess.TimeoutExpired) as error:result['error']=error
        finally:done.set()
    thread=threading.Thread(target=communicate,daemon=True);thread.start()
    deadline=time.monotonic()+900;last_heartbeat=0
    try:
        while not done.wait(.2):
            if not valid() or time.monotonic()>deadline:raise ValueError('Demande annulée ou fournisseur indisponible.')
            if time.monotonic()-last_heartbeat>=5:heartbeat();last_heartbeat=time.monotonic()
        if not valid():raise ValueError('Demande annulée ou accès désactivé.')
        output=result.get('output',b'')
        if process.returncode or result.get('error') or len(output)>16*1024*1024:
            raise ValueError('Le fournisseur a refusé la demande API ou ne répond pas.')
        value=json.loads(output)
        value.update(id='chatcmpl-'+__import__('secrets').token_hex(16),created=int(time.time()),model=selection['id'])
        return value
    finally:
        if process.poll() is None:process.kill()
        thread.join(timeout=5)
        process.wait(timeout=5)
        temporary.cleanup()


def response_body(result, streaming):
    if not streaming:return json.dumps(result,ensure_ascii=False).encode()
    chunk=dict(result,object='chat.completion.chunk')
    chunk['choices']=[]
    for choice in result['choices']:
        delta=dict(choice['message'])
        if delta.get('tool_calls'):
            delta['tool_calls']=[dict(call,index=index) for index,call in enumerate(delta['tool_calls'])]
        chunk['choices'].append({'index':choice['index'],'delta':delta,'finish_reason':None})
    ending=dict(result,object='chat.completion.chunk',choices=[{'index':c['index'],'delta':{},'finish_reason':c['finish_reason']} for c in result['choices']])
    return ('data: '+json.dumps(chunk,ensure_ascii=False)+'\n\ndata: '+json.dumps(ending,ensure_ascii=False)+'\n\ndata: [DONE]\n\n').encode()
