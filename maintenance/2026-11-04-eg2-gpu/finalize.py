"""Summarize measured results and verify that production stayed on CPU."""
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from releases import profile
from validate_live_lots6_8 import get,models


def main():
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
    names=('cpu_eager','cpu_sdpa','p2200_fp32','rtx4080_fp16','p2200_fp32_batch4')
    results={name:json.loads((OUT/(name+'.json')).read_text(encoding='utf-8')) for name in names}
    assert all(r['passed'] for r in results.values())
    for result in results.values():
        for row in result['cases']:
            assert row.get('minimum_cosine_vs_cpu',1)>=.995
    engine=get('/api/knowledge')['engine']
    assert engine['status']=='pret' and engine['device']=='cpu'
    assert engine['pid']==before['engine']['pid']
    assert models()==before['models']
    records=json.loads((ROOT/'lanceur/acces-distants.json').read_text(encoding='utf-8'))['clients']
    active={r['id'] for r in records if not r['revoked'] and not r.get('suspended')}
    values=next(profile(p) for p in (ROOT/'lanceur/clients').glob('*.exe') if p.stem in active)
    request=urllib.request.Request('http://127.0.0.1:8766/v1/embeddings',
        json.dumps({'model':'google/embeddinggemma-2','input':'Vérification après les essais GPU.'}).encode(),
        {'Authorization':'Bearer '+values['token'],'Content-Type':'application/json','X-Fred-Agent-Protocol':'4'})
    started=time.monotonic()
    with urllib.request.urlopen(request,timeout=60) as response:
        status=response.status;value=json.load(response)
    http_seconds=round(time.monotonic()-started,3)
    assert status==200 and len(value['data'][0]['embedding'])==768
    runtime=json.loads(subprocess.check_output([str(ROOT/'toolchain/eg2-python/Scripts/python.exe'),'-c',
        "import torch,json;print(json.dumps({'torch':torch.__version__,'cuda_build':torch.version.cuda}))"],text=True))
    assert runtime['cuda_build'] is None
    summary={'passed':True,'production_changed':False,'engine_pid_preserved':True,
        'qwen_processes_preserved':True,'production_device':engine['device'],'production_runtime':runtime,
        'production_http_check':{'http':status,'dimensions':768,'seconds':http_seconds},
        'measurements':[]}
    for name,result in results.items():
        rows={r['case']:r for r in result['cases']}
        item={'configuration':name,'dtype':result['dtype'],'attention':result['attention'],
            'microbatch':result['batch'],'short_32_seconds':rows['documents_32']['median_seconds'],
            'long_32_seconds':rows['long_32']['median_seconds'],
            'long_32_speedup_vs_production_cpu':round(results['cpu_eager']['cases'][-1]['median_seconds']/rows['long_32']['median_seconds'],2)}
        if result['gpu_uuid']:
            monitor=json.loads((OUT/(name+'-monitor.json')).read_text())
            assert monitor['exit_code']==0 and 'stopped_reason' not in monitor
            item['minimum_free_vram_mib']=monitor['minimum_observed_free_mib']
            item['max_reserved_torch_mib']=max(r['memory']['peak_reserved_mib'] for r in result['cases'])
            item['minimum_cosine_vs_cpu']=min(r['minimum_cosine_vs_cpu'] for r in result['cases'])
        summary['measurements'].append(item)
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True))


if __name__=='__main__':main()
