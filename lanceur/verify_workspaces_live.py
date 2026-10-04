"""Safe live evidence: process identities, gateway capabilities and signed client."""
import hashlib
import json
from pathlib import Path
import psutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'client-qwen'))
from core import HOME,ROOT,BASE_PATH,matching_servers,process_identity,same_process,write_json,read_json
from releases import profile,status
from client import Remote

def model_processes():
    directory=read_json(HOME/'session.json',{}).get('directory')
    return [process_identity(p) for p in matching_servers([BASE_PATH,*ROOT.glob('strata-*.json'),*([Path(directory)/'strata.json'] if directory else [])])]

if __name__=='__main__':
    evidence=HOME/'workspace-live-proof.json'
    if '--before' in sys.argv:
        values={'model_before':model_processes()}
        write_json(evidence,values);print({'model_processes_recorded':len(values['model_before'])})
    else:
        values=read_json(evidence,{})
        candidates=[c for c in read_json(HOME/'acces-distants.json',{})['clients'] if not c['revoked'] and not c.get('suspended')]
        if not candidates:raise ValueError('Aucun accès existant à vérifier.')
        exe=HOME/'clients'/(candidates[0]['id']+'.exe');p=profile(exe);remote=Remote(p)
        try:
            connected=remote.check()
            with remote.open('/v1/status') as r:state=json.load(r)
            with remote.open('/v1/workspace') as r:workspace=json.load(r)
            with remote.open('/v1/client/release') as r:release=json.load(r)
            with remote.open('/v1/client/download') as r:
                digest=hashlib.file_digest(r,'sha256').hexdigest()
            response=None
            if '--chat' in sys.argv and connected['connected']:
                with remote.open('/v1/chat/completions',json.dumps({'assistant_id':'analysis','messages':[{'role':'user','content':'Réponds uniquement : TEST_FRED_OK'}],'max_tokens':32,'stream':False,'chat_template_kwargs':{'enable_thinking':False}}).encode()) as r:response=json.load(r)
            values.update(server_version=state['version'],client_version=p['version'],connected=connected['connected'],capabilities=workspace['capabilities'],
                          no_login=not bool(remote.session),signed_release_verified=status(HOME)['verified'],download_hash_matches=digest==release['sha256'],
                          model_was_running=bool(values.get('model_before')),model_processes_preserved=all(same_process(p) for p in values.get('model_before',[])),model_loaded=connected['connected'],authenticated_workspace=True,
                          workspace_projects=len(workspace['projects']),chat_answer_present=bool(response and response.get('choices',[{}])[0].get('message',{}).get('content')))
            write_json(evidence,values)
            print(json.dumps({k:v for k,v in values.items() if k!='model_before'},ensure_ascii=False))
            assert values['authenticated_workspace'] and values['signed_release_verified'] and values['download_hash_matches'] and values['model_processes_preserved']
        finally:remote.close()
