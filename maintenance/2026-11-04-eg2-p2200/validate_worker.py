"""Exercise real GPU HTTP worker and real startup fallback on synthetic data."""
import json
from pathlib import Path
import sys
import tempfile
import time
import subprocess
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from workspace import Workspace
from embeddings import EmbeddingService
from eg2_runtime import configuration
from validate_live_lots6_8 import models


def main():
    print('Checking current model processes.',flush=True)
    before=models();options=configuration();report={'checks':[],'synthetic_only':True}
    for fallback in (False,True):
        print('Starting '+('CPU recovery' if fallback else 'P2200')+' worker.',flush=True)
        settings=dict(options)
        if fallback:settings['minimum_free_mib']=8192
        with tempfile.TemporaryDirectory(prefix='kiara-eg2-gpu-worker-') as folder:
            workspace=Workspace(Path(folder));engine=EmbeddingService(workspace)
            try:
                with patch('eg2_runtime.configuration',return_value=settings):
                    original=subprocess.Popen
                    log=(OUT/('worker-cpu.log' if fallback else 'worker-gpu.log')).open('w',encoding='utf-8')
                    def launch(command,**kwargs):
                        target=command[1]
                        code="import sys,os,faulthandler,runpy;sys.path.insert(0,os.path.dirname("+repr(target)+"));faulthandler.dump_traceback_later(30,repeat=True);sys.argv=["+repr(target)+",*sys.argv[1:]];runpy.run_path("+repr(target)+",run_name='__main__')"
                        command=[command[0],'-u','-c',code,*command[2:]]
                        kwargs.update(stdout=log,stderr=log)
                        return original(command,**kwargs)
                    with patch('embeddings.subprocess.Popen',side_effect=launch):engine.configure(True)
                    deadline=time.monotonic()+120
                    while engine.state!='pret':
                        engine.tick()
                        if time.monotonic()>deadline:raise TimeoutError(engine.status())
                        time.sleep(.25)
                status=engine.status()
                assert status['device']==('cpu' if fallback else 'cuda:0'),status
                if fallback:assert status['fallback_reason']
                else:assert status['gpu_name']=='Quadro P2200' and status['gpu_uuid']==options['gpu_uuid']
                text=('Le projet conserve les décisions et les documents. Un rappel aide à reprendre le dossier. '*60)[:4200]
                started=time.monotonic()
                result=engine.encode(['Contrôle du repli CPU.'] if fallback else [text]*32,include_usage=True,timeout=45)
                assert len(result['vectors'])==(1 if fallback else 32)
                row={'mode':'cpu_fallback' if fallback else 'p2200','engine':status,
                    'vectors':len(result['vectors']),'prompt_tokens':result['prompt_tokens'],
                    'seconds':round(time.monotonic()-started,3)}
                report['checks'].append(row);print(row['mode']+': '+str(row['vectors'])+' real vectors, '+str(row['seconds'])+' seconds.',flush=True)
            finally:engine.stop();workspace.shutdown()
    assert models()==before
    report['qwen_processes_preserved']=True;report['passed']=True
    (OUT/'worker-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
