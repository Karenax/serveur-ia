"""Add the running client's model to local OpenCode/Hermes configurations."""
import copy
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import time
from urllib.parse import urlsplit

import yaml
import opencode_visibility
import hermes_catalogue
from file_lock import locked
from history_store import atomic

PROVIDER='serveur-fred'
LABEL='Serveur Fred'
MAX_CONFIG=2*1024*1024


def detect(home=None,environ=None,which=None):
    home=Path.home() if home is None else Path(home)
    env=os.environ if environ is None else environ
    which=shutil.which if which is None else which
    local=Path(env.get('LOCALAPPDATA',str(home/'AppData/Local')))
    xdg=Path(env.get('XDG_CONFIG_HOME',str(home/'.config')))
    directory=Path(env.get('OPENCODE_CONFIG_DIR',str(xdg/'opencode')))
    # OpenCode merges JSON before JSONC; edit the source with the last word.
    paths=[directory/'opencode.jsonc',directory/'opencode.json']
    opencode=Path(env['OPENCODE_CONFIG']) if env.get('OPENCODE_CONFIG') else next((p for p in paths if p.is_file()),directory/'opencode.json')
    hermes_default=local/'hermes' if (local/'hermes/bin/hermes.exe').is_file() else home/'.hermes'
    hermes_home=Path(env['HERMES_HOME']) if env.get('HERMES_HOME') else next((p for p in (local/'hermes',home/'.hermes') if (p/'config.yaml').is_file()),hermes_default)
    hermes=hermes_home/'config.yaml'
    binaries={
        'opencode':[local/'Programs/@opencodedesktop/OpenCode.exe',local/'Programs/OpenCode/OpenCode.exe',home/'.opencode/bin/opencode.exe'],
        'hermes':[local/'hermes/bin/hermes.exe',home/'.hermes/bin/hermes.exe'],
    }
    configs={'opencode':opencode,'hermes':hermes}
    result={name:{'installed':bool(configs[name].is_file() or any(p.is_file() for p in binaries[name]) or which(name) or (name=='opencode' and which('opencode2'))),
                  'config_path':str(configs[name].expanduser().absolute())} for name in configs}
    # The Electron distribution is OpenCode 2; the v1 desktop uses another store.
    desktop=binaries['opencode'][0]
    if desktop.is_file():
        roaming=Path(env.get('APPDATA',str(home/'AppData/Roaming')))/'ai.opencode.desktop'
        database=roaming/'drafts.sqlite'
        result['opencode']['desktop']={'executable':str(desktop),'state_path':str(database if database.is_file() else roaming/'opencode.global.dat'),
                                      'format':'sqlite' if database.is_file() else 'legacy'}
    return result


def _pairs(values):
    result={}
    for key,value in values:
        if key in result:raise ValueError('Clé de configuration dupliquée : modification annulée.')
        result[key]=value
    return result


def jsonc(text):
    """Mask comments/trailing commas without changing offsets or quoted strings."""
    pattern=r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/'
    clean=re.sub(pattern,lambda m:m[0] if m[0].startswith('"') else ''.join(c if c in '\r\n' else ' ' for c in m[0]),text)
    clean=re.sub(r'"(?:\\.|[^"\\])*"|,(?=\s*[}\]])',lambda m:' ' if m[0]==',' else m[0],clean)
    try:value=json.loads(clean,object_pairs_hook=_pairs)
    except (ValueError,RecursionError) as error:raise ValueError('Configuration OpenCode illisible : fichier conservé.') from error
    if not isinstance(value,dict):raise ValueError('La configuration OpenCode doit être un objet.')
    return value,clean


def _value_end(clean,start):
    decoder=json.JSONDecoder()
    if clean[start] not in '{[':return decoder.raw_decode(clean,start)[1]
    depth=0;i=start
    while i<len(clean):
        if clean[i]=='"':i=decoder.raw_decode(clean,i)[1];continue
        if clean[i] in '{[':depth+=1
        elif clean[i] in '}]':
            depth-=1
            if not depth:return i+1
        i+=1
    raise ValueError('Configuration OpenCode incomplète.')


def _fields(clean,start):
    decoder=json.JSONDecoder();i=start+1;result={}
    while True:
        while clean[i].isspace() or clean[i]==',':i+=1
        if clean[i]=='}':return result,i
        key,i=decoder.raw_decode(clean,i)
        while clean[i].isspace():i+=1
        i+=1
        while clean[i].isspace():i+=1
        end=_value_end(clean,i);result[key]=(i,end);i=end


def _json_set(text,path,value):
    _,clean=jsonc(text);start=len(clean)-len(clean.lstrip())
    for key in path[:-1]:
        fields,_=_fields(clean,start)
        if key not in fields:return _json_set(text,path[:-1],{path[-1]:value})
        start=fields[key][0]
        if clean[start]!='{':raise ValueError('Section OpenCode invalide : fichier conservé.')
    fields,end=_fields(clean,start);encoded=json.dumps(value,ensure_ascii=False,indent=2)
    if path[-1] in fields:
        a,b=fields[path[-1]];return text[:a]+encoded+text[b:]
    # Insert after the final value (before trailing comments) to keep JSONC intact.
    if fields:
        point=list(fields.values())[-1][1]
        return text[:point]+',\n'+json.dumps(path[-1])+': '+encoded+text[point:]
    return text[:end]+'\n'+json.dumps(path[-1])+': '+encoded+'\n'+text[end:]


def opencode_text(text,base_url,key,model,catalogue=None):
    value,_=jsonc(text)
    v2='providers' in value or 'provider' not in value
    section='providers' if v2 else 'provider'
    providers=value.get(section,{})
    if not isinstance(providers,dict):raise ValueError('Liste des fournisseurs OpenCode invalide.')
    old=providers.get(PROVIDER,{})
    if not isinstance(old,dict):raise ValueError('Fournisseur Serveur Fred invalide.')
    entry=copy.deepcopy(old);models=entry.setdefault('models',{})
    if not isinstance(models,dict):raise ValueError('Liste des modèles OpenCode invalide.')
    details=models.setdefault(model,{})
    if not isinstance(details,dict):raise ValueError('Paramètres du modèle OpenCode invalides.')
    details['name']=model
    if catalogue is not None:
        rows={row['id']:row for row in catalogue.get('data',[]) if isinstance(row,dict)
              and isinstance(row.get('id'),str) and not (row.get('capabilities') or {}).get('embedding')}
        if model not in rows or not rows[model].get('available',True):
            raise ValueError('Ce modèle de conversation n’est plus disponible. Actualisez la liste.')
        # Refresh names of models already added; adding one model must not import
        # every shared provider into OpenCode's configuration.
        for identity,settings in models.items():
            if identity in rows and isinstance(settings,dict):
                row=rows[identity]
                settings['name']=row.get('label') or row.get('name') or identity
    if v2:
        details['disabled']=False
        capabilities=details.setdefault('capabilities',{})
        if not isinstance(capabilities,dict):raise ValueError('Capacités du modèle OpenCode invalides.')
        capabilities.update(tools=True)
        capabilities.setdefault('input',['text']);capabilities.setdefault('output',['text'])
    entry['name']=LABEL
    entry['package' if v2 else 'npm']='@opencode/ai/providers/openai-compatible' if v2 else '@ai-sdk/openai-compatible'
    settings=entry.setdefault('settings' if v2 else 'options',{})
    if not isinstance(settings,dict):raise ValueError('Paramètres du fournisseur OpenCode invalides.')
    settings.update(baseURL=base_url,apiKey=key)
    if old==entry:return text
    updated=_json_set(text,[section,PROVIDER],entry)
    check,_=jsonc(updated)
    if check[section][PROVIDER]!=entry:raise ValueError('Configuration OpenCode non vérifiée : modification annulée.')
    return updated


class UniqueLoader(yaml.SafeLoader):
    pass


def _yaml_mapping(loader,node):
    # Merged/aliased maps need a full round-trip editor; do not silently rewrite them.
    keys=[loader.construct_object(k) for k,_ in node.value]
    if len(keys)!=len(set(keys)):raise ValueError('Clé YAML dupliquée : fichier conservé.')
    return yaml.SafeLoader.construct_mapping(loader,node)


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,_yaml_mapping)


def _yaml_end(node):
    """End of actual YAML content, excluding following comments and blank lines."""
    if isinstance(node,(yaml.MappingNode,yaml.SequenceNode)) and node.flow_style:return node.end_mark.index
    if isinstance(node,yaml.MappingNode) and node.value:return _yaml_end(node.value[-1][1])
    if isinstance(node,yaml.SequenceNode) and node.value:return _yaml_end(node.value[-1])
    return node.end_mark.index


def _yaml_provider(text,node,section,entry,legacy,providers):
    """Replace only our provider; leave other providers' formatting/comments intact."""
    if node is None:return text+yaml.safe_dump({section:[entry] if legacy else {PROVIDER:entry}},allow_unicode=True,sort_keys=False)
    if not isinstance(node,yaml.MappingNode):raise ValueError('Configuration Hermes invalide : fichier conservé.')
    if node.flow_style:
        value=yaml.load(text,Loader=UniqueLoader)
        fragment=yaml.safe_dump({**value,section:providers},allow_unicode=True,sort_keys=False).rstrip('\n')
        return text[:node.start_mark.index]+fragment+text[node.end_mark.index:]
    for k,v in node.value:
        if k.value!=section:continue
        if v.flow_style:
            fragment=yaml.safe_dump({section:providers},allow_unicode=True,sort_keys=False).rstrip('\n')
            return text[:k.start_mark.index]+fragment+text[v.end_mark.index:]
        if legacy:
            target=next((p for p in v.value if any(a.value=='name' and b.value==PROVIDER for a,b in p.value)),None)
            item=yaml.safe_dump([entry],allow_unicode=True,sort_keys=False).rstrip('\n')
            # YAML allows sequences at the same indentation as the section key.
            indent=v.start_mark.column
            start=target.start_mark.index-2 if target else None
        else:
            target=next(((a,b) for a,b in v.value if a.value==PROVIDER),None)
            item=yaml.safe_dump({PROVIDER:entry},allow_unicode=True,sort_keys=False).rstrip('\n')
            indent=v.start_mark.column
            start=target[0].start_mark.index if target else None
            target=target[1] if target else None
        fragment=('\n'+' '*indent).join(item.splitlines())
        if target is not None:
            end=_yaml_end(target)
            return text[:start]+fragment+text[end:]
        point=_yaml_end(v)
        if point and text[point-1]=='\n':
            return text[:point]+' '*indent+fragment+'\n'+text[point:]
        line_end=text.find('\n',point)
        if line_end>=0:point=line_end
        return text[:point]+'\n'+' '*indent+fragment+text[point:]
    fragment=yaml.safe_dump({section:[entry] if legacy else {PROVIDER:entry}},allow_unicode=True,sort_keys=False)
    return text.rstrip()+'\n'+fragment


def hermes_text(text,base_url,key,model,catalogue=None):
    try:
        value=yaml.load(text,Loader=UniqueLoader) or {}
        node=yaml.compose(text,Loader=UniqueLoader)
    except (yaml.YAMLError,ValueError,RecursionError,TypeError) as error:raise ValueError('Configuration Hermes illisible : fichier conservé.') from error
    if not isinstance(value,dict):raise ValueError('La configuration Hermes doit être un objet.')
    legacy='custom_providers' in value and 'providers' not in value
    section='custom_providers' if legacy else 'providers'
    providers=copy.deepcopy(value.get(section,[] if legacy else {}))
    if legacy:
        if not isinstance(providers,list) or not all(isinstance(p,dict) for p in providers):raise ValueError('Fournisseurs Hermes invalides.')
        matches=[p for p in providers if p.get('name')==PROVIDER]
        if len(matches)>1:raise ValueError('Fournisseur Serveur Fred dupliqué.')
        old=matches[0] if matches else {};entry=copy.deepcopy(old)
        entry.update(name=PROVIDER,base_url=base_url,api_key=key,api_mode='chat_completions',model=model)
        models=entry.setdefault('models',{})
        if isinstance(models,list):
            if model not in models:models.append(model)
        elif isinstance(models,dict):models.setdefault(model,{})
        else:raise ValueError('Modèles Hermes invalides.')
        if matches:providers[providers.index(old)]=entry
        else:providers.append(entry)
    else:
        if not isinstance(providers,dict):raise ValueError('Fournisseurs Hermes invalides.')
        old=providers.get(PROVIDER,{})
        if not isinstance(old,dict):raise ValueError('Fournisseur Serveur Fred invalide.')
        entry=copy.deepcopy(old);entry.update(name=LABEL,api=base_url,api_key=key,transport='chat_completions',default_model=model)
        models=entry.setdefault('models',{})
        if not isinstance(models,dict):raise ValueError('Modèles Hermes invalides.')
        models.setdefault(model,{})
        providers[PROVIDER]=entry
    if catalogue is not None:
        # This provider belongs to Fred: replace obsolete opaque/embedding entries.
        entry['models']={row['id']:{} for row in catalogue['data']}
    if value.get(section)==providers:return text
    updated=_yaml_provider(text,node,section,entry,legacy,providers)
    try:check=yaml.load(updated,Loader=UniqueLoader)
    except (yaml.YAMLError,ValueError) as error:raise ValueError('Configuration Hermes non vérifiée : modification annulée.') from error
    expected={**value,section:providers}
    if check!=expected:raise ValueError('Configuration Hermes non vérifiée : modification annulée.')
    return updated


def install(app,base_url,key,model,apps=None,catalogue=None):
    if app not in ('opencode','hermes'):raise ValueError('Application inconnue.')
    url=urlsplit(base_url)
    if url.scheme!='http' or url.hostname!='127.0.0.1' or not url.port or url.path!='/v1' or url.query or url.fragment or url.username:raise ValueError('API locale attendue.')
    if not isinstance(model,str) or not model.strip() or len(model)>512 or any(ord(c)<32 for c in model):raise ValueError('Modèle chargé invalide.')
    if not isinstance(key,str) or not 32<=len(key)<=256:raise ValueError('Clé API locale invalide.')
    hermes_models=None
    display_model=model
    if catalogue is not None:
        display_model=next((row.get('label') or row.get('name') or model
                            for row in catalogue.get('data',[]) if isinstance(row,dict) and row.get('id')==model),model)
    if app=='hermes' and catalogue is not None:
        hermes_models,mapping=hermes_catalogue.catalogue(catalogue)
        selected=next((alias for alias,native in mapping.items() if native==model),None)
        if selected is None:raise ValueError('Ce modèle de conversation n’est plus disponible. Actualisez la liste.')
        display_model=next(row.get('name') or row.get('label') or model for row in catalogue['data'] if row['id']==model)
        model=selected
        base_url=base_url.removesuffix('/v1')+'/hermes/v1'
    apps=detect() if apps is None else apps
    if not apps[app]['installed']:raise ValueError('OpenCode non détecté sur ce PC.' if app=='opencode' else 'Hermes non détecté sur ce PC.')
    path=Path(apps[app]['config_path'])
    with locked(path):
        try:raw=path.read_bytes()
        except FileNotFoundError:raw=b''
        if len(raw)>MAX_CONFIG:raise ValueError('Configuration trop volumineuse : fichier conservé.')
        try:text=raw.decode('utf-8-sig')
        except UnicodeError as error:raise ValueError('Configuration non UTF-8 : fichier conservé.') from error
        updated=opencode_text(text or '{}',base_url,key,model,catalogue) if app=='opencode' else hermes_text(text,base_url,key,model,hermes_models)
        backup=None
        if updated!=text:
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():
                backup=path.with_name(path.name+'.fred-backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3))
                atomic(backup,raw)
            if path.exists() and path.read_bytes()!=raw:raise ValueError('Configuration modifiée ailleurs. Réessayez.')
            payload=updated.encode('utf-8')
            if raw.startswith(b'\xef\xbb\xbf'):payload=b'\xef\xbb\xbf'+payload
            atomic(path,payload)
    visibility=opencode_visibility.enable(apps[app].get('desktop'),PROVIDER,model) if app=='opencode' else None
    message=f'Modèle {display_model} ajouté à Hermes. Relancez Hermes, puis ouvrez Modèles et activez l’interrupteur du modèle sous Serveur Fred pour le voir dans le sélecteur.'
    if app=='opencode':
        message=f'Configuration du modèle {display_model} enregistrée pour OpenCode. '
        if visibility['status']=='enabled':message+='Modèle activé dans le sélecteur. Ouvrez OpenCode et sélectionnez Serveur Fred dans /models.'
        elif visibility['status']=='close_required':message+='Pour afficher le modèle dans OpenCode 2, fermez complètement OpenCode puis cliquez à nouveau sur Ajouter à OpenCode 2.'
        else:message+='Dans OpenCode 2, ouvrez Paramètres > Modèles et activez ce modèle sous Serveur Fred. Relancez OpenCode si la liste est vide.'
    backups=[str(backup)] if backup else []
    if visibility and visibility.get('backup'):backups.append(visibility['backup'])
    return {'app':app,'model':model,'provider':PROVIDER,'config_path':str(path),'backup':str(backup) if backup else None,
            'backups':backups,'visibility':visibility,'message':message+' Gardez le client Fred ouvert.'}
