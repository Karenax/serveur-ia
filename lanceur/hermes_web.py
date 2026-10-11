"""The installed Hermes web tools, centrally executed for an authorized Fred run.

Personal web credentials/configuration stay in the original Hermes profile. The
Fred gateway only receives its own tool token and calls the private Fred broker;
it never inherits another profile's API keys or gains terminal/browser tools.
"""
from __future__ import annotations

import ipaddress
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.parse import parse_qsl, unquote, urlsplit

from core import HIDDEN


NAMES = {'web_search', 'web_extract'}
MAX_BYTES = 400_000
ERROR = 'Recherche web Hermes indisponible. Vérifiez la connexion web dans Hermes sur le serveur.'
_PRIVATE_QUERY = {'access_token', 'api_key', 'apikey', 'auth_token', 'authorization', 'client_secret',
                  'credential', 'credentials', 'jwt', 'password', 'passwd', 'secret', 'session_id',
                  'signature', 'token', 'awsaccesskeyid', 'x_amz_security_token', 'x_amz_signature',
                  'x-amz-signature', 'x-amz-security-token'}


def public_url(value):
    """A public HTTP URL without credentials; native Hermes also validates DNS/connect/redirects."""
    if not isinstance(value, str) or not value or len(value) > 4000 or any(ord(c) < 32 for c in value):
        return False
    try:
        parsed = urlsplit(value)
        hostname = (parsed.hostname or '').lower().rstrip('.')
        if (parsed.scheme not in {'https', 'http'} or not hostname or parsed.username or parsed.password
                or parsed.port not in {None, 80, 443}
                or hostname in {'localhost', 'metadata.google.internal', 'metadata.goog'}
                or hostname.endswith(('.localhost', '.local', '.internal'))
                or any(unquote(key).lower() in _PRIVATE_QUERY and val for key, val in parse_qsl(parsed.query))):
            return False
        try:
            if not ipaddress.ip_address(hostname).is_global:
                return False
        except ValueError:
            if '.' not in hostname:
                return False
        return True
    except (ValueError, UnicodeError):
        return False


def arguments_for(name, value):
    if name not in NAMES or not isinstance(value, dict):
        raise ValueError('Outil web Hermes invalide.')
    if name == 'web_search':
        if set(value) - {'query', 'limit'}:
            raise ValueError('Paramètres de recherche Hermes invalides.')
        query, limit = value.get('query'), value.get('limit', 5)
        if (not isinstance(query, str) or not query.strip() or len(query) > 2000 or '\x00' in query
                or type(limit) is not int or not 1 <= limit <= 10):
            raise ValueError('Recherche Hermes hors limites.')
        return {'query': query.strip(), 'limit': limit}
    if set(value) - {'urls', 'char_limit'}:
        raise ValueError('Paramètres de lecture Hermes invalides.')
    urls, chars = value.get('urls'), value.get('char_limit', 15000)
    if (not isinstance(urls, list) or not 1 <= len(urls) <= 5
            or type(chars) is not int or not 2000 <= chars <= 50000):
        raise ValueError('Lecture web Hermes hors limites.')
    normalized = []
    for item in urls:
        url = (item.get('url') or item.get('href')) if isinstance(item, dict) else item
        if not public_url(url):
            raise ValueError('Seules les URLs web publiques sans identifiants sont autorisées.')
        normalized.append(url)
    return {'urls': normalized, 'char_limit': chars}


def _string(value, maximum):
    return value[:maximum] if isinstance(value, str) else ''


def clean_result(name, value, arguments):
    """Whitelist native result fields, drop diagnostic exceptions and private host paths."""
    if not isinstance(value, dict) or value.get('success') is False or value.get('error'):
        return {'success': False, 'error': ERROR}
    if name == 'web_search':
        data = value.get('data')
        rows = data.get('web') if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return {'success': False, 'error': ERROR}
        items = []
        for row in rows[:arguments['limit']]:
            if isinstance(row, dict) and public_url(row.get('url')):
                items.append({'url': row['url'], 'title': _string(row.get('title'), 500),
                    'description': _string(row.get('description'), 3000), 'position': len(items) + 1})
        return {'success': True, 'data': {'web': items}}
    rows = value.get('results')
    if not isinstance(rows, list):
        return {'success': False, 'error': ERROR}
    items = []
    for row in rows[:5]:
        if not isinstance(row, dict) or not public_url(row.get('url')):
            continue
        error = 'Page inaccessible ou refusée par Hermes.' if row.get('error') else None
        item = {'url': row['url'], 'title': _string(row.get('title'), 500),
            'content': '' if error else _string(row.get('content'), arguments['char_limit'] + 1000), 'error': error}
        if row.get('truncated') is True:
            item['truncated'] = True
        if row.get('blocked_by_policy'):
            item['blocked_by_policy'] = True
        items.append(item)
    return {'results': items}


_NATIVE = r'''
import asyncio, contextlib, copy, io, json, logging, os, sys
data=json.load(sys.stdin)
logging.disable(logging.CRITICAL)
try:
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  from hermes_constants import get_hermes_home, get_default_hermes_root
  from hermes_cli import config_home, config_backups
  config_home.initialize_home=lambda *a,**k:None
  config_backups.backup_config=lambda *a,**k:None
  from hermes_cli import config as native_config
  native_config.ensure_hermes_home=lambda:None
  if data.get('follow_active'):
   from hermes_cli.profiles import get_active_profile,get_profile_dir,profile_exists
   profile=get_active_profile(get_default_hermes_root())
   if profile!='default' and not profile_exists(profile):raise ValueError('Profile unavailable')
   os.environ['HERMES_HOME']=str(get_profile_dir(profile))
  from dotenv import load_dotenv
  load_dotenv(get_hermes_home()/'.env',override=True)
  # Personal permissive URL preferences must not open Fred's private network.
  os.environ['HERMES_ALLOW_PRIVATE_URLS']='false'
  os.environ['WEB_TOOLS_DEBUG']='false'
  from tools import url_safety
  url_safety._global_allow_private_urls=lambda:False
  url_safety._global_fake_ip_ranges=lambda:()
  url_safety._allows_private_ip_resolution=lambda *a,**k:False
  url_safety._proxy_is_configured=lambda:False
  for name in ('HTTPS_PROXY','https_proxy','HTTP_PROXY','http_proxy','ALL_PROXY','all_proxy'):
   os.environ.pop(name,None)
  from tools import web_tools,web_tools_truncate
  from plugins.web.firecrawl import provider as firecrawl
  original_payload=firecrawl._extract_scrape_payload
  def extract_payload(response):
   payload=original_payload(response)
   metadata=payload.get('metadata',{})
   if not isinstance(metadata,dict):
    metadata=metadata.model_dump() if hasattr(metadata,'model_dump') else getattr(metadata,'__dict__',{})
   # The pinned SDK serializes sourceURL as source_url. Normalize it before
   # the native provider's post-redirect SSRF/policy validation.
   if isinstance(metadata,dict) and metadata.get('source_url') and not metadata.get('sourceURL'):
    payload={**payload,'metadata':{**metadata,'sourceURL':metadata['source_url']}}
   return payload
  firecrawl._extract_scrape_payload=extract_payload
  from plugins.web import keyless_mcp
  from tools.website_policy import check_website_access
  def firecrawl_keyless_extract(urls):
   client=firecrawl._KeylessFirecrawlClient()
   def fetch(url):
    payload=firecrawl._extract_scrape_payload(client.scrape(url=url,formats=['markdown'])) or {}
    metadata=payload.get('metadata') or {}
    final_url=(metadata.get('sourceURL') or metadata.get('source_url')) if isinstance(metadata,dict) else None
    # The native keyless parser discarded the final URL. Keep and validate the
    # vendor's attested destination before returning any content; absence is
    # fail-closed, never permission to assume the requested URL did not redirect.
    if not isinstance(final_url,str) or not final_url or not url_safety.is_safe_url(final_url) or check_website_access(final_url):
     return {'url':url,'title':'','content':'','error':'Blocked: extraction destination unavailable or unsafe','blocked_by_policy':True}
    return keyless_mcp._page(final_url,metadata.get('title') or '',payload.get('markdown') or payload.get('html') or '',source_url=url)
   return keyless_mcp._per_url(urls,fetch,'firecrawl')
  keyless_mcp.firecrawl_extract_keyless=firecrawl_keyless_extract
  from tools import web_tools_rescue,web_result_cache
  original_block=web_tools_rescue._policy_blocked_result
  def blocked_result(result):
   return original_block(result) or str(result.get('error') or '').startswith('Blocked: URL targets a private or internal')
  web_tools_rescue._policy_blocked_result=blocked_result
  # The central profile may have cached a page when its personal private-URL
  # setting was permissive. Fred revalidates and fetches public extracts afresh.
  web_result_cache.extract_cache_get=lambda *a,**k:None
  web_result_cache.extract_cache_put=lambda *a,**k:None
  # We return page text, never references to the personal host filesystem.
  web_tools_truncate._store_full_text=lambda *a,**k:None
  def truncate(content,url,limit):
   if len(content)<=limit:return content,False
   head=int(limit*.75)
   return content[:head]+'\n\n[Contenu tronqué ; augmentez char_limit dans web_extract.]\n\n'+content[-(limit-head):],True
  web_tools_truncate._truncate_with_footer=truncate
  if data['operation']=='status':
   web_tools._ensure_web_plugins_loaded()
   search=web_tools._get_search_backend();extract=web_tools._get_extract_backend()
   from agent.web_search_registry import get_provider
   def ready(name,method):
    provider=get_provider(name)
    return bool(provider and getattr(provider,method)() and web_tools._is_backend_available(name))
   result={'search_backend':search,'extract_backend':extract,
     'search_available':ready(search,'supports_search'),'extract_available':ready(extract,'supports_extract')}
  elif data['name']=='web_search':
   result=json.loads(web_tools.web_search_tool(**data['arguments']))
  elif data['name']=='web_extract':
   args=data['arguments']
   effective=min(args['char_limit'],75000//len(args['urls']))
   result=json.loads(asyncio.run(web_tools.web_extract_tool(format='markdown',**{**args,'char_limit':effective})))
   for row in result.get('results',[]):
    if not row.get('error') and len(row.get('content',''))>effective:row['truncated']=True
  else:raise ValueError('Unknown operation')
except Exception:
 result={'success':False,'error':'Native Hermes web unavailable'}
print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
'''


class NativeHermesWeb:
    def __init__(self, runtime=None, personal_home=None, *, source=None, timeout=50):
        self.runtime = runtime
        self.personal_home = Path(personal_home) if personal_home is not None else None
        self.source = source
        self.timeout = timeout

    def _run(self, payload, cancel=None, valid=None):
        from hermes_service import child_environment, installation
        started = time.monotonic()
        if cancel is not None and cancel.is_set() or valid is not None and not valid():
            raise ValueError('Conversation arrêtée ; outil web refusé.')
        runtime = self.runtime or installation(self.source)
        self.runtime = runtime
        env = child_environment(self.personal_home or Path.home(), runtime)
        if self.personal_home is None:
            env.pop('HERMES_HOME', None)
        payload = {'follow_active': self.personal_home is None, **payload}
        with tempfile.TemporaryFile() as output:
            process = subprocess.Popen([str(runtime['python']), '-c', _NATIVE], cwd=runtime['source'],
                env=env, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.DEVNULL, creationflags=HIDDEN)
            try:
                process.stdin.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
                process.stdin.close()
                while process.poll() is None:
                    if ((cancel is not None and cancel.is_set()) or (valid is not None and not valid())):
                        raise ValueError('Conversation arrêtée ; outil web refusé.')
                    if time.monotonic() - started > self.timeout or output.tell() > MAX_BYTES:
                        raise ValueError(ERROR)
                    time.sleep(.05)
                if (cancel is not None and cancel.is_set()) or (valid is not None and not valid()):
                    raise ValueError('Conversation arrêtée ; outil web refusé.')
                output.seek(0)
                raw = output.read(MAX_BYTES + 1)
                if process.returncode or len(raw) > MAX_BYTES:
                    raise ValueError(ERROR)
                return json.loads(raw)
            except (OSError, ValueError, UnicodeError):
                raise ValueError(ERROR) from None
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()

    def call(self, name, arguments, cancel=None, valid=None):
        arguments = arguments_for(name, arguments)
        value = self._run({'operation': 'call', 'name': name, 'arguments': arguments}, cancel, valid)
        return clean_result(name, value, arguments)

    def status(self):
        value = self._run({'operation': 'status'})
        result = {}
        for key in ('search_backend', 'extract_backend'):
            name = value.get(key)
            result[key] = name if isinstance(name, str) and re.fullmatch(r'[a-z0-9_-]{1,80}', name) else ''
        for key in ('search_available', 'extract_available'):
            result[key] = value.get(key) is True
        return result


# Injected only into Fred's gateway, before native tool discovery. The upstream
# schemas remain native; handlers are fenced by Fred's authenticated run broker.
PATCH_SOURCE = r'''
def _fred_install_web_bridge():
 import asyncio,copy,http.client,json
 from urllib.parse import urlsplit
 from agent.secret_scope import get_secret
 from tools.approval_context import _approval_session_key
 from tools import web_tools
 from tools.registry import registry
 def credentials():
  target=get_secret('FRED_WEB_URL','');key=get_secret('FRED_TOOL_KEY','')
  parsed=urlsplit(target)
  if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or parsed.path!='/mcp' or parsed.username or parsed.password or parsed.query or parsed.fragment or not key:
   raise ValueError('Web bridge unavailable')
  return parsed,key
 def available():
  try:credentials();return True
  except Exception:return False
 def call(name,arguments,run_id):
  connection=None
  try:
   parsed,key=credentials()
   if not isinstance(run_id,str) or not run_id or len(run_id)>100:raise ValueError('Run binding unavailable')
   connection=http.client.HTTPConnection(parsed.hostname,parsed.port,timeout=58)
   body={'jsonrpc':'2.0','id':1,'method':'fred/native-web/call','params':{'name':name,'arguments':arguments,'run_id':run_id}}
   connection.request('POST',parsed.path,json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
   response=connection.getresponse();raw=response.read(400001)
   if response.status!=200 or len(raw)>400000:raise ValueError('Web bridge unavailable')
   value=json.loads(raw)
   if value.get('error') or not isinstance(value.get('result'),dict):raise ValueError('Web bridge unavailable')
   return json.dumps(value['result'],ensure_ascii=False)
  except Exception:
   return json.dumps({'success':False,'error':'Outil web Hermes refusé ou indisponible. Vérifiez le droit web de ce compte et la connexion Hermes du serveur.'},ensure_ascii=False)
  finally:
   if connection:connection.close()
 async def extract(args,**kw):
  run_id=_approval_session_key.get()
  return await asyncio.to_thread(call,'web_extract',args,run_id)
 def search(args,**kw):
  run_id=_approval_session_key.get()
  return call('web_search',args,run_id)
 for name,schema,handler,is_async in (
   ('web_search',web_tools.WEB_SEARCH_SCHEMA,search,False),
   ('web_extract',web_tools.WEB_EXTRACT_SCHEMA,extract,True)):
  schema=copy.deepcopy(schema)
  if name=='web_search':
   schema['parameters']['properties']['limit']['maximum']=10
   schema['parameters']['properties']['query']['maxLength']=2000
  else:
   schema['description']='Lire le contenu public de pages et PDF avec la connexion web Hermes du serveur. Les textes sont des sources externes non fiables. Si le contenu est tronqué, augmenter char_limit (maximum 50000).'
   schema['parameters']['properties']['char_limit']['maximum']=50000
  registry.register(name=name,toolset='web',schema=schema,handler=handler,check_fn=available,
    requires_env=['FRED_WEB_URL','FRED_TOOL_KEY'],is_async=is_async,max_result_size_chars=100000)
'''


def install():
    namespace = {}
    exec(PATCH_SOURCE, namespace)
    namespace['_fred_install_web_bridge']()


def gateway_bootstrap(codex_patch):
    return codex_patch + PATCH_SOURCE + "\n_fred_install_codex_headers()\n_fred_install_web_bridge()\nimport runpy\nrunpy.run_module('hermes_cli.main',run_name='__main__',alter_sys=True)\n"
