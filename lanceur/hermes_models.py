"""Hermes model discovery and explicit, centrally brokered provider sharing.

Only public model metadata reaches clients. Personal refresh tokens stay in the
original Hermes store; native Kiara profiles request a short-lived credential
through the authenticated private broker while their own run is active.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import subprocess
import threading
import time
from urllib.parse import urlsplit

from core import HIDDEN, health, read_json, write_json
from workspace import Denied
from chat_attachments import capabilities as attachment_capabilities
from hermes_reasoning import controls

LOCAL = 'fred-qwen'
MODEL_ID = re.compile(r'fred-model-[a-f0-9]{24}')
MODES = {'chat_completions', 'anthropic_messages', 'codex_responses'}


def normalize_policy(value):
    if not isinstance(value,dict) or set(value)-{'version','share_all','shared_accounts','exposed_models'}:
        raise ValueError('Politique de modèles Hermes invalide.')
    if type(value.get('version',1)) is not int or value.get('version',1)!=1:
        raise ValueError('Version de politique Hermes invalide.')
    if type(value.get('share_all',False)) is not bool:raise ValueError('Partage global invalide.')
    owners=value.get('shared_accounts',[])
    if not isinstance(owners,list) or len(owners)>100 or any(not isinstance(owner,str) or not re.fullmatch(r'[a-f0-9]{16}',owner) for owner in owners):
        raise ValueError('Liste de comptes Hermes invalide.')
    exposed=value.get('exposed_models')
    if exposed is not None and (not isinstance(exposed,list) or len(exposed)>512 or any(not isinstance(model,str) or not MODEL_ID.fullmatch(model) for model in exposed)):
        raise ValueError('Liste de modèles exposés invalide.')
    return {'version':1,'share_all':value.get('share_all',False),'shared_accounts':list(dict.fromkeys(owners)),
        'exposed_models':list(dict.fromkeys(exposed)) if exposed is not None else None}


class ModelUnavailable(ValueError): pass


_NATIVE = r'''
import contextlib, copy, io, json, logging, os
from pathlib import Path
payload=json.load(__import__('sys').stdin)
logging.disable(logging.CRITICAL)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
 from hermes_constants import get_hermes_home, get_default_hermes_root
 from hermes_cli import config_home, config_backups
 config_home.initialize_home=lambda *a,**k:None
 config_backups.backup_config=lambda *a,**k:None
 from hermes_cli import config as native_config
 # Native readonly loading can seed the home and snapshot personal config.
 # Suppress that maintenance in this short-lived metadata/credential process.
 native_config.ensure_hermes_home=lambda:None
 config_backups.backup_config=lambda *a,**k:None
 native_profile='fixed'
 if payload.get('follow_active'):
  from hermes_cli.profiles import get_active_profile, get_profile_dir, profile_exists
  native_profile=get_active_profile(get_default_hermes_root())
  if native_profile!='default' and not profile_exists(native_profile):raise ValueError('Active profile unavailable')
  os.environ['HERMES_HOME']=str(get_profile_dir(native_profile))
 from dotenv import load_dotenv
 load_dotenv(get_hermes_home()/'.env', override=True)
 from hermes_cli.config import load_config_readonly, _normalize_root_model_keys
 from hermes_cli import models
 from hermes_cli.providers import get_provider, normalize_provider, custom_provider_slug
 from hermes_cli.auth import get_auth_status
 cfg=_normalize_root_model_keys(copy.deepcopy(load_config_readonly()))
 def copilot_mode(mid,catalog):
  mode=models.copilot_model_api_mode(mid,catalog=catalog)
  item=next((item for item in catalog if item.get('id')==mid),{})
  endpoints=item.get('supported_endpoints')
  if isinstance(endpoints,list) and endpoints:
   if mode=='chat_completions' and '/chat/completions' not in endpoints and '/responses' in endpoints:return 'codex_responses'
   if mode=='codex_responses' and '/responses' not in endpoints and '/chat/completions' in endpoints:return 'chat_completions'
  return mode
 if payload['operation']=='credential':
  from hermes_cli.runtime_provider import resolve_runtime_provider
  runtime=resolve_runtime_provider(requested=payload['provider'],target_model=payload['model'])
  key=runtime.get('api_key')
  key=key() if callable(key) else key
  if not isinstance(key,str) or not key.strip():raise ValueError('Credential unavailable')
  if payload['provider'] in {'copilot','github-copilot'}:
   from hermes_cli.copilot_auth import validate_copilot_token
   # A raw GitHub credential is a degraded native fallback, not proof of a
   # licensed Copilot connection. Never forward it as an available model key.
   if validate_copilot_token(key)[0]:raise ValueError('Copilot connection unavailable')
   catalog=models.fetch_github_model_catalog(api_key=key,timeout=5) or []
   if not any(item.get('id')==payload['model'] for item in catalog):raise ValueError('Copilot model unavailable')
   runtime['api_mode']=copilot_mode(payload['model'],catalog)
  result={'api_key':key,'base_url':runtime.get('base_url',''),'api_mode':runtime.get('api_mode','chat_completions'),
          'expires_at':runtime.get('expires_at')}
 else:
  main=cfg.get('model',{}) if isinstance(cfg.get('model'),dict) else {}
  main_provider=normalize_provider(str(main.get('provider') or ''))
  custom={}
  for name,entry in (cfg.get('providers',{}).items() if isinstance(cfg.get('providers'),dict) else []):
   if isinstance(entry,dict) and entry.get('enabled',True) is not False:
    custom[custom_provider_slug(str(entry.get('name') or name),str(name))]=entry
  for entry in cfg.get('custom_providers',[]) if isinstance(cfg.get('custom_providers'),list) else []:
   if isinstance(entry,dict):custom[custom_provider_slug(str(entry.get('name') or ''))]=entry
  from hermes_cli.inventory import ConfigContext, build_models_payload
  from hermes_cli.config import coerce_provider_id, stringify_provider_map, get_compatible_custom_providers
  from agent.models_dev import get_model_info, get_model_capabilities
  from agent.reasoning_effort import OPENAI_COMPAT_WIRE_EFFORTS, codex_supported_efforts
  from hermes_cli.models_reasoning_caps import nous_model_reasoning_capabilities, openrouter_model_reasoning_capabilities
  from hermes_cli.models_reasoning_caps import _fetch_caps, _NOUS_CAPS, _OPENROUTER_CAPS
  from hermes_cli.providers import determine_api_mode
  excluded=cfg.get('model_catalog',{}).get('excluded_providers',[])
  ctx=ConfigContext(coerce_provider_id(main.get('provider','')),str(main.get('default') or main.get('name') or ''),
    str(main.get('base_url') or ''),stringify_provider_map(cfg.get('providers')),
    get_compatible_custom_providers(cfg),excluded if isinstance(excluded,list) else [])
  inventory=build_models_payload(ctx,include_unconfigured=False,pricing=False,capabilities=False,
    probe_custom_providers=True,non_blocking_catalogs=False)
  rows=[]
  for candidate in inventory.get('providers',[]):
   pid=str(candidate.get('slug') or '')
   if pid in {'moa','llamacpp'} or candidate.get('authenticated') is False:continue
   entry=custom.get(pid,{})
   try:status=get_auth_status(pid)
   except Exception:status={}
   # The native inventory has already checked auth stores, credential pools,
   # per-profile keys and external CLI connections. Do not replace that ladder
   # with a second partial check, or connected Codex accounts disappear.
   configured=True
   definition=get_provider(pid,allow_network=False)
   url=str(candidate.get('api_url') or entry.get('base_url') or entry.get('api') or entry.get('url') or status.get('base_url') or (definition.base_url if definition else '') or '')
   if pid==main_provider:url=str(main.get('base_url') or url)
   selected=[];provider_available=True;unavailable_reason='';copilot_catalog=[]
   # Discovery is bounded and outside admission locks. Refresh a single public
   # capability catalogue per aggregator; a stale disk verdict must not cause
   # Kiara to advertise an effort that the route now silently clamps.
   reasoning_catalog=None
   if pid in {'nous','openrouter'}:
    reasoning_catalog=_fetch_caps(_NOUS_CAPS if pid=='nous' else _OPENROUTER_CAPS,timeout=4,force=True)
   if pid in {'copilot','github-copilot'}:
    try:
     from hermes_cli.runtime_provider import resolve_runtime_provider
     from hermes_cli.copilot_auth import validate_copilot_token
     connection=resolve_runtime_provider(requested=pid,target_model=str(main.get('default') or '') or None)
     api_key=connection.get('api_key');api_key=api_key() if callable(api_key) else api_key
     copilot_catalog=models.fetch_github_model_catalog(api_key=api_key,timeout=5) or []
     provider_available=bool(copilot_catalog) and isinstance(api_key,str) and bool(api_key) and not validate_copilot_token(api_key)[0]
     url=str(connection.get('base_url') or url)
    except Exception:provider_available=False
    if not provider_available:unavailable_reason='Connexion Copilot incomplète ou non autorisée.'
   def add(mid,meta=None):
    if isinstance(mid,str) and mid.strip():
     mid=mid.strip()
     meta=meta if isinstance(meta,dict) else {}
     caps=meta.get('capabilities') if isinstance(meta.get('capabilities'),dict) else {}
     supports=caps.get('supports') if isinstance(caps.get('supports'),dict) else {}
     limits=caps.get('limits') if isinstance(caps.get('limits'),dict) else {}
     info=get_model_info(pid,mid,allow_network=False,config=cfg)
     native_caps=get_model_capabilities(pid,mid,allow_network=False,config=cfg)
     mode=str(entry.get('api_mode') or entry.get('transport') or determine_api_mode(pid,url,mid))
     mode={'openai_chat':'chat_completions','openai':'chat_completions'}.get(mode,mode)
     if pid in {'copilot','github-copilot'}:mode=copilot_mode(mid,copilot_catalog)
     elif models.opencode_provider_family(pid):mode=models.opencode_model_api_mode(pid,mid)
     elif pid=='azure-foundry':mode=models.azure_foundry_model_api_mode(mid) or mode
     detail=None;efforts=supports.get('reasoning_effort') or caps.get('reasoning_efforts')
     thinking=bool(supports.get('reasoning_effort') or supports.get('adaptive_thinking')) or getattr(native_caps,'supports_reasoning',None) is True
     control_mode='effort' if isinstance(efforts,list) and efforts else 'none'
     if pid in {'nous','openrouter'}:
      detail=reasoning_catalog.get(mid) if isinstance(reasoning_catalog,dict) else None
      if detail is not None:
       thinking=detail.get('supports_reasoning') is True
       efforts=detail.get('supported_efforts')
       if thinking:
        if isinstance(efforts,list) and efforts:
         efforts=[e for e in OPENAI_COMPAT_WIRE_EFFORTS if e in efforts]
         if not detail.get('mandatory') and 'none' not in efforts:efforts.insert(0,'none')
         if detail.get('mandatory'):efforts=[e for e in efforts if e!='none']
         if pid=='openrouter' and mid.startswith('openai/') and 'none' not in codex_supported_efforts(mid):efforts=[e for e in efforts if e!='none']
         control_mode='effort'
        else:
         efforts=['on'] if detail.get('mandatory') else ['none','on'];control_mode='toggle'
       else:efforts=[];control_mode='none'
     elif pid=='openai-codex':
      thinking=True;efforts=list(codex_supported_efforts(mid));control_mode='effort'
     elif pid in {'nvidia','nvidia-nim'}:
      # The pinned native NVIDIA profile emits no reasoning override. Do not
      # claim an effort or toggle merely because the model can think internally.
      efforts=[];control_mode='none'
     if control_mode=='none':efforts=[]
     selected.append({'id':mid,'name':str(meta.get('name') or (info.name if info else '') or mid),
       'api_mode':mode,'context_length':limits.get('max_prompt_tokens') or limits.get('max_context_window_tokens') or meta.get('context_length') or meta.get('context_window') or (info.context_window if info else None),
       'capabilities':{'vision':supports.get('vision',caps.get('vision',meta.get('vision',getattr(native_caps,'supports_vision',None)))) is True,
                       'thinking':thinking,'reasoning_mode':control_mode,'reasoning_efforts':efforts},
       'available':provider_available and (not isinstance(meta.get('supported_endpoints'),list) or not meta['supported_endpoints'] or ('/responses' if mode=='codex_responses' else '/chat/completions') in meta['supported_endpoints'])})
   metadata=entry.get('models',{}) if isinstance(entry.get('models'),dict) else {}
   if copilot_catalog:
    for item in copilot_catalog:add(item.get('id'),item)
   else:
    for mid in candidate.get('models',[]):add(mid,metadata.get(mid))
   rows.append({'provider':pid,'label':candidate.get('name') or pid,'configured':configured,
                'base_url':url,'models':selected,'available':provider_available,'unavailable_reason':unavailable_reason})
  result={'providers':rows,'home':str(get_hermes_home()),'profile':native_profile,
          'main_model':str(main.get('default') or ''),'main_provider':main_provider}
print(json.dumps(result,separators=(',',':')))
'''


class NativeModelSource:
    """Read-only metadata; credential resolution is a separate execution-time operation."""
    def __init__(self, runtime=None, personal_home=None):
        self.runtime = runtime
        # The native Windows home is LOCALAPPDATA/hermes, and its sticky active
        # profile is resolved by Hermes itself. An explicitly supplied home is
        # fixed (used by isolated tests and intentionally selected deployments).
        self.personal_home = Path(personal_home) if personal_home is not None else None
        self.lock = threading.Lock()
        self.provider_locks = {}
        self.credential_cache = {}

    def _run(self, operation, timeout, **values):
        from hermes_service import child_environment, installation
        started=time.monotonic()
        runtime = self.runtime or installation()
        self.runtime=runtime
        timeout-=time.monotonic()-started
        if timeout<=0:raise ModelUnavailable('Connexion Hermes du fournisseur indisponible.')
        home=values.pop('source_home',None) or self.personal_home
        env = child_environment(home or Path.home(), runtime)
        if home is None:env.pop('HERMES_HOME',None)
        completed = subprocess.run([str(runtime['python']), '-c', _NATIVE],
            input=json.dumps({'operation':operation,'follow_active':home is None, **values}).encode(),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=runtime['source'],
            env=env, timeout=timeout, creationflags=HIDDEN)
        if completed.returncode or len(completed.stdout)>4*1024*1024:
            raise ModelUnavailable('Connexion Hermes du fournisseur indisponible.')
        try:return json.loads(completed.stdout)
        except (ValueError,UnicodeError):raise ModelUnavailable('Catalogue Hermes indisponible.') from None

    def _request(self, operation, **values):
        # Discovery can involve slow provider catalogue requests. Its lock must
        # never delay execution-time key_cmd beyond Hermes' 15-second deadline.
        if operation!='credential':return self._run(operation,35,**values)
        provider=values['provider'];identity=(provider,values['model'],values.get('source_home'));deadline=time.monotonic()+11.5
        # Refresh tokens rotate centrally, serialized per provider. Duplicate
        # same-model requests coalesce for at most two seconds; model-specific
        # pool selection is preserved, never reused for a different model.
        with self.lock:
            guard=self.provider_locks.setdefault(provider,threading.Lock())
        if not guard.acquire(timeout=max(0,deadline-time.monotonic())):
            raise ModelUnavailable('Connexion Hermes occupée ; réessayez dans un instant.')
        try:
            now=time.monotonic()
            with self.lock:
                cached=self.credential_cache.get(identity)
                if cached and cached[0]>now:return dict(cached[1])
            remaining=deadline-now
            if remaining<.2:raise ModelUnavailable('Connexion Hermes occupée ; réessayez dans un instant.')
            value=self._run(operation,remaining,**values)
            ttl=2.0;expiry=value.get('expires_at')
            if type(expiry) in (int,float):ttl=max(0,min(ttl,expiry-time.time()-30))
            with self.lock:
                self.credential_cache={key:entry for key,entry in self.credential_cache.items() if entry[0]>time.monotonic()}
                if len(self.credential_cache)>=256:self.credential_cache.pop(next(iter(self.credential_cache)))
                if ttl>0:self.credential_cache[identity]=(time.monotonic()+ttl,dict(value))
            return value
        except (OSError,subprocess.TimeoutExpired):raise ModelUnavailable('Connexion Hermes du fournisseur indisponible.') from None
        finally:guard.release()

    def discover(self): return self._request('discover')
    def credential(self, provider, model, source_home=None):
        return self._request('credential',provider=provider,model=model,**({'source_home':source_home} if source_home else {}))


class HermesModels:
    def __init__(self, store, backend, accounts, *, source=None, clock=time.monotonic):
        self.store, self.backend, self.accounts = store, backend, accounts
        self.source = source or NativeModelSource()
        self.path = Path(store.home) / 'hermes-models.json'
        self.clock = clock; self.lock = threading.RLock()
        self.cached = []; self.providers = []; self.cached_at = None; self.error = ''; self.on_changed = None
        self.hermes_context={}
        self.local_route=None

    def policy(self):
        value = read_json(self.path,{})
        try:return normalize_policy(value)
        except ValueError:return normalize_policy({})

    def allowed(self, owner):
        policy = self.policy()
        return bool(self.accounts.authorized(owner) and (policy['share_all'] or owner in policy['shared_accounts']))

    @staticmethod
    def _endpoint(value):
        parsed=urlsplit(value)
        if (parsed.scheme not in {'https','http'} or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or (parsed.scheme=='http' and parsed.hostname not in {'127.0.0.1','localhost','::1'})):
            raise ValueError('Endpoint Hermes non pris en charge.')
        return value.rstrip('/')

    def refresh(self, force=False):
        with self.lock:
            if not force and self.cached_at is not None and self.clock()-self.cached_at<30:return self.cached
            try:
                discovered=self.source.discover(); rows=[]; providers=[]
                source_home=discovered.get('home') if isinstance(self.source,NativeModelSource) else None
                self.hermes_context={key:discovered.get(key,'') for key in ('profile','main_model','main_provider')}
                for provider in discovered.get('providers',[]):
                    if not isinstance(provider,dict) or provider.get('configured') is not True:continue
                    try:endpoint=self._endpoint(provider['base_url'])
                    except (KeyError,TypeError,ValueError):continue
                    native=str(provider.get('provider') or '')
                    if not native or len(native)>128:continue
                    providers.append({'id':'fred-provider-'+hashlib.sha256(native.encode()).hexdigest()[:24],
                        'label':str(provider.get('label') or native),'configured':True,'model_count':0,
                        'available':provider.get('available',True) is True,
                        'unavailable_reason':('Connexion Copilot incomplète ou non autorisée.'
                            if native in {'copilot','github-copilot'} and provider.get('available') is False else '')})
                    for item in provider.get('models',[]):
                        if not isinstance(item,dict):continue
                        model=item.get('id')
                        if not isinstance(model,str) or not 1<=len(model)<=256 or any(ord(c)<32 for c in model):continue
                        mode=item.get('api_mode',provider.get('api_mode','chat_completions'))
                        if mode not in MODES:continue
                        identity='fred-model-'+hashlib.sha256(json.dumps([native,endpoint,model,mode]).encode()).hexdigest()[:24]
                        capabilities=item.get('capabilities',{}) if isinstance(item.get('capabilities'),dict) else {}
                        vision=capabilities.get('vision',item.get('vision',False)) is True
                        context=item.get('context_length') or item.get('context_window')
                        context=context if type(context) is int and 0<context<=10000000 else None
                        reasoning=controls(capabilities)
                        rows.append({'id':identity,'name':model,'label':str(item.get('name') or model),
                            'provider':str(provider.get('label') or native),'provider_id':native,'local':False,
                            'base_url':endpoint,'api_mode':mode,'available':provider.get('available',True) is True and item.get('available',True) is True and (context is None or context>=64000),
                            'capabilities':{**attachment_capabilities({'images':vision}),
                                'vision':vision,'images':vision,'context_length':context,
                                **reasoning},
                            'native_provider':'custom:'+identity,'native_model':model,'source_home':source_home})
                    providers[-1]['model_count']=len({row['id'] for row in rows if row['provider_id']==native})
                    providers[-1]['available_model_count']=len({row['id'] for row in rows if row['provider_id']==native and row['available']})
                self.cached=list({row['id']:row for row in rows}.values()); self.providers=providers; self.error=''
            except Exception:
                # Discovery errors can carry URLs or authentication details; never retain them.
                self.cached=[]; self.providers=[]; self.hermes_context={};self.error='Catalogue Hermes temporairement indisponible.'
            self.cached_at=self.clock()
            return list(self.cached)

    def _local(self):
        try:
            port,alias,_=self.backend(); state=health('127.0.0.1',port)
            self.local_route=(port,{str(alias),str(state.get('model') or '')})
        except Exception:alias='';state={}
        vision=state.get('images') is True
        context=state.get('context_length') or state.get('context_size') or 262144
        return {'id':LOCAL,'name':str(state.get('model') or alias or 'Qwen local'),'label':'Qwen local',
                'provider':'Qwen local','local':True,'available':state.get('loaded') is True,
                'capabilities':{**attachment_capabilities(state),'vision':vision,'context_length':context,'reasoning_mode':'effort'},'native_model':LOCAL}

    @staticmethod
    def public(row):
        return {key:row[key] for key in ('id','name','label','provider','available','capabilities')} | {'object':'model','owned_by':'fred'}

    def exposed(self, identity):
        exposed=self.policy()['exposed_models']
        return exposed is None or identity in exposed

    def duplicate_local(self,row):
        if not self.local_route:return False
        port,names=self.local_route;endpoint=urlsplit(row.get('base_url',''))
        return bool(endpoint.hostname in {'127.0.0.1','localhost','::1'}
            and (endpoint.port or (443 if endpoint.scheme=='https' else 80))==port
            and row.get('native_model') in names)

    def usable(self,row):return row['available'] and not self.duplicate_local(row)

    def catalog(self, owner):
        if not self.accounts.authorized(owner):raise Denied('Accès aux modèles désactivé.')
        rows=[self._local()]+([row for row in self.refresh() if self.usable(row) and self.exposed(row['id'])] if self.allowed(owner) else [])
        return {'object':'list','data':[self.public(row) for row in rows], 'default_model':LOCAL,'source':'hermes'}

    def select(self, owner, requested=None, *, require_available=True):
        if not self.accounts.authorized(owner):raise Denied('Accès aux modèles désactivé.')
        local=self._local()
        if requested in (None,'',LOCAL,local['name']):selection=local
        else:
            if not isinstance(requested,str) or not MODEL_ID.fullmatch(requested):raise ValueError('Modèle Hermes inconnu.')
            if not self.allowed(owner):raise Denied('Ce compte ne peut pas utiliser les fournisseurs Hermes partagés.')
            selection=next((dict(row) for row in self.refresh() if row['id']==requested),None)
            if selection is None:raise ValueError('Modèle Hermes inconnu ou connexion retirée.')
            if not self.exposed(requested):raise Denied('Ce modèle n’est pas exposé aux clients Kiara.')
            if self.duplicate_local(selection):raise Denied('Ce modèle est déjà disponible avec Qwen local.')
        if require_available and not selection['available']:raise ModelUnavailable('Le modèle sélectionné est indisponible.')
        return selection

    def valid(self, owner, selection):
        if not self.accounts.authorized(owner):return False
        # Watchers and admission fences never perform network discovery while
        # holding account/controller locks. A credential is resolved afresh at
        # execution time; policy revocation is checked here on every use.
        return bool(selection.get('local') or (self.allowed(owner) and self.exposed(selection.get('id')) and any(row['id']==selection.get('id') and self.usable(row) for row in self.cached)))

    def credential(self, owner, selection):
        if selection.get('local') or not self.valid(owner,selection):raise Denied('Fournisseur non autorisé.')
        try:
            value=self.source.credential(selection['provider_id'],selection['native_model'],selection.get('source_home')) if isinstance(self.source,NativeModelSource) else self.source.credential(selection['provider_id'],selection['native_model'])
            if self._endpoint(value['base_url'])!=selection['base_url'] or value.get('api_mode')!=selection['api_mode']:
                raise ModelUnavailable('La connexion Hermes a changé ; actualisez les modèles.')
            key=value['api_key']
            if not isinstance(key,str) or not 1<=len(key)<=32768 or any(c in key for c in '\r\n'):
                raise ModelUnavailable('Credential de fournisseur indisponible.')
            if not self.valid(owner,selection):raise Denied('Fournisseur non autorisé.')
            return {'access_token':key,'expires_in':1}
        except Denied:raise
        except Exception:raise ModelUnavailable('Connexion Hermes du fournisseur indisponible.') from None

    def admin(self,force=False):
        self._local()
        rows=self.refresh(force=force)
        providers=[{**provider,'available_model_count':sum(self.usable(row) for row in rows if row['provider']==provider['label']),
            'local_model_reused':any(self.duplicate_local(row) for row in rows if row['provider']==provider['label'])} for provider in self.providers]
        return {**self.policy(),'providers':providers,
                'models':[{**self.public(row),'exposed':self.exposed(row['id'])} for row in rows if self.usable(row)],
                'default_model':LOCAL,'source':'hermes','error':self.error,'hermes_context':dict(self.hermes_context)}

    def configure(self, value):
        if not isinstance(value,dict) or set(value)-{'share_all','shared_accounts','exposed_models'}:raise ValueError('Politique de modèles invalide.')
        policy=self.policy()
        if 'share_all' in value:
            if type(value['share_all']) is not bool:raise ValueError('Partage global invalide.')
            policy['share_all']=value['share_all']
        if 'shared_accounts' in value:
            owners=value['shared_accounts']
            known={client['id'] for client in read_json(self.store.path,{}).get('clients',[])}
            if not isinstance(owners,list) or len(owners)>100 or any(not isinstance(owner,str) or owner not in known for owner in owners):
                raise ValueError('Compte de partage inconnu.')
            policy['shared_accounts']=list(dict.fromkeys(owners))
        if 'exposed_models' in value:
            requested=normalize_policy({'exposed_models':value['exposed_models']})['exposed_models']
            if requested is not None:
                known={row['id'] for row in self.refresh() if self.usable(row)}
                retained=set(policy['exposed_models'] or [])
                if any(identity not in known and identity not in retained for identity in requested):
                    raise ValueError('Modèle exposé inconnu ou indisponible.')
            policy['exposed_models']=requested
        policy=normalize_policy(policy)
        with self.lock:write_json(self.path,policy)
        if self.on_changed:self.on_changed()
        return self.admin()

    def profile_config(self, owner, request_id=None):
        if not self.allowed(owner):return {}
        runtime=self.source.runtime if isinstance(self.source,NativeModelSource) else None
        if not runtime:
            from hermes_service import installation
            runtime=installation()
        command=[str(runtime['python']),str(Path(__file__).with_name('hermes_model_key.py'))]
        providers={}
        for row in self.refresh():
            if not self.usable(row) or not self.exposed(row['id']):continue
            providers[row['id']]={'name':row['id'],'base_url':row['base_url'],'transport':row['api_mode'],
                'default_model':row['native_model'],'key_cmd':subprocess.list2cmdline(command+[row['id']]+([request_id] if request_id else [])),
                'models':{row['native_model']:row['capabilities']},
                'capabilities':{'vision':row['capabilities']['vision']}}
            if row['capabilities']['context_length']:providers[row['id']]['context_length']=row['capabilities']['context_length']
        return {'providers':providers} if providers else {}
