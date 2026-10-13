"""Native MCP and local model requests bound to their admitted Hermes run."""
PATCH_SOURCE = r'''
def _fred_install_run_binding():
 import re,httpx
 from functools import wraps
 from agent.secret_scope import get_secret
 from tools.approval_context import _approval_session_key
 from urllib.parse import urlsplit
 from mcp import ClientSession,types
 from gateway.platforms import api_server_runs,api_server
 original_history=api_server_runs._resolve_conversation_history
 if not getattr(original_history,'_fred_multimodal',False):
  @wraps(original_history)
  def history(adapter,body,raw_input,**kwargs):
   result=original_history(adapter,body,raw_input,**kwargs)
   raw=body.get('conversation_history')
   if raw and result[3] is None:
    try:
     normalized=[{'role':str(m['role']),'content':api_server._normalize_multimodal_content(m['content'])} for m in raw]
    except ValueError:
     return [],result[1],None,api_server_runs._json_error(kwargs['_openai_error'],'Invalid historical attachment',status=400)
    return normalized,result[1],result[2],None
   return result
  history._fred_multimodal=True;api_server_runs._resolve_conversation_history=history
 def identity():
  value=_approval_session_key.get()
  if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',value):raise ValueError('Fred run binding unavailable')
  return value
 def bind_http(request):
  target=get_secret('FRED_PROVIDER_URL','');key=get_secret('FRED_INFERENCE_KEY','')
  if not target or not key:return
  route=urlsplit(target);url=urlsplit(str(request.url))
  if (route.scheme,route.hostname,route.port)!=(url.scheme,url.hostname,url.port):return
  if url.path!='/v1/chat/completions':return
  if request.headers.get('Authorization')!='Bearer '+key:return
  request.headers['X-Fred-Run']=identity()
 original=ClientSession.call_tool
 if not getattr(original,'_fred_run_binding',False):
  @wraps(original)
  async def call_tool(session,name,*args,**kwargs):
   if name.startswith('fred_') and get_secret('FRED_WEB_URL',''):
    meta=kwargs.get('meta')
    meta=meta.model_dump(exclude_none=True) if hasattr(meta,'model_dump') else dict(meta or {})
    meta['fred_run_id']=identity();kwargs['meta']=types.RequestParamsMeta(**meta)
   return await original(session,name,*args,**kwargs)
  call_tool._fred_run_binding=True;ClientSession.call_tool=call_tool
 original_send=httpx.Client.send
 if not getattr(original_send,'_fred_run_binding',False):
  @wraps(original_send)
  def send(client,request,*args,**kwargs):
   bind_http(request);return original_send(client,request,*args,**kwargs)
  send._fred_run_binding=True;httpx.Client.send=send
 original_async=httpx.AsyncClient.send
 if not getattr(original_async,'_fred_run_binding',False):
  @wraps(original_async)
  async def send_async(client,request,*args,**kwargs):
   bind_http(request);return await original_async(client,request,*args,**kwargs)
  send_async._fred_run_binding=True;httpx.AsyncClient.send=send_async
'''
