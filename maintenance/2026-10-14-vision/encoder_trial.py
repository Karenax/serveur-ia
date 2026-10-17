"""Measure the separate P2200 encoder without stopping the loaded Qwen model."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import psutil
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'dependances/strata-0.1.43.1/source'))
from serve.server import Vision


def memory(pid=None):
    data=subprocess.run(['nvidia-smi','--query-gpu=index,name,memory.used,memory.total','--format=csv,noheader,nounits'],
                        capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    rows=[line.split(', ') for line in data.stdout.strip().splitlines()]
    result={'available_ram_mib':round(psutil.virtual_memory().available/2**20),
            'gpus':[{'index':int(row[0]),'name':row[1],'used_mib':int(row[2]),'total_mib':int(row[3])} for row in rows]}
    if pid:
        info=psutil.Process(pid).memory_info()
        result.update(encoder_rss_mib=round(info.rss/2**20,1),encoder_private_mib=round(getattr(info,'private',info.vms)/2**20,1))
    return result


def main():
    base=json.loads((ROOT/'lanceur/base-strata.json').read_text(encoding='utf-8-sig'))
    args=base['args'];model=args[args.index('--native')+1]
    executable=os.environ.get('FRED_VISION_EXE') or str(ROOT/'dependances/strata-0.1.43.1/engine-cuda12/strata-vision.exe')
    cfg={'exe':executable,
         'mmproj':str(ROOT/'strata-data/vision/mmproj-Qwen3.8-Flash-Next-BF16.gguf'),
         'model':model,'gpu':True,'threads':4,'max_tokens':1024,'cuda_device':'GPU-97ca6406-8625-b829-b053-191c238ff046'}
    canvas=Image.new('RGB',(640,384),'white');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',56)
    draw.text((155,20),'VISION 47',fill='black',font=font)
    draw.ellipse((60,150,230,320),fill='red');draw.rectangle((380,150,550,320),fill='blue')
    fixture=OUT/'vision-fixture.png';canvas.save(fixture)
    env={**os.environ,**base.get('env',{}),'CUDA_VISIBLE_DEVICES':cfg['cuda_device'],'CUDA_DEVICE_ORDER':'PCI_BUS_ID'}
    env['PATH']=os.pathsep.join([*base.get('lib_dirs',[]),env.get('PATH','')])
    before=memory();peak=[];done=threading.Event();vision=None
    report={'before':before,'vision_config':cfg,'fixture':'vision-fixture.png'}
    def sample():
        while not done.wait(.25):
            try:peak.append(memory(vision.proc.pid if vision and vision.alive() else None))
            except (OSError,psutil.Error):pass
    monitor=threading.Thread(target=sample,daemon=True);monitor.start()
    try:
        with (OUT/'encoder-trial.log').open('w',encoding='utf-8') as log:
            started=time.monotonic();vision=Vision(cfg,log,env)
            report['startup_seconds']=round(time.monotonic()-started,3)
            report['loaded']=memory(vision.proc.pid)
            started=time.monotonic();embedding,tokens=vision.encode(fixture.read_bytes())
            report.update(encode_seconds=round(time.monotonic()-started,3),image_tokens=tokens,
                          embedding_bytes=embedding.stat().st_size,after_encode=memory(vision.proc.pid))
            log.flush()
            error_log=(OUT/'encoder-trial.log').read_text(encoding='utf-8')
            accelerated=report['loaded']['gpus'][0]['used_mib']-before['gpus'][0]['used_mib']>256 and 'failed to initialize CUDA' not in error_log
            report.update(gpu_acceleration=accelerated,passed=accelerated)
            assert accelerated,'The encoder fell back to CPU; do not activate it as a P2200 encoder'
            (ROOT/'toolchain/vision-trial-20261014').mkdir(parents=True,exist_ok=True)
            (ROOT/'toolchain/vision-trial-20261014/vision-config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    except Exception as error:
        report.update(passed=False,error=str(error));raise
    finally:
        if vision:vision.close()
        done.set();monitor.join(timeout=3)
        report['samples']=len(peak)
        if peak:
            report['peak_p2200_used_mib']=max(row['gpus'][0]['used_mib'] for row in peak)
            report['peak_encoder_private_mib']=max((row.get('encoder_private_mib',0) for row in peak),default=0)
        report['after_close']=memory()
        (OUT/'encoder.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report),flush=True)


if __name__=='__main__':main()
