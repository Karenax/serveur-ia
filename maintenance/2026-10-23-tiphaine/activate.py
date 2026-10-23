"""Activate the validated local Tiphaine embedding without rebuilding clients."""
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(OUT)]
from validate import source_hashes
from validate_live_lots6_8 import get,models,preserved_files,content_fingerprints,backup_config


def write(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    proof=json.loads((OUT/'native-validation.json').read_text(encoding='utf-8'))
    assert proof['passed'] and proof['voice']=='Tiphaine' and proof['source_sha256']==source_hashes()
    assert not (OUT/'avant-livraison.json').exists(),'Inspect an activation already started before retrying.'
    assert get('/api/state')['queue']['active']==0 and not get('/api/voice')['busy']
    before={'models':models(),'files':preserved_files(),'users':content_fingerprints(),
            'backups':backup_config(get('/api/backups'))}
    write('avant-livraison.json',before)
    spec=importlib.util.spec_from_file_location('delivery',ROOT/'maintenance/2026-10-21-api-embeddings/livrer.py')
    delivery=importlib.util.module_from_spec(spec);spec.loader.exec_module(delivery)
    delivery.OUT=OUT;delivery.restart()
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        voice=get('/api/voice')
        if voice['ready'] and voice['voice']=='Tiphaine':break
        time.sleep(1)
    else:raise TimeoutError('Tiphaine did not become ready.')
    assert models()==before['models'] and get('/api/state')['health']['loaded']
    assert preserved_files()==before['files'] and content_fingerprints()==before['users']
    assert backup_config(get('/api/backups'))==before['backups']
    result={'passed':True,'voice':voice['voice'],'engine':voice['engine'],
            'qwen_keys_data_backups_preserved':True,'client_rebuild_required':False}
    write('production.json',result);print(json.dumps(result))


if __name__=='__main__':main()
